# CABAL v291 EP36_291_TEST: read ONLY eight metadata bytes from original WorldSvr.
# Never modifies WorldSvr, game files, SQL, inventory, Docker or Supervisor.
# Uses Python os.pread() instead of the invalid prior dd bs=1 skip=... method.
$ErrorActionPreference = 'Stop'
$vbox = Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'
if (-not (Test-Path -LiteralPath $vbox -PathType Leaf)) {
    throw 'STOP: VirtualBox VBoxManage.exe nav atrasts.'
}
$running = @(& $vbox list runningvms)
if ($LASTEXITCODE -ne 0) { throw 'STOP: VirtualBox VM status nav nolasāms.' }
$foundVm = @($running | Where-Object { $_ -match '^"EP36_291_TEST"\s+\{' })
if ($foundVm.Count -ne 1) {
    throw 'STOP: EP36_291_TEST nedarbojas vai neatbilst VM nosaukums.'
}
$py = @'
import hashlib
import json
import os
import struct
import subprocess
import sys

EXPECTED = "caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3"
EXPECTED_SIZE = 10596184
KIND_ADDR = 0x13CAB80
ITEM_ID = 33554961

def fail(reason):
    print("DIAMOND_TICKET_METADATA=STOP: " + reason, file=sys.stderr)
    sys.exit(2)

try:
    if os.geteuid() != 0:
        fail("NOT_ROOT_INSIDE_CONTAINER")
    proc = subprocess.run(
        ["supervisorctl", "pid", "WorldSvr_01_01"],
        capture_output=True, text=True, timeout=8
    )
    if proc.returncode or not proc.stdout.strip().isdigit():
        fail("WORLDSVR_NOT_RUNNING_OR_SUPERVISOR_INACCESSIBLE")
    pid = int(proc.stdout.strip())
    if pid <= 1:
        fail("INVALID_WORLDSVR_PID")
    path = "/proc/{}/".format(pid)
    with open(path + "exe", "rb", buffering=0) as world:
        if os.fstat(world.fileno()).st_size != EXPECTED_SIZE:
            fail("WRONG_WORLD_EXECUTABLE_SIZE")
        digest = hashlib.sha256()
        while True:
            chunk = world.read(1048576)
            if not chunk:
                break
            digest.update(chunk)
    if digest.hexdigest() != EXPECTED:
        fail("WRONG_WORLD_EXECUTABLE_SHA")
    # Verify memory range is actually mapped and readable before pread.
    mapped = False
    with open(path + "maps", "r") as maps:
        for line in maps:
            columns = line.split()
            if len(columns) < 2 or not columns[1].startswith("r"):
                continue
            start_end = columns[0].split("-")
            if len(start_end) != 2:
                continue
            start, end = (int(x, 16) for x in start_end)
            if start <= KIND_ADDR and KIND_ADDR + 8 <= end:
                mapped = True
                break
    if not mapped:
        fail("WORLD_CATALOG_METADATA_ADDRESS_NOT_READABLE")
    # Bind the memory read to the same process incarnation.
    def process_start_time():
        with open(path + "stat", "r") as info:
            line = info.read()
        tail = line[line.rfind(")") + 2:].split()
        if len(tail) < 20:
            fail("WORLDSVR_PROC_STAT_INVALID")
        return int(tail[19])
    started_before = process_start_time()
    # This is a read-only seek by offset, NOT a dd skip of 20 MB.
    fd = os.open(path + "mem", os.O_RDONLY | os.O_CLOEXEC)
    try:
        data = os.pread(fd, 8, KIND_ADDR)
    finally:
        os.close(fd)
    if len(data) != 8:
        fail("SHORT_METADATA_READ")
    if process_start_time() != started_before:
        fail("WORLDSVR_PID_REUSED_DURING_CAPTURE")
    kind, limit = struct.unpack("<Ii", data)
    if limit <= 1:
        codec = "singleton_if_stack_limit_le_1"
    elif kind in (0x43, 0x46):
        codec = "option_upper_10_bits"
    elif kind in (0xaf, 0xb8):
        codec = "option_lower_16_bits"
    elif kind in (0x10, 0x1b, 0x66):
        codec = "option_lower_7_bits"
    else:
        codec = "original_helper_fallback_1_NOT_verified_ticket_stack_quantity"
    print(json.dumps({
        "status": "READ_ONLY_WORLD_METADATA",
        "server": "EP36_291_TEST",
        "world_pid": pid,
        "world_sha256": EXPECTED,
        "item_id": ITEM_ID,
        "item_catalog_index": 529,
        "item_catalog_variant": 1,
        "kind_metadata_addr": hex(KIND_ADDR),
        "kind_field38_hex": hex(kind),
        "stack_field3c_signed": limit,
        "quantity_codec": codec,
        "safe_to_plan_ticket_debit": limit <= 1 or kind in (
            0x43, 0x46, 0xaf, 0xb8, 0x10, 0x1b, 0x66),
        "metadata_B0_999_count_not_proven": kind == 0xB0 and limit == 999,
        "no_game_data_changed": True
    }, sort_keys=True))
except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
    fail(type(exc).__name__ + ": " + str(exc))
'@
Write-Host 'DIAMOND: preciza 8 baitu WorldSvr ticket metadata nolasishana; READ ONLY'
# SSH stdin carries the Python source: no temporary code files on the VM.
$py | & ssh root@192.168.56.101 'docker exec -i --privileged cabal_main python3 -'
$exit = $LASTEXITCODE
if ($exit -ne 0) {
    throw "STOP: nolasishana neizdevās (exit $exit). Nekas netika mainits."
}
