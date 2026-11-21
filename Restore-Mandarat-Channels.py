"""Restore the saved data for the 4379 test deployment inside cabal_main."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

DATA = Path('/etc/cabal/Data')
ROOT = Path('/etc/cabal/migration_tools/mandarat-lv1-test')
BACKUP = ROOT / 'backup-eyngyc_l'
CHANNELS = ('WorldSvr_01_01', 'WorldSvr_01_16')
MANIFEST = 'b6a3d6f678952f699c273867d43fab43d15626f9f33125795d4fd8b252ffc6c6'

def require(ok, why):
    if not ok:
        raise RuntimeError(why)

def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def supervisor(*args):
    return subprocess.run(['supervisorctl', *args], text=True, capture_output=True, timeout=60)

def pid(name):
    result = supervisor('pid', name)
    require(result.stdout.strip().isdigit(), 'PID_UNKNOWN_' + name)
    return int(result.stdout.strip())

def restore():
    saved = json.loads((BACKUP / 'original.json').read_bytes())
    applied = json.loads((BACKUP / 'applied.json').read_bytes())
    files = applied['files']
    require(hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest() == MANIFEST, 'WRONG_DEPLOYMENT')
    require(set(saved) == set(files) and set(applied['pids']) == set(CHANNELS), 'RECEIPT_DIFFERS')
    status = supervisor('status')
    require(status.returncode in (0, 3), 'STATUS_FAILED')
    for line in status.stdout.splitlines():
        fields = line.split()
        if fields and fields[0].startswith('WorldSvr_') and fields[0] not in CHANNELS:
            require(fields[1] in ('STOPPED','EXITED','FATAL'), 'OTHER_CHANNEL_ACTIVE')
    for name, row in files.items():
        target = DATA / name
        original = saved[name]['sha256']
        require(not target.is_symlink() and not target.parent.is_symlink(), 'SYMLINK_' + name)
        require(original == row['before'] == checksum(BACKUP / name), 'BACKUP_DIFFERS_' + name)
        require(checksum(target) in (row['before'], row['after']), 'DATA_CHANGED_' + name)
    for channel in CHANNELS:
        result = supervisor('stop', channel)
        require(pid(channel) == 0, 'STOP_FAILED_' + channel + result.stdout)
    for name, row in saved.items():
        target = DATA / name
        if checksum(target) == row['sha256']:
            continue
        if row['sha256'] is None:
            target.unlink()
        else:
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as tmp:
                tmp.write((BACKUP / name).read_bytes())
                tmp.flush()
                os.fsync(tmp.fileno())
            os.chmod(tmp.name, row['mode'])
            os.replace(tmp.name, target)
        require(checksum(target) == row['sha256'], 'RESTORE_FAILED_' + name)
    print('ORIGINAL_DATA_RESTORED', flush=True)
    for channel in CHANNELS:
        result = supervisor('start', channel)
        require(result.returncode == 0, 'START_FAILED_' + channel + result.stdout)
    initial = [pid(channel) for channel in CHANNELS]
    require(all(initial), 'CHANNEL_NOT_RUNNING')
    for _ in range(30):
        time.sleep(2)
        require([pid(channel) for channel in CHANNELS] == initial, 'CHANNEL_RESTARTED')
    print('ORIGINAL_DATA_RESTORED_CH1_CH16_STABLE_60S', flush=True)

if __name__ == '__main__':
    if '--inside' not in sys.argv:
        require(Path('/sys/class/dmi/id/product_uuid').read_text().strip().lower() ==
                '7632fb78-37a0-f645-97c0-dc322c50b002', 'WRONG_TEST_VM')
        subprocess.run(['docker', 'exec', '-i', 'cabal_main', 'python3', '-', '--inside'],
                       input=Path(sys.argv[0]).read_bytes(), check=True)
    else:
        with (ROOT / 'apply.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            restore()
