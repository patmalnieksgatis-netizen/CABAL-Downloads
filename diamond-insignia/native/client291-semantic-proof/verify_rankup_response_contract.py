#!/usr/bin/env python3
"""Exercise the owner's exact v291 Rank-up reader in an isolated x64 emulator.

No game process is started or modified. Real instructions implement the
response branch, quantity access, WExp and grade writes; GUI, catalog and
inventory-container services are explicit fixtures. Success cases stop before
the final GUI rendering. This is not a functioning WorldSvr/backend test.
Requires unicorn 2.x. No client bytes are included in the repository.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE, UC_HOOK_MEM_READ
from unicorn.x86_const import (
    UC_X86_REG_RAX, UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8,
    UC_X86_REG_R9, UC_X86_REG_RSP, UC_X86_REG_RIP,
)

SHA = '52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9'
BASE = 0x140000000
GLOBAL = 0x30000000
MERIT = GLOBAL + 0x10000
COSTS = MERIT + 0x1000
ITEM = MERIT + 0x2000
META = MERIT + 0x3000
VTABLE = MERIT + 0x4000
UI = MERIT + 0x5000
STACK = 0x40000000
PACKET_PAGE = 0x50000000
PACKET = PACKET_PAGE + 4096 - 7  # next page deliberately unmapped
FETCH_ITEM = 0x180000000
STOP = FETCH_ITEM + 0x100


class Fixture:
    def __init__(self, body):
        self.u = Uc(UC_ARCH_X86, UC_MODE_64)
        nt, = struct.unpack_from('<I', body, 60)
        if body[nt:nt+4] != b'PE\0\0':
            raise ValueError('PE_SIGNATURE')
        optional = nt + 24
        if struct.unpack_from('<H', body, optional)[0] != 0x20b:
            raise ValueError('NOT_PE64')
        image_size, = struct.unpack_from('<I', body, optional + 56)
        image_base, = struct.unpack_from('<Q', body, optional + 24)
        if image_base != BASE or not 0x1000000 < image_size < 0x4000000:
            raise ValueError('IMAGE_LAYOUT')
        self.u.mem_map(BASE, (image_size + 4095) & ~4095)
        count, = struct.unpack_from('<H', body, nt + 6)
        opt_size, = struct.unpack_from('<H', body, nt + 20)
        for i in range(count):
            at = optional + opt_size + 40*i
            rva, size, off = struct.unpack_from('<III', body, at + 12)
            if size:
                self.u.mem_write(BASE+rva, body[off:off+size])
        self.u.mem_map(GLOBAL, 0x20000)
        self.u.mem_map(STACK, 0x10000)
        self.u.mem_map(PACKET_PAGE, 4096)
        self.u.mem_map(FETCH_ITEM, 4096)
        self.stubs = {}
        self.packet_reads = []
        self.stopped = False
        self.u.hook_add(UC_HOOK_CODE, self.code)
        self.u.hook_add(UC_HOOK_MEM_READ, self.read)

    def put(self, at, n, width=8):
        self.u.mem_write(at, n.to_bytes(width, 'little'))

    def get(self, at, width=8):
        return int.from_bytes(self.u.mem_read(at, width), 'little')

    def code(self, u, at, _size, _ctx):
        if at == STOP:
            self.stopped = True
            u.emu_stop()
        elif at in self.stubs:
            result = self.stubs[at]()
            if result is not None:
                u.reg_write(UC_X86_REG_RAX, result)
            sp = u.reg_read(UC_X86_REG_RSP)
            target = self.get(sp)
            u.reg_write(UC_X86_REG_RSP, sp+8)
            u.reg_write(UC_X86_REG_RIP, target)

    def read(self, _u, _access, at, size, _value, _ctx):
        if at < PACKET+7 and at+size > PACKET:
            self.packet_reads.append((at-PACKET, size))

    def run(self, at, rcx=0, rdx=0, r8=0, r9=0):
        sp = STACK + 0x8008
        self.put(sp, STOP)
        for reg, value in ((UC_X86_REG_RSP, sp), (UC_X86_REG_RCX, rcx),
                           (UC_X86_REG_RDX, rdx), (UC_X86_REG_R8, r8),
                           (UC_X86_REG_R9, r9)):
            self.u.reg_write(reg, value)
        self.stopped = False
        self.u.emu_start(at, STOP+1, count=20000)
        if not self.stopped:
            raise AssertionError('INSTRUCTION_BUDGET_OR_UNEXPECTED_RETURN')
        return self.u.reg_read(UC_X86_REG_RAX)


def response_case(body, status, quantity, consumed, ui=True):
    f = Fixture(body)
    f.u.mem_write(PACKET, bytes((0xe2, 0xb7, 7, 0, 0xda, 0xb, status)))
    f.put(BASE+0xdec090, GLOBAL)
    f.put(GLOBAL, VTABLE)
    f.put(VTABLE+0x120, FETCH_ITEM)
    f.put(GLOBAL+0xab88, 1, 4)
    f.put(GLOBAL+0xab74, 17, 4)
    f.put(GLOBAL+0xaba4, 5, 4)
    f.put(GLOBAL+0x7958, 40000)
    f.put(MERIT+0x1b0, COSTS)
    f.put(COSTS+4, 30000, 4)
    f.put(ITEM+0x20, META)
    f.put(ITEM+0x80, quantity)
    f.put(META+0x178, 0xb0, 4)
    f.put(META+0x264, 999, 4)
    events = []

    def selection():
        f.put(f.u.reg_read(UC_X86_REG_RDX), 51+47, 4)
        f.put(f.u.reg_read(UC_X86_REG_R8), consumed, 4)
        return 1

    def remove():
        events.append(('remove', f.u.reg_read(UC_X86_REG_RDX)))
        return 0

    def reset_category():
        events.append(('reset_category', f.u.reg_read(UC_X86_REG_RDX),
                       f.u.reg_read(UC_X86_REG_R8), f.u.reg_read(UC_X86_REG_R9)))
        return 0

    f.stubs = {
        BASE+0x2437c8: lambda: MERIT,
        BASE+0x678804: lambda: UI if ui else 0,
        BASE+0x243924: lambda: 1,
        BASE+0x243894: selection,
        FETCH_ITEM: lambda: ITEM,
        BASE+0x36a010: remove,
        BASE+0x7f8e50: lambda: 0,  # final item refresh, not quantity setter
        BASE+0x37f9d8: reset_category,  # native category tree external service
        BASE+0x365e44: lambda: 0,
        BASE+0x245028: lambda: 0,
        BASE+0x24d128: lambda: 0,
        BASE+0x24d01c: lambda: 0,
        BASE+0x242824: lambda: events.append(('pending_reset',)) or 0,
    }

    def stop_before_render(u, at, _size, _ctx):
        if at == BASE+0x6daabc:
            f.stopped = True
            u.emu_stop()

    f.u.hook_add(UC_HOOK_CODE, stop_before_render)
    f.run(BASE+0x6da920, PACKET)
    active = status != 0 and ui
    if f.get(GLOBAL+0xab88, 4) != (2 if active else 1):
        raise AssertionError('GRADE_WRITE')
    if f.get(GLOBAL+0x7958) != (10000 if active else 40000):
        raise AssertionError('WEXP_WRITE')
    expected = quantity-consumed if active and quantity > consumed else quantity
    if f.get(ITEM+0x80) != expected:
        raise AssertionError('PARTIAL_STACK_WRITE')
    if (('remove', 98) in events) != (active and quantity == consumed):
        raise AssertionError('FULL_STACK_REMOVE')
    if not active and ('pending_reset',) not in events:
        raise AssertionError('PENDING_NOT_CLEARED')
    if not active and (f.get(GLOBAL+0xab74, 4) != 17 or
                       f.get(GLOBAL+0xaba4, 4) != 5):
        raise AssertionError('FAILED_RESPONSE_CHANGED_GRADE_STATE')
    if active:
        if f.get(GLOBAL+0xaba4, 4) != 3 or f.get(GLOBAL+0xab74, 4) != 0:
            raise AssertionError('INITIAL_GRADE_STATE')
        if [e for e in events if e[0] == 'reset_category'] != [
                ('reset_category', 2, n, 0) for n in (1, 2, 3)]:
            raise AssertionError('CATEGORY_RESET')
    if f.packet_reads != [(6, 1)]:
        raise AssertionError(('PACKET_EXTENT', f.packet_reads))
    return {'status': status, 'ui_present': ui, 'before': quantity,
            'consumed': consumed, 'after_option64': expected,
            'removed_from_container': ('remove', 98) in events,
            'grade': 2 if active else 1,
            'packet_reads': f.packet_reads}


def quantity_case(body, raw):
    f = Fixture(body)
    f.put(ITEM+0x20, META)
    f.put(ITEM+0x80, raw)
    f.put(META+0x178, 0xb0, 4)
    f.put(META+0x264, 999, 4)
    got = f.run(BASE+0x7fae98, ITEM) & 0xffffffff
    if got != raw & 0xffffffff:
        raise AssertionError('B0_LOW_DWORD_GETTER')
    f.stubs[BASE+0x7f8e50] = lambda: 0
    f.run(BASE+0x802664, ITEM, 899)
    if f.get(ITEM+0x80) != 899:
        raise AssertionError('B0_WHOLE_OPTION_SETTER')
    return {'input_option64': hex(raw), 'client_quantity32': got,
            'option_after_set_899': 899}


def verify(path):
    body = Path(path).read_bytes()
    if hashlib.sha256(body).hexdigest() != SHA:
        raise ValueError('CLIENT_SHA_MISMATCH')
    responses = [response_case(body, *case) for case in (
        (0, 999, 100), (1, 999, 100), (2, 999, 100),
        (255, 999, 100), (1, 100, 100), (1, 999, 100, False),
    )]
    quantities = [quantity_case(body, raw) for raw in (
        1, 99, 100, 999, 1024, 65536, 0x1000003e7, 0x80000000000003e7,
    )]
    return {'client_sha256': SHA, 'response_opcode': '0x0BDA',
            'response_bytes_exercised': 7, 'response_cases': responses,
            'quantity_cases': quantities, 'status': 'EXACT_CLIENT_INSTRUCTIONS_PASS',
            'gui_and_inventory_container_services': 'STUBBED',
            'success_execution_stops': 'BEFORE_FINAL_GUI_RENDERING',
            'saved_inventory_option_mapping': 'NOT_ESTABLISHED_BY_GETTER_TEST',
            'worldsvr_or_sql_tested': False, 'deployment_ready': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('client')
    parser.add_argument('--output')
    args = parser.parse_args()
    report = json.dumps(verify(args.client), indent=2) + '\n'
    if args.output:
        Path(args.output).write_text(report, encoding='utf-8')
    else:
        print(report, end='')
