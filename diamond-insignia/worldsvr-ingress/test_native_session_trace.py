"""Exercise debugger attachment and detachment against a local test process."""
import contextlib
import hashlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from trace_native_session_lifecycle import WORKER

DEBUGGER = os.environ.get("DIAMOND_TEST_GDB") or shutil.which("gdb")

@unittest.skipUnless(DEBUGGER and shutil.which("gcc"), "requires gdb and gcc")
class NativeTraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="diamond-trace-test-")
        root = Path(cls.directory.name)
        source = root / "target.c"
        source.write_text("""
#include <sys/prctl.h>
#include <unistd.h>
__attribute__((noinline)) void transition(void) { __asm__ volatile(""); }
__attribute__((noinline)) void unlink_session(void) { __asm__ volatile(""); }
__attribute__((noinline)) void remove_link(void) { __asm__ volatile(""); }
int main(int argc, char **argv) {
    prctl(PR_SET_PTRACER, PR_SET_PTRACER_ANY, 0, 0, 0);
    for (;;) {
        if (argc == 1) { transition(); unlink_session(); remove_link(); }
        usleep(10000);
    }
}
""")
        cls.target = root / "target"
        subprocess.run(["gcc", "-O0", "-g", "-no-pie", str(source),
                        "-o", str(cls.target)], check=True)
        cls.symbols = {s[-1]: "0x"+s[0] for line in subprocess.check_output(
            ["nm", str(cls.target)], text=True).splitlines()
            if len(s := line.split()) == 3}

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def fixture(self):
        namespace = {}
        exec(WORKER, namespace)
        namespace["WORLD_SHA"] = hashlib.sha256(self.target.read_bytes()).hexdigest()
        source = namespace["GDB_SOURCE"]
        for address, name in (("0xb0acd0", "transition"), ("0xb0afd0", "unlink_session"),
                              ("0xb0b260", "remove_link")):
            source = source.replace(address, self.symbols[name])
        namespace["GDB_SOURCE"] = source
        return namespace

    def run_fixture(self, namespace, idle=False, expect_failure=False):
        output = io.StringIO()
        target = subprocess.Popen([str(self.target), *(["idle"] if idle else [])])
        try:
            with contextlib.redirect_stdout(output):
                if expect_failure:
                    with self.assertRaises(RuntimeError):
                        namespace["run"](target.pid, DEBUGGER, 0.1)
                else:
                    namespace["run"](target.pid, DEBUGGER, 0.1 if idle else 5)
            self.assertIsNone(target.poll())
            status = Path(f"/proc/{target.pid}/status").read_text()
            self.assertRegex(status, r"TracerPid:\s+0\b")
        finally:
            target.terminate()
            target.wait(timeout=5)
        return output.getvalue()

    def test_hit_limit_detaches(self):
        output = self.run_fixture(self.fixture())
        self.assertEqual(output.count("DIAMOND_CALL "), 12)
        self.assertIn("DIAMOND_LIFECYCLE_TRACE_COMPLETE", output)

    def test_timer_detaches_without_signalling_target(self):
        output = self.run_fixture(self.fixture(), idle=True)
        self.assertNotIn("DIAMOND_CALL ", output)
        self.assertIn("DIAMOND_TRACE_DETACHED", output)

    def test_source_error_detaches(self):
        namespace = self.fixture()
        namespace["GDB_SOURCE"] = "breaks=[]\nraise RuntimeError('fixture')"
        output = self.run_fixture(namespace, expect_failure=True)
        self.assertIn("DIAMOND_TRACE_DETACHED", output)

    def test_wrong_hash_prevents_attachment(self):
        namespace = self.fixture()
        namespace["WORLD_SHA"] = "0"*64
        output = self.run_fixture(namespace, expect_failure=True)
        self.assertNotIn("DIAMOND_TRACE_READY", output)

if __name__ == "__main__":
    unittest.main()
