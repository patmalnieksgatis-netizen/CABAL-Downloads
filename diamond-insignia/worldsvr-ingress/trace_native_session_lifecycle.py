#!/usr/bin/env python3
"""Bounded native call trace for the operator's isolated CABAL test VM."""
import subprocess
import shutil

WORKER = r'''
import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
import tempfile
import time

WORLD_SHA = "caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3"

GDB_SOURCE = r"""
import gdb
import hashlib
import json
from pathlib import Path
breaks = []
if hashlib.sha256(Path("/proc/TRACE_PID/exe").read_bytes()).hexdigest() != "TRACE_SHA":
    raise RuntimeError("WORLD_CHANGED_DURING_ATTACH")
hits = 0
class Capture(gdb.Breakpoint):
    def __init__(self, address, label):
        self.label = label
        super().__init__("*" + hex(address), internal=True)
    def stop(self):
        global hits
        hits += 1
        frames = []
        frame = gdb.newest_frame()
        try:
            while frame and len(frames) < 10:
                frames.append(hex(frame.pc()))
                frame = frame.older()
        except gdb.error:
            pass
        gdb.write("DIAMOND_CALL " + json.dumps(dict(event=self.label, frames=frames)) + "\n")
        gdb.flush()
        return hits >= 12
for address, label in ((0xb0acd0, "world_transition"),
                       (0xb0afd0, "unlink"),
                       (0xb0b260, "remove_link")):
    breaks.append(Capture(address, label))
gdb.write("DIAMOND_TRACE_READY\n")
gdb.flush()
"""

def run(pid, debugger, seconds=45):
    target = Path("/proc") / str(pid)
    if pid <= 1 or hashlib.sha256((target / "exe").read_bytes()).hexdigest() != WORLD_SHA:
        raise RuntimeError("WORLD_PROFILE_DIFFERS")
    source = GDB_SOURCE.replace("TRACE_PID", str(pid)).replace("TRACE_SHA", WORLD_SHA)
    with tempfile.TemporaryDirectory(prefix="diamond-lifecycle-") as folder:
        script = Path(folder) / "trace.py"
        script.write_text(source)
        proc = subprocess.Popen([debugger, "-nx", "-nh", "--quiet", "--interpreter=mi2"],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, bufsize=0)
        selector = selectors.DefaultSelector()
        selector.register(proc.stdout, selectors.EVENT_READ)
        buffer = b""
        serial = 0
        running = False
        attached = False
        ready = False
        detached = False

        def read_line(timeout):
            nonlocal buffer, running, ready
            end = time.monotonic() + timeout
            while b"\n" not in buffer:
                remaining = end - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    return None
                chunk = os.read(proc.stdout.fileno(), 65536)
                if not chunk:
                    raise RuntimeError("GDB_OUTPUT_CLOSED")
                buffer += chunk
            raw, buffer = buffer.split(b"\n", 1)
            line = raw.decode("utf-8", errors="replace").strip()
            if line.startswith("*running"):
                running = True
            if line.startswith("*stopped"):
                running = False
            if line.startswith('~"'):
                text = json.loads(line[1:])
                for row in text.splitlines():
                    if row.startswith(("DIAMOND_CALL ", "DIAMOND_TRACE_READY")):
                        print(row, flush=True)
                        if row == "DIAMOND_TRACE_READY":
                            ready = True
            return line

        def command(text, timeout=20):
            nonlocal serial, running
            serial += 1
            token = str(serial)
            proc.stdin.write((token + text + "\n").encode())
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                line = read_line(max(0, end - time.monotonic()))
                if line is None:
                    break
                if line.startswith(token + "^"):
                    result = line[len(token)+1:].split(",", 1)[0]
                    if result == "running":
                        running = True
                    if result in ("done", "running", "exit", "connected"):
                        return
                    print("DIAMOND_GDB_REPLY=" + line, flush=True)
                    raise RuntimeError("GDB_COMMAND_FAILED")
            raise RuntimeError("GDB_COMMAND_TIMEOUT")

        def stop():
            if running:
                command("-exec-interrupt --all", timeout=10)
                end = time.monotonic() + 10
                while running and time.monotonic() < end:
                    read_line(max(0, end - time.monotonic()))
                if running:
                    raise RuntimeError("GDB_INTERRUPT_NOT_CONFIRMED")

        try:
            command("-gdb-set mi-async on")
            command('-interpreter-exec console "set pagination off"')
            command('-interpreter-exec console "set confirm off"')
            command('-interpreter-exec console "set print frame-arguments none"')
            command('-interpreter-exec console "set auto-load off"')
            command("-target-attach " + str(pid))
            attached = True
            command("-interpreter-exec console " + json.dumps("source " + str(script)))
            if not ready:
                raise RuntimeError("TRACE_SETUP_NOT_CONFIRMED")
            command("-exec-continue")
            end = time.monotonic() + seconds
            while running and time.monotonic() < end:
                read_line(max(0, end - time.monotonic()))
        finally:
            try:
                if attached:
                    stop()
                    command("-interpreter-exec console " + json.dumps(
                        "python [p.delete() for p in breaks if p.is_valid()]"))
                    command("-target-detach")
                    detached = True
                    print("DIAMOND_TRACE_DETACHED", flush=True)
                command("-gdb-exit", timeout=10)
                proc.wait(timeout=10)
            finally:
                selector.close()
                try:
                    if proc.poll() is None:
                        # GDB detaches its attached inferior on debugger exit.
                        proc.terminate()
                        proc.wait(timeout=10)
                finally:
                    proc.stdin.close()
                    proc.stdout.close()
        status = (target / "status").read_text()
        tracer = next(s for s in status.splitlines() if s.startswith("TracerPid:"))
        if int(tracer.split()[1]):
            raise RuntimeError("DEBUGGER_STILL_ATTACHED")
        if not ready or not detached:
            raise RuntimeError("TRACE_NOT_CONFIRMED")
        print("DIAMOND_LIFECYCLE_TRACE_COMPLETE", flush=True)
'''

def main():
    pid = int(subprocess.check_output(
        ["docker", "exec", "cabal_main", "supervisorctl", "pid", "WorldSvr_01_01"],
        text=True, timeout=15).strip())
    if pid <= 1:
        raise RuntimeError("WORLD_NOT_RUNNING")
    debugger = shutil.which("gdb")
    if debugger:
        # Translate the container PID into its host PID using namespace metadata.
        from pathlib import Path
        values = subprocess.check_output(
            ["docker", "top", "cabal_main", "-eo", "pid"], text=True, timeout=15)
        found = []
        for value in values.split():
            if not value.isdigit():
                continue
            try:
                status = (Path("/proc") / value / "status").read_text()
            except FileNotFoundError:
                continue
            for row in status.splitlines():
                if row.startswith("NSpid:") and int(row.split()[-1]) == pid:
                    found.append(int(value))
        if len(found) != 1:
            raise RuntimeError("WORLD_HOST_PID_NOT_UNIQUE")
        namespace = {}
        exec(compile(WORKER, "<diamond-trace-worker>", "exec"), namespace)
        namespace["run"](found[0], debugger)
    else:
        location = subprocess.run(
            ["docker", "exec", "cabal_main", "sh", "-c", "command -v gdb"],
            capture_output=True, text=True, timeout=15)
        debugger = location.stdout.strip()
        if location.returncode or not debugger.startswith("/"):
            raise RuntimeError("GDB_UNAVAILABLE")
        payload = WORKER + "\nrun(" + str(pid) + ", " + repr(debugger) + ")\n"
        result = subprocess.run(["docker", "exec", "-i", "cabal_main", "python3", "-"],
                                input=payload, text=True)
        if result.returncode:
            raise RuntimeError("CONTAINER_TRACE_FAILED")

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, OSError, subprocess.SubprocessError) as error:
        print("DIAMOND_TRACE_STOPPED=" + type(error).__name__ + ":" + str(error), flush=True)
        raise SystemExit(2)
