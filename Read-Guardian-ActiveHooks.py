"""Read only the pinned Guardian's live code routes; no player/session memory.

READY/module presence is not live hook ownership. This reports the current
targets without installing, rewriting hooks, restarting or executing game code.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess

VM='7632fb78-37a0-f645-97c0-dc322c50b002'
WORLD='caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3'
MODULE='e9c95a43c0804ad21e75bd6a4e2333f7ead526f0577d009eccd1d231ee087717'
NAME='GuardianArcana-v1.so'
SITES=[('move',0xa1baa0,0x1c60),('swap',0xa1bda0,0x2340),
       ('mode',0xae68c0,0x22b0),('hold',0xa184e0,0x2010),
       ('put',0xa18940,0x1f70),('apply',0x7b3060,0x2190),
       ('recalc',0x7b3230,0x2220),('broadcast_equip',0x7dc440,0x20d0),
       ('broadcast_unequip',0x7dc630,0x1d30),
       ('predicate_apply_call',0x7b3147,0x2130),
       ('predicate_put_call',0xa190c1,0x2130),
       ('predicate_move_call',0xa1c9de,0x2130)]


def need(value,code):
    if not value:raise RuntimeError(code)


def run(args):
    return subprocess.check_output(args,timeout=15,text=True).strip()


def main():
    need(os.geteuid()==0 and Path('/sys/class/dmi/id/product_uuid').read_text().strip().lower()==VM,
         'WRONG_TEST_VM_OR_ROOT_REQUIRED')
    inner=run(['docker','exec','cabal_main','supervisorctl','pid','WorldSvr_01_01'])
    need(inner.isdigit() and int(inner)>0,'WORLD_NOT_RUNNING')
    matches=[]
    for pid in run(['docker','top','cabal_main','-eo','pid']).split():
        if not pid.isdigit():continue
        p=Path('/proc')/pid
        try:m=re.search(r'^NSpid:\s+([0-9 \t]+)$',(p/'status').read_text(),re.M)
        except FileNotFoundError:continue
        if m and m[1].split()[-1]==inner:matches.append(p)
    need(len(matches)==1,'WORLD_HOST_PID_NOT_UNIQUE')
    p=matches[0]
    need(hashlib.sha256((p/'exe').read_bytes()).hexdigest()==WORLD,'WORLD_PROFILE_CHANGED')
    regions=[]
    for line in (p/'maps').read_text().splitlines():
        w=line.split(maxsplit=5);a,b=(int(v,16) for v in w[0].split('-'))
        regions.append((a,b,w[1],int(w[2],16),w[5] if len(w)>5 else 'anonymous'))
    paths={r[4] for r in regions if Path(r[4]).name==NAME}
    need(len(paths)==1,'GUARDIAN_MODULE_NOT_UNIQUE')
    path=next(iter(paths))
    need(hashlib.sha256((p/'root'/path.lstrip('/')).read_bytes()).hexdigest()==MODULE,'GUARDIAN_MODULE_PROFILE_CHANGED')
    base=min(r[0]-r[3] for r in regions if r[4]==path)
    def owner(at):
        return next((Path(r[4]).name for r in regions if r[0]<=at<r[1]),'UNMAPPED')
    results=[]
    with (p/'mem').open('rb',buffering=0) as f:
        def code(at,n):
            need(any(a<=at and at+n<=b and 'r' in perm for a,b,perm,_,_ in regions),'CODE_NOT_READABLE')
            data=os.pread(f.fileno(),n,at);need(len(data)==n,'SHORT_CODE_READ');return data
        for name,site,offset in SITES:
            target=site;chain=[];error=None;wanted=base+offset
            try:
                for hop in range(5):
                    chain.append(dict(Address=hex(target),Owner=owner(target)))
                    if target==wanted:break
                    b=code(target,16)
                    if b[0] in (0xe8,0xe9):target=target+5+struct.unpack_from('<i',b,1)[0]
                    elif b[:2]==b'\xff\x25':
                        slot=target+6+struct.unpack_from('<i',b,2)[0]
                        target=struct.unpack('<Q',code(slot,8))[0]
                    elif b[:2]==b'\x48\xb8' and b[10:12]==b'\xff\xe0':target=struct.unpack_from('<Q',b,2)[0]
                    else:break
            except (RuntimeError,OSError) as e:error=str(e)
            row=dict(Hook=name,ExpectedDirectRoute=target==wanted,Chain=chain)
            if error:row['ReadError']=error
            results.append(row)
    for row in results:print(json.dumps(row,separators=(',',':')))
    print('GUARDIAN_LIVE_DIRECT_ROUTES='+str(sum(r['ExpectedDirectRoute'] for r in results))+'/12; READ_ONLY_COMPLETE')
    print('NOTE=OTHER_ENTRY_CAN_CHAIN_INDIRECTLY; NO_AUTOMATIC_REPATCH_OR_RESTART')


if __name__=='__main__':
    try:main()
    except Exception as e:
        print('GUARDIAN_ROUTE_READ_STOPPED; '+str(e),flush=True)
        raise SystemExit(1)
