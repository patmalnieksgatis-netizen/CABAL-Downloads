#!/usr/bin/env python3
"""Read exact native save/cleanup entries and their current procedure routes."""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess

WORLD_SHA = 'caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3'
SITES = {'save': 0x7deb00, 'save_route': 0x7e14d0, 'save_pack': 0x8be440,
         'ipc_ack': 0x7debd0, 'owner_ack': 0x7ded30,
         'uninitialize': 0x7df520, 'data_reset': 0xad6060,
         'transport_close': 0xb3cd90}


def command(args):
    return subprocess.check_output(args, text=True, timeout=15).strip()


def main():
    pid = int(command(['docker', 'exec', 'cabal_main', 'supervisorctl',
                       'pid', 'WorldSvr_01_01']))
    if pid <= 1:
        raise RuntimeError('WORLD_NOT_RUNNING')
    found = []
    for token in command(['docker', 'top', 'cabal_main', '-eo', 'pid']).split():
        if not token.isdigit():
            continue
        process = Path('/proc')/token
        try:
            rows = (process/'status').read_text().splitlines()
        except FileNotFoundError:
            continue
        if any(row.startswith('NSpid:') and int(row.split()[-1]) == pid for row in rows):
            found.append(process)
    if len(found) != 1:
        raise RuntimeError('WORLD_HOST_PID_NOT_UNIQUE')
    process = found[0]
    executable = (process/'exe').read_bytes()
    if hashlib.sha256(executable).hexdigest() != WORLD_SHA:
        raise RuntimeError('WORLD_PROFILE_DIFFERS')
    regions = []
    for row in (process/'maps').read_text().splitlines():
        parts = row.split(maxsplit=5)
        start, end = (int(v, 16) for v in parts[0].split('-'))
        regions.append((start, end, parts[1], Path(parts[5]).name if len(parts) == 6 else 'anonymous'))
    phoff = struct.unpack_from('<Q', executable, 0x20)[0]
    phsize, phcount = struct.unpack_from('<HH', executable, 0x36)
    segments = [struct.unpack_from('<IIQQQQQQ', executable, phoff+i*phsize)
                for i in range(phcount)]

    def original(at, size):
        for kind, flags, offset, base, physical, count, memory, align in segments:
            if kind == 1 and base <= at and at+size <= base+count:
                return executable[offset+at-base:offset+at-base+size]
        raise RuntimeError('SITE_NOT_FILE_BACKED')

    def owner(at):
        return next((name for start, end, mode, name in regions if start <= at < end), 'unmapped')

    with (process/'mem').open('rb', buffering=0) as memory:
        def read(at, size):
            if size > 256 or not any(start <= at and at+size <= end and 'r' in mode
                                     for start, end, mode, name in regions):
                raise RuntimeError('SITE_NOT_READABLE')
            value = os.pread(memory.fileno(), size, at)
            if len(value) != size:
                raise RuntimeError('SHORT_READ')
            return value

        sites = []
        for name, address in SITES.items():
            live = read(address, 16)
            sites.append({'site': name, 'address': hex(address), 'bytes': live.hex(' '),
                          'matches_original': live == original(address, 16)})
        routes = []
        for name, table, opcode in [('uninitialize', 0x235f8c0, 143),
                                     ('ipc_ack', 0x2357bc0, 47),
                                     ('owner_ack', 0x2357bc0, 2032)]:
            mapping = int.from_bytes(read(table+opcode*8, 8), 'little')
            if not mapping:
                routes.append({'route': name, 'present': False})
                continue
            first, end, capacity = struct.unpack('<QQQ', read(mapping, 24))
            if end < first or end-first > 256 or (end-first) % 8 or capacity < end:
                raise RuntimeError('INVALID_NATIVE_HANDLER_VECTOR')
            handlers = struct.unpack('<'+'Q'*((end-first)//8), read(first, end-first)) if end > first else ()
            routes.append({'route': name, 'present': True,
                           'locking': int.from_bytes(read(mapping+0x20, 1), 'little'),
                           'handlers': [{'address': hex(at), 'owner': owner(at)} for at in handlers]})
    # Prevent treating observations from a recycled container process as current.
    if int(command(['docker', 'exec', 'cabal_main', 'supervisorctl',
                    'pid', 'WorldSvr_01_01'])) != pid:
        raise RuntimeError('WORLD_RESTARTED_DURING_READ')
    print(json.dumps({'status': 'NATIVE_SAVE_SITES_READ_ONLY_COMPLETE',
                      'world_sha256': WORLD_SHA, 'sites': sites, 'routes': routes}, indent=2))


if __name__ == '__main__':
    main()
