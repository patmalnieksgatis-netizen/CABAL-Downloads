#!/usr/bin/env python3
"""Exercise pinned dispatch, WarExp save accounting and cmd47 clear semantics.

Original instructions execute in Unicorn with clock/network/SQL services
absent. This is not proof of a live owner lifetime or durable SQL commit.
No supplied game binaries or source are copied into the repository.
"""
import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'native/grade2-ingress'))
from verify_world_48_ticket_helper import segments, mapped
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
from unicorn.x86_const import *

WORLD_SHA='caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3'
DBA_SHA='474acd9fec66cde11a55458d77b6b352aacc2a003385d2e9b79fd817b1f4ffce'


class Image:
    def __init__(self, path, expected):
        self.raw=Path(path).read_bytes()
        if hashlib.sha256(self.raw).hexdigest()!=expected:
            raise ValueError('NATIVE_BINARY_PROFILE_DIFFERS')
        self.regions=segments(self.raw)

    def read(self, at, n):
        return mapped(self.raw,self.regions,at,n)



def audit_ack_queue(world):
    """Execute the original IPC-to-owner-queue conversion with service stubs."""
    u=Uc(UC_ARCH_X86,UC_MODE_64)
    for start,size in ((0x7de000,0x1000),(0xb2c000,0x2000),
                       (0x410000,0x1000),(0x35000000,0x10000)):
        u.mem_map(start,size)
    u.mem_write(0x7dec1d,world.read(0x7dec1d,0x7dec9a-0x7dec1d))
    arena=0x35000000
    source,copied,ctx,layer,stack=(arena+0x1000,arena+0x2000,
                                 arena+0x3000,arena+0x4000,arena+0x8000)
    frames=[]; allocation_ok=True

    def ret(value=0):
        sp=u.reg_read(UC_X86_REG_RSP)
        target=struct.unpack('<Q',u.mem_read(sp,8))[0]
        u.reg_write(UC_X86_REG_RAX,value)
        u.reg_write(UC_X86_REG_RSP,sp+8)
        u.reg_write(UC_X86_REG_RIP,target)

    def hook(uc,at,size,opaque):
        if at==0xb2c580:
            assert uc.reg_read(UC_X86_REG_RDI)==18
            ret(copied if allocation_ok else 0)
        elif at==0x410540:
            assert uc.reg_read(UC_X86_REG_RDI)==copied
            assert uc.reg_read(UC_X86_REG_RSI)==source
            assert uc.reg_read(UC_X86_REG_RDX)==18
            uc.mem_write(copied,bytes(uc.mem_read(source,18)))
            ret(copied)
        elif at==0xb2d370:
            assert uc.reg_read(UC_X86_REG_RDI)==layer
            queued=uc.reg_read(UC_X86_REG_RSI)
            user,packet,n=struct.unpack('<QQQ',uc.mem_read(queued,24))
            generation=struct.unpack('<I',uc.mem_read(queued+24,4))[0]
            assert (user,packet,n)==(ctx,copied,18)
            frames.append((bytes(uc.mem_read(packet,n)),generation))
            ret()
    u.hook_add(UC_HOOK_CODE,hook)
    cases=[]
    original=struct.pack('<HHI HII',0xb7e2,18,0,47,4242,2)
    for generation in (1,77,0xffffffff):
        for allocation_ok in (False,True):
            before=len(frames)
            u.mem_write(source,original)
            u.mem_write(ctx+0xe4,struct.pack('<I',generation))
            for register,value in ((UC_X86_REG_RBX,source),(UC_X86_REG_R12,ctx),
                                   (UC_X86_REG_R13,layer),(UC_X86_REG_RBP,stack),
                                   (UC_X86_REG_RSP,stack-0x200)):
                u.reg_write(register,value)
            u.emu_start(0x7dec1d,0x7dec9a,count=100)
            assert bytes(u.mem_read(source,18))==original
            if allocation_ok:
                expected=original[:8]+struct.pack('<H',2032)+original[10:]
                assert frames[-1]==(expected,generation) and len(frames)==before+1
            else:
                assert len(frames)==before
            cases.append(dict(generation=generation,allocation_ok=allocation_ok,
                              queued=len(frames)>before))
    return dict(ipc_command=47,itc_command=2032,bytes=18,cases=cases,
                original_packet_preserved=True,queue_service_substituted=True,
                session_lifetime_proven=False)


def audit(world_path, dba_path):
    world=Image(world_path,WORLD_SHA)
    dba=Image(dba_path,DBA_SHA)
    # These are field/order anchors, not guesses from the old SDK struct.
    pins=(
        (world,0xa41694,'490185f0160000'),
        (world,0xa416a4,'4d89bde0160000'),
        (world,0x8be6d8,'488b97e0160000'),
        (world,0x8be6df,'48899099000000'),
        (world,0x8be6e6,'488b97e8160000'),
        (world,0x8be6ed,'488990a1000000'),
        (world,0x8be6f4,'488b97f0160000'),
        (world,0x8be6fb,'488990a9000000'),
        (dba,0x53730e,'488bb399000000'),
        (dba,0x537321,'488bb3a1000000'),
        (dba,0x537334,'488bb3a9000000'),
        (world,0xb2e48d,'49837e3801'),
        (world,0xb2e494,'41807f2000'),
    )
    for image,at,hex_bytes in pins:
        if image.read(at,len(bytes.fromhex(hex_bytes)))!=bytes.fromhex(hex_bytes):
            raise ValueError('NATIVE_INSTRUCTION_CHANGED:'+hex(at))
    declaration=dba.read(0x600960,18000).split(b'\0',1)[0].decode('ascii')
    parameters=re.findall(r':(\w+)<',declaration)
    if parameters[63:66]!=['WarExpStatus','warExpEarn','warExpUsed']:
        raise ValueError('NATIVE_SQL_BINDING_ORDER_CHANGED')

    u=Uc(UC_ARCH_X86,UC_MODE_64)
    for start,size in ((0xa41000,0x1000),(0x8be000,0x1000),(0x537000,0x1000),
                       (0x452000,0x1000),(0xb2e000,0x1000),(0xb49000,0x1000),
                       (0x410000,0x2000),(0x30000000,0x40000),
                       (0x7de000,0x2000),(0xadd000,0x1000),
                       (0x2163000,0x1000),(0x75d000,0x1000)):
        u.mem_map(start,size)
    u.mem_write(0xa41694,world.read(0xa41694,0x17))
    u.mem_write(0x8be6d8,world.read(0x8be6d8,0x2a))
    u.mem_write(0x53730e,dba.read(0x53730e,0x39))
    # Includes the original branches to lock/unlock blocks at 0xB2E930/918.
    u.mem_write(0xb2e000,world.read(0xb2e000,0x1000))
    u.mem_write(0x7ded30,world.read(0x7ded30,0x190))
    u.mem_write(0xa41788,world.read(0xa41788,0x1d))
    arena=0x30000000
    user,payload,sql_frame,stack,layer,proc,ctx=(arena,arena+0x2000,arena+0x4000,
                                              arena+0x7000,arena+0x8000,
                                              arena+0x9000,arena+0xa000)
    sql_values=[];events=[];sent=[];depth=0;handler_result=0

    def put(at,value,width=8):
        u.mem_write(at,value.to_bytes(width,'little'))

    def get(at,width=8):
        return int.from_bytes(u.mem_read(at,width),'little')

    def ret(value=0):
        sp=u.reg_read(UC_X86_REG_RSP)
        target=get(sp)
        u.reg_write(UC_X86_REG_RAX,value)
        u.reg_write(UC_X86_REG_RSP,sp+8)
        u.reg_write(UC_X86_REG_RIP,target)

    def hook(uc,at,_size,_ctx):
        nonlocal depth
        if at==0x452b60:
            if uc.reg_read(UC_X86_REG_RDI)!=sql_frame-0xd0:
                raise AssertionError('SQL_STATEMENT_CONTEXT')
            sql_values.append(uc.reg_read(UC_X86_REG_RSI));ret()
        elif at in (0x410750,0x410890):
            if uc.reg_read(UC_X86_REG_RDI)!=0x23685e0:
                raise AssertionError('DISPATCH_MUTEX_ADDRESS')
            depth+=1 if at==0x410750 else -1
            events.append(('lock' if at==0x410750 else 'unlock',depth));ret()
        elif at==0xb49750:
            if tuple(uc.reg_read(r) for r in (UC_X86_REG_RDI,UC_X86_REG_RSI,UC_X86_REG_RDX))!=(proc,layer,ctx):
                raise AssertionError('CALLPROC_ARGUMENTS')
            events.append(('handler',depth));ret(handler_result)
        elif at==0xadd2c0:
            # Native session lookup is substituted, not claimed as a proven
            # session lifetime lock. Execute the complete original ACK paths.
            if uc.reg_read(UC_X86_REG_RSI)!=4242:
                raise AssertionError('ACK_CHARACTER_LOOKUP')
            ret(ctx)
        elif at==0x75d4e0:
            # Capture the native call ABI only; do not emulate a socket or
            # assert a real network send. Client reader proof is separate.
            target=uc.reg_read(UC_X86_REG_RDI)
            packet=uc.reg_read(UC_X86_REG_RSI)
            size=uc.reg_read(UC_X86_REG_RDX)
            if target!=ctx or size!=7:
                raise AssertionError('NATIVE_STATUS_SEND_ARGUMENTS')
            sent.append(bytes(uc.mem_read(packet,size)).hex());ret()

    u.hook_add(UC_HOOK_CODE,hook)
    cases=[]
    for balance,earned,used,cost in ((40000,90000,7,30000),
                                    (30000,30000,0,30000),
                                    (10**12,10**12+1,12345,30000)):
        for offset,value in ((0x16e0,balance),(0x16e8,earned),(0x16f0,used)):
            put(user+offset,value)
        for reg,value in ((UC_X86_REG_R13,user),(UC_X86_REG_R15,balance),
                          (UC_X86_REG_RAX,cost),(UC_X86_REG_RBP,stack)):
            u.reg_write(reg,value)
        u.emu_start(0xa41694,0xa416ab,count=30)
        expected=(balance-cost,earned,used+cost)
        if tuple(get(user+x) for x in (0x16e0,0x16e8,0x16f0))!=expected:
            raise AssertionError('NATIVE_SPEND_COUNTERS')
        u.reg_write(UC_X86_REG_RDI,user);u.reg_write(UC_X86_REG_RAX,payload)
        u.emu_start(0x8be6d8,0x8be702,count=30)
        if tuple(get(payload+x) for x in (0x99,0xa1,0xa9))!=expected:
            raise AssertionError('NATIVE_SAVE_FIELDS')
        sql_values.clear()
        for reg,value in ((UC_X86_REG_RBX,payload),(UC_X86_REG_RBP,sql_frame),
                          (UC_X86_REG_RSP,stack)):
            u.reg_write(reg,value)
        u.emu_start(0x53730e,0x537347,count=80)
        if tuple(sql_values)!=expected:
            raise AssertionError('DBAGENT_NAMED_BIND_VALUES')
        cases.append({'before':[balance,earned,used],'cost':cost,'saved_and_bound':sql_values[:]})

    guards=[]
    for layer_field in (0,1,2,15):
        for locking in (0,1):
            for handler_result in (0,7):
                depth=0;events.clear()
                put(layer+0x38,layer_field);put(proc+0x20,locking,1)
                for reg,value in ((UC_X86_REG_R14,layer),(UC_X86_REG_R15,proc),
                                  (UC_X86_REG_R12,ctx),(UC_X86_REG_RBP,stack),
                                  (UC_X86_REG_RSP,stack-0x200)):
                    u.reg_write(reg,value)
                u.emu_start(0xb2e48d,0xb2e4c5,count=80)
                protected=layer_field>1 and locking!=0
                expected=[('lock',1),('handler',1),('unlock',0)] if protected else [('handler',0)]
                if events!=expected or depth!=0:
                    raise AssertionError(('DISPATCH_SCOPE',events,expected))
                guards.append({'layer_field38':layer_field,'map_locking':locking,
                               'handler_result':handler_result,'protected':protected})

    # cmd47 clears each selected pending word and status using only CharIdx
    # and flags. These fields are NOT an operation-specific save receipt.
    put(ctx+0xe8,user);put(proc+8,payload)
    put(payload+10,4242,4)
    pending_offsets=(0x2b7b8,0x2b7c0,0x2b7c8)
    status_offsets=(0x2b7e0,0x2b7e4,0x2b7e8)
    flag_bits=(0x2000,0x200,2)
    put(user+0x2b7f6,0,1)  # skip unrelated client notification service
    ack_cases=[]

    def run_ack(flags):
        put(payload+14,flags,4)
        u.reg_write(UC_X86_REG_RSI,proc)
        u.reg_write(UC_X86_REG_RSP,stack)
        u.emu_start(0x7ded30,0x7ded94,count=120)

    for mask in range(8):
        flags=sum(bit for i,bit in enumerate(flag_bits) if mask&(1<<i))
        for off,value in zip(pending_offsets,(3,4,5)):put(user+off,value)
        for off,value in zip(status_offsets,(11,22,33)):put(user+off,value,4)
        run_ack(flags)
        actual=tuple(get(user+off) for off in pending_offsets)
        statuses=tuple(get(user+off,4) for off in status_offsets)
        expected=tuple(0 if flags&bit else n for bit,n in zip(flag_bits,(3,4,5)))
        expected_status=tuple(0 if flags&bit else n for bit,n in zip(flag_bits,(11,22,33)))
        if actual!=expected or statuses!=expected_status:
            raise AssertionError(('NATIVE_ACK_CLEAR_SEMANTICS',flags,actual,statuses))
        ack_cases.append({'flags':hex(flags),'pending_before':[3,4,5],
                          'pending_after':list(actual),'status_after':list(statuses)})
    # A repeated identical ACK also clears newly set pending state. Therefore
    # merely observing zero native words cannot establish unique completion.
    put(user+pending_offsets[0],1);put(user+status_offsets[0],7,4)
    run_ack(0x2202)
    if get(user+pending_offsets[0])!=0 or get(user+status_offsets[0],4)!=0:
        raise AssertionError('REPEATED_ACK_CLEAR_SEMANTICS')

    # Original Platinum success reply: the handler passes USERCONTEXT*, a
    # seven-byte B7E2 status packet, and byte count 7 to the native sender.
    u.mem_write(stack-0x107,bytes.fromhex('e2b70700100b00'))
    u.reg_write(UC_X86_REG_RBP,stack);u.reg_write(UC_X86_REG_RSP,stack-0x200)
    u.reg_write(UC_X86_REG_R12,ctx)
    u.emu_start(0xa41788,0xa417a5,count=50)
    if sent!=['e2b70700100b01']:
        raise AssertionError('NATIVE_SEVEN_BYTE_STATUS_REPLY')
    return {'status':'PINNED_NATIVE_INSTRUCTIONS_PASS','world_sha256':WORLD_SHA,
            'dba_sha256':DBA_SHA,'accounting_cases':cases,'dispatch_cases':guards,
            'native_wexp_offsets':{'current':'0x16E0','earned':'0x16E8','used':'0x16F0'},
            'packed_body_offsets':{'current':'0x99','earned':'0xA1','used':'0xA9'},
            'dbagent_parameters_1_based':{'WarExpStatus':64,'warExpEarn':65,'warExpUsed':66},
            'dispatch_mutex':'0x23685E0','dispatch_mutex_scope':'GLOBAL_CONDITIONAL',
            'cmd47_ack_cases':ack_cases,
            'owner_queue_conversion':audit_ack_queue(world),
            'cmd47_pending_qword_offsets':[hex(x) for x in pending_offsets],
            'cmd47_status_dword_offsets':[hex(x) for x in status_offsets],
            'cmd47_flag_bits':[hex(x) for x in flag_bits],
            'identical_repeated_ack_clears_new_pending_state':True,
            'native_pending_words_prove_unique_operation_completion':False,
            'native_status_reply_call':{'call_site':'0xA417A0','sender':'0x75D4E0',
                'arguments':['USERCONTEXT*','packet*','7'],
                'observed_original_platinum_reply':sent[0],
                'socket_service_substituted':True,'network_send_tested':False},
            'per_character_lifetime_or_save_fence_proven':False,
            'sql_executed':False,'server_or_client_modified':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--world',required=True,type=Path)
    p.add_argument('--dba',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    result=audit(a.world,a.dba)
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(result['status']+'; ACCOUNTING_CASES='+str(len(result['accounting_cases']))+
          '; DISPATCH_CASES='+str(len(result['dispatch_cases']))+
          '; ACK_CASES='+str(len(result['cmd47_ack_cases']))+'; SQL_EXECUTED=NO')
