"""Read the isolated291 clone's cached public menu and categorical auth log events.

No login request, process write, file write, restart, account/credential export,
packet capture or raw log output. Works on the existing attempt.
"""
import datetime
import hashlib
import json
import os
import re
import struct
import subprocess
from pathlib import Path

VM_UUID = '7632fb78-37a0-f645-97c0-dc322c50b002'
LOGIN_SHA = '8441a56885dbb29c58e5b2ada75cf58aae2d7d35bd01c01fa13212b5e31bb8c9'


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def menu_metadata(body):
    need(len(body) >= 7, 'MENU_SHORT_HEADER')
    magic, size, opcode = struct.unpack_from('<HHH', body)
    need(magic == 0xb7e2 and size == len(body) and opcode == 121, 'MENU_HEADER_DIFFERS')
    groups = []
    at = 7
    for _ in range(body[6]):
        need(at + 9 <= len(body), 'MENU_SHORT_GROUP')
        group_id, count = body[at], body[at + 8]
        at += 9
        channels = []
        for _ in range(count):
            need(at + 103 <= len(body), 'MENU_SHORT_CHANNEL')
            ch = body[at:at + 103]
            # Original291 parser6A2CFC consumes this103-byte layout.
            ip = ch[28:93].split(b'\0', 1)[0].decode('ascii', errors='replace')
            if not re.fullmatch(r'[0-9.]{0,15}', ip):
                ip = 'NON_IPV4_TEXT'
            current = struct.unpack_from('<H', ch, 2)[0]
            maximum = struct.unpack_from('<H', ch, 26)[0]
            channels.append(dict(group=ch[0], channel=ch[1], current_players=current,
                                 max_players=maximum, count_at_or_over_max=current >= maximum,
                                 ip=ip, port=struct.unpack_from('<H', ch, 93)[0]))
            at += 103
        groups.append(dict(group=group_id, channels=channels))
    need(at == len(body), 'MENU_UNEXPECTED_TRAILING_BYTES')
    return dict(opcode=opcode, bytes=len(body), groups=groups)


def log_metadata(root):
    result = []
    categories = (
        ('AUTH_COMPLETE', r'\bAuth\s+Complete\b'),
        ('AUTH_TYPE_MISMATCH', r'Not\s+Matched\s+Auth\s+Type'),
        ('AUTH_VERIFY_SUCCESS', r'\bVerify\s*Success\b'),
        ('AUTH_VERIFY_REMOTE', r'\bVerify\s+Remote\b'),
        ('WRONG_PACKET_COMMAND', r'wrong\s+packet\s+command'),
        ('AUTH_CLOSE', r'\bAuth\s+Close\b'),
        ('TIMEOUT', r'\b(?:timeout|timeover|timed\s+out)\b'),
    )
    for name in ('LoginSvr_01.log', 'GlobalDBAgent.log'):
        path = root / 'var/log/cabal' / name
        if not path.is_file():
            result.append(dict(log=name, status='MISSING'))
            continue
        st = path.stat()
        with path.open('rb') as f:
            f.seek(max(0, st.st_size - 256 * 1024))
            lines = f.read(256 * 1024).decode('utf-8', errors='replace').splitlines()
        rows = []
        for line in lines:
            matches = [label for label, pattern in categories if re.search(pattern, line, re.I)]
            if not matches:
                continue
            # Whitelist outputs; never print names, keys, full lines or arbitrary values.
            timestamp = re.search(r'\b20\d\d-\d\d-\d\d[ T]\d\d:\d\d:\d\d\b', line)
            row = dict(events=matches, time=timestamp[0] if timestamp else 'UNPARSED')
            for label in ('Result', 'Reason', 'AuthType'):
                value = re.search(r'\b' + label + r'\s*(?:[=:]\s*)?\(?\s*(-?\d{1,8})\b', line, re.I)
                if value:
                    row[label.lower()] = int(value[1])
            for requester in ('CompletedStep1', 'RequesterPassword'):
                if requester.lower() in line.lower():
                    row['requester'] = requester
            command = re.search(r'wrong\s+packet\s+command\s*:\s*(\d{1,5})\b', line, re.I)
            if command:
                row['command'] = int(command[1])
            rows.append(row)
        result.append(dict(log=name, mtime_utc=datetime.datetime.fromtimestamp(
            st.st_mtime, datetime.timezone.utc).isoformat(), events=rows[-24:]))
    return result


def main():
    need(os.geteuid() == 0, 'ROOT_REQUIRED_FOR_READ')
    need(Path('/sys/class/dmi/id/product_uuid').read_text().strip().lower() == VM_UUID, 'WRONG_291_TEST_VM')
    def run(args):
        return subprocess.check_output(args, text=True, timeout=15).strip()
    namespace_pid = run(['docker', 'exec', 'cabal_main', 'supervisorctl', 'pid', 'LoginSvr_01'])
    need(namespace_pid.isdigit() and int(namespace_pid) > 0, 'LOGIN_NOT_RUNNING')
    candidates = run(['docker', 'top', 'cabal_main', '-eo', 'pid']).splitlines()
    matches = []
    for value in candidates:
        if not value.strip().isdigit():
            continue
        p = Path('/proc') / value.strip()
        try:
            n = re.search(r'^NSpid:\s+([0-9 \t]+)$', (p / 'status').read_text(), re.M)
            if n and n[1].split()[-1] == namespace_pid:
                matches.append(p)
        except FileNotFoundError:
            pass
    need(len(matches) == 1, 'LOGIN_PROCESS_NOT_UNIQUE')
    p = matches[0]
    start = (p / 'stat').read_text().rsplit(')', 1)[1].split()[19]
    need(hashlib.sha256((p / 'exe').read_bytes()).hexdigest() == LOGIN_SHA, 'LOGIN_BINARY_CHANGED')
    ranges = []
    for line in (p / 'maps').read_text().splitlines():
        span, flags = line.split()[:2]
        if 'r' in flags:
            ranges.append(tuple(int(v, 16) for v in span.split('-')))
    fd = os.open(p / 'mem', os.O_RDONLY)
    def read(at, count):
        need(1 <= count <= 4096 and any(lo <= at and at + count <= hi for lo, hi in ranges), 'PUBLIC_MENU_RANGE_NOT_READABLE')
        data = os.pread(fd, count, at)
        need(len(data) == count, 'SHORT_PUBLIC_MENU_READ')
        return data
    def pointer(at):
        return struct.unpack('<Q', read(at, 8))[0]
    def packet(at, opcode):
        h = read(at, 6)
        magic, size, command = struct.unpack('<HHH', h)
        need(magic == 0xb7e2 and command == opcode and 6 <= size <= 4096, 'PUBLIC_MENU_HEADER_DIFFERS')
        b = read(at, size)
        need(b[:6] == h and read(at, size) == b, 'PUBLIC_MENU_CHANGED_DURING_READ')
        return b
    menus = {}
    try:
        context = pointer(0x80c9a0)
        for label, offset in (('list_a', 0x103aa), ('list_b', 0x202aa)):
            try:
                menus[label] = menu_metadata(packet(context + offset, 121))
            except RuntimeError as e:
                menus[label] = dict(status=str(e))
        try:
            status = packet(pointer(0x80df88) + 0x40, 124)
            menus['status124'] = dict(opcode=124, bytes=len(status))
        except RuntimeError as e:
            menus['status124'] = dict(status=str(e))
    finally:
        os.close(fd)
    logs = log_metadata(p / 'root')
    need((p / 'stat').read_text().rsplit(')', 1)[1].split()[19] == start, 'LOGIN_PROCESS_CHANGED')
    print(json.dumps(dict(status='READ_ONLY_COMPLETE', utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                          login_pid=int(namespace_pid), login_sha256=LOGIN_SHA, menus=menus, logs=logs,
                          changes=False, credentials_exported=False), indent=2), flush=True)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.SubprocessError) as e:
        raise SystemExit('READ_NOT_COMPLETED: ' + type(e).__name__ + ': ' + str(e))
