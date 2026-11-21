"""Apply the pinned Mandarat Lv.1 overlay on the explicitly selected test VM."""
import base64
import hashlib
from pathlib import Path
import subprocess
import sys

VM = "7632fb78-37a0-f645-97c0-dc322c50b002"
ARCHIVE_SHA = "4fc70b47a643451751a2f3e9849120f565a23e7ae5bbaf20fb68e0940cf0da41"

INSIDE = r'''
import fcntl, hashlib, io, json, os, re, shutil, stat, subprocess, tempfile, time, zipfile
from pathlib import Path

DATA = Path("/etc/cabal/Data")
ROOT = Path("/etc/cabal/migration_tools/mandarat-lv1-test")
WORLD = "WorldSvr_01_01"
WORLD_SHA = "caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3"

def require(ok, message):
    if not ok:
        raise RuntimeError(message)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

def pid(service):
    result = subprocess.run(["supervisorctl", "pid", service], capture_output=True, text=True, timeout=15)
    require(result.stdout.strip().isdigit(), "SERVICE_PID_UNAVAILABLE_" + service)
    return int(result.stdout.strip())

def control(action, service):
    result = subprocess.run(["supervisorctl", action, service], capture_output=True, text=True, timeout=50)
    require(result.returncode == 0 or (action == "stop" and pid(service) == 0), service + "_" + action.upper() + "_FAILED")

def atomic(path, data, mode):
    fd, name = tempfile.mkstemp(prefix=".mandarat-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)

def listening(process):
    root = Path("/proc") / str(process)
    inodes = set()
    for fd in (root / "fd").iterdir():
        try:
            target = os.readlink(fd)
        except OSError:
            continue
        if target.startswith("socket:["):
            inodes.add(target[8:-1])
    for filename in ("tcp", "tcp6"):
        for row in (root / "net" / filename).read_text().splitlines()[1:]:
            fields = row.split()
            if fields[3] == "0A" and fields[9] in inodes:
                return True
    return False

def channel_ready(name, process, expected):
    if process <= 0:
        return False
    try:
        if not listening(process):
            return False
        actual = digest(Path("/proc") / str(process) / "exe")
    except (FileNotFoundError, ProcessLookupError):
        return False
    if actual is None or pid(name) != process:
        return False
    require(actual == expected, name + "_BINARY_CHANGED")
    return True

def log_position(path):
    try:
        info = path.stat()
        return info.st_ino, info.st_size
    except OSError:
        return None, 0

def report_start_errors(positions):
    for path, (inode, offset) in positions.items():
        try:
            with path.open("rb") as stream:
                info = os.fstat(stream.fileno())
                start = offset if info.st_ino == inode and info.st_size >= offset else 0
                stream.seek(max(start, info.st_size - 2 * 1024 * 1024))
                lines = stream.read(2 * 1024 * 1024).decode(errors="replace").splitlines()
            relevant = [line for line in lines if any(tag in line.upper() for tag in
                        ("ASSERT", "INVALID", "FATAL", "SIGABRT", "SIGSEGV", "FAILED"))]
            for line in relevant[:16]:
                print(path.name, line[:700], flush=True)
        except OSError as error:
            print(path.name, "LOG_UNAVAILABLE", error, flush=True)

def healthy(login, binaries):
    started = time.monotonic()
    stable = None
    stable_since = started
    while time.monotonic() - started < 180:
        processes = {name: pid(name) for name in binaries}
        require(pid("LoginSvr_01") == login, "LOGIN_PROCESS_CHANGED")
        if all(channel_ready(name, process, binaries[name]) for name, process in processes.items()):
            if processes != stable:
                stable = processes
                stable_since = time.monotonic()
            if time.monotonic() - stable_since >= 90:
                return processes
        else:
            stable = None
            stable_since = time.monotonic()
        time.sleep(2)
    raise RuntimeError("WORLD_START_TIMEOUT")

def registered_world(config, number=b"166"):
    section_name = b"world-" + number
    headers = list(re.finditer(rb"(?m)^[ \t]*\[([^\]\r\n]+)\][^\r\n]*", config))
    sections = {}
    for index, header in enumerate(headers):
        name = header[1].strip().lower()
        if name not in (b"world-165", section_name, b"world-172"):
            continue
        require(name not in sections, "DUPLICATE_WORLD_SECTION")
        end = headers[index + 1].start() if index + 1 < len(headers) else len(config)
        values = {}
        for line in config[header.end():end].splitlines():
            line = line.split(b";", 1)[0].strip()
            if not line or line.startswith(b"#"):
                continue
            key, sep, value = line.partition(b"=")
            key = key.strip().lower()
            require(sep and key not in values, "WORLD_SECTION_FORMAT_DIFFERS")
            values[key] = value.strip()
        sections[name] = values

    def expected(number):
        prefix = b"Data/Data_World/world" + number
        return {b"worldtype": b"1", b"threadmap": prefix + b"-tmap.bin",
                b"mobsmap": prefix + b"-mmap.scp", b"npc": prefix + b"-npc.scp", b"skillexp": b"1"}

    require(sections.get(b"world-165") == expected(b"165"), "WORLD_165_PROFILE_DIFFERS")
    for key in (b"threadmap", b"mobsmap", b"npc"):
        require(sections.get(b"world-172", {}).get(key) == expected(b"172")[key], "WORLD_172_PATH_DIFFERS")
    if section_name in sections:
        require(sections[section_name] == expected(number), "EXISTING_WORLD_" + number.decode() + "_DIFFERS")
        return config
    pos = next(h.start() for h in headers if h[1].strip().lower() == b"world-165")
    nl = b"\r\n" if config[config.index(b"\n",pos)-1:config.index(b"\n",pos)+1] == b"\r\n" else b"\n"
    lines = [b"[World-" + number + b"]", b"WorldType=1", b"ThreadMap=Data/Data_World/world" + number + b"-tmap.bin",
             b"MobsMap=Data/Data_World/world" + number + b"-mmap.scp", b"Npc=Data/Data_World/world" + number + b"-npc.scp",
             b"SkillExp=1", b"", b""]
    return config + nl + nl.join(lines)

def main(body, six=False):
    require(os.geteuid() == 0, "ROOT_REQUIRED")
    require(DATA.is_dir() and not DATA.is_symlink(), "DATA_PATH_DIFFERS")
    require(not ROOT.is_symlink(), "BACKUP_ROOT_SYMLINK")
    ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (ROOT / "apply.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            manifest = json.loads(archive.read("hashes.json"))
            if not six:
                manifest["Data_World/world166-tmap.bin"] = {
                "before": None,
                "after": "17cac3a1db17b570f39f70c877485b38bf3930f023bdada9234d53cbd5f20db9"}
            payload = {}
            for name, hashes in manifest.items():
                require(not Path(name).is_absolute() and ".." not in Path(name).parts, "INVALID_PATH")
                target = DATA / name
                require(not target.is_symlink() and not target.parent.is_symlink(), "TARGET_SYMLINK_" + name)
                data = archive.read("Data/" + name)
                require(hashlib.sha256(data).hexdigest() == hashes["after"], "PAYLOAD_HASH_DIFFERS_" + name)
                require(digest(target) in (hashes["before"], hashes["after"]), "BASELINE_CHANGED_" + name)
                payload[name] = data
        require(digest(DATA / "Mobs.scp") == "994c2e923cd7192a8ccfa6ae00613a99c8082b1d72a070bf9d0bc3dd74c040d1", "NATIVE_SPECIES_TABLE_DIFFERS")
        paths = {name: DATA / name for name in payload}
        common = DATA.parent / "Common.ini"
        require(common.is_file() and not common.is_symlink(), "COMMON_INI_PATH_DIFFERS")
        original = common.read_bytes()
        updated = original
        for number in range(166, 172 if six else 167):
            updated = registered_world(updated, str(number).encode())
        paths["Common.ini"] = common
        manifest["Common.ini"] = {"before": hashlib.sha256(original).hexdigest(), "after": hashlib.sha256(updated).hexdigest()}
        payload["Common.ini"] = updated
        process = pid(WORLD)
        login = pid("LoginSvr_01")
        require(process > 0 and login > 0, "START_TEST_SERVER_FIRST")
        require(digest(Path("/proc") / str(process) / "exe") == WORLD_SHA, "WORLD_BINARY_DIFFERS")
        status = subprocess.run(["supervisorctl", "status"], capture_output=True, text=True, timeout=15)
        # Supervisor returns 3 when the listing includes services that are stopped.
        require(status.returncode in (0, 3), "SUPERVISOR_STATUS_FAILED")
        rows = [line.split() for line in status.stdout.splitlines()]
        active = [row[0] for row in rows if len(row) >= 2 and row[0].startswith("WorldSvr_") and row[1] == "RUNNING"]
        require(WORLD in active and set(active) <= {WORLD, "WorldSvr_01_16"}, "OTHER_WORLD_CHANNEL_RUNNING")
        require(all(row[1] in ("RUNNING", "STOPPED", "EXITED", "FATAL") for row in rows
                    if len(row) >= 2 and row[0].startswith("WorldSvr_")), "WORLD_CHANNEL_TRANSITION")
        binaries = {name: digest(Path("/proc") / str(pid(name)) / "exe") for name in active}
        require(all(binaries.values()), "WORLD_BINARY_UNAVAILABLE")
        if all(digest(paths[name]) == row["after"] for name, row in manifest.items()):
            healthy(login, binaries)
            print("MANDARAT_ALREADY_APPLIED; GAMEPLAY_PENDING", flush=True)
            return
        backup = Path(tempfile.mkdtemp(prefix="backup-", dir=ROOT))
        print("MANDARAT_BACKUP=" + str(backup), flush=True)
        saved = {}
        for name in payload:
            target = paths[name]
            data = target.read_bytes() if target.exists() else None
            mode = stat.S_IMODE(target.stat().st_mode) if data is not None else 0o644
            require(name != "Common.ini" or data == original, "COMMON_CHANGED_BEFORE_BACKUP")
            saved[name] = {"sha256": hashlib.sha256(data).hexdigest() if data is not None else None, "mode": mode}
            if data is not None:
                destination = backup / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
                require(digest(destination) == saved[name]["sha256"], "BACKUP_HASH_FAILED")
        (backup / "original.json").write_text(json.dumps(saved, indent=2))
        touched = []
        positions = {}
        stopped = False
        try:
            stopped = True
            for name in active:
                control("stop", name)
                require(pid(name) == 0, name + "_STILL_RUNNING")
            for name, row in saved.items():
                require(digest(paths[name]) == row["sha256"], "DATA_CHANGED_DURING_STOP_" + name)
            for name, data in payload.items():
                target = paths[name]
                target.parent.mkdir(parents=True, exist_ok=True)
                touched.append(name)
                atomic(target, data, saved[name]["mode"])
                require(digest(target) == manifest[name]["after"], "POST_WRITE_HASH_FAILED")
            for name in active:
                path = Path("/var/log/cabal") / (name + ".log")
                positions[path] = log_position(path)
            for name in active:
                control("start", name)
            new_pids = healthy(login, binaries)
        except BaseException:
            if stopped or touched:
                for name in active:
                    control("stop", name)
                report_start_errors(positions)
                for name in reversed(touched):
                    target = paths[name]
                    if saved[name]["sha256"] is None:
                        target.unlink(missing_ok=True)
                    else:
                        atomic(target, (backup / name).read_bytes(), saved[name]["mode"])
                    require(digest(target) == saved[name]["sha256"], "ROLLBACK_HASH_FAILED_" + name)
                for name in active:
                    control("start", name)
                healthy(login, binaries)
                print("MANDARAT_ROLLED_BACK; BACKUP=" + str(backup), flush=True)
            raise
        (backup / "applied.json").write_text(json.dumps({"pids": new_pids, "files": manifest}, indent=2))
        print("MANDARAT_FILES_APPLIED; WORLD_PIDS=" + str(new_pids) + "; LISTENER_STABLE_90_SECONDS; GAMEPLAY_PENDING", flush=True)
'''

def main():
    if Path("/sys/class/dmi/id/product_uuid").read_text().strip().lower() != VM:
        sys.exit("WRONG_TEST_VM")
    six = sys.argv[1:] == ["--six"]
    if sys.argv[1:] and not six:
        sys.exit("Unknown option")
    body = Path("/tmp/Mandarat-Lv1-Ticket.zip" if six else "/tmp/Mandarat-Lv1-4379-r2.zip").read_bytes()
    expected = "2855728f630c96a0d7ac7874ab45955d56820f8e09822b62f81e8949c3da3191" if six else ARCHIVE_SHA
    if hashlib.sha256(body).hexdigest() != expected:
        sys.exit("ZIP_HASH_DIFFERS")
    source = INSIDE + "\nmain(__import__('base64').b64decode(" + repr(base64.b64encode(body).decode()) + "), six=" + repr(six) + ")\n"
    subprocess.run(["docker", "exec", "-i", "cabal_main", "python3", "-"], input=source.encode(), check=True)

if __name__ == "__main__":
    main()
