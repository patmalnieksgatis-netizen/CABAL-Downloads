"""Read the native slot12 refusal conditions, without remote calls or writes."""
import base64,hashlib,json,os,subprocess
from pathlib import Path

INNER=r'''import hashlib,json,os,struct,subprocess
from pathlib import Path
def need(ok,why):
 if not ok:raise RuntimeError(why)
p=subprocess.check_output(['supervisorctl','pid','WorldSvr_01_01'],text=True).strip()
need(p.isdigit() and int(p)>0,'WORLD_NOT_RUNNING')
proc=Path('/proc')/p
need(hashlib.sha256((proc/'exe').read_bytes()).hexdigest()=='caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3','WORLD_PROFILE_DIFFERS')
ranges=[]
for row in (proc/'maps').read_text().splitlines():
 w=row.split()
 if 'r' in w[1]:ranges.append(tuple(int(x,16) for x in w[0].split('-')))
fd=os.open(proc/'mem',os.O_RDONLY)
def read(at,n):
 need(0<n<=256 and any(a<=at and at+n<=b for a,b in ranges),'READ_OUTSIDE_MAPPED_RANGE')
 b=os.pread(fd,n,at);need(len(b)==n,'SHORT_READ');return b
def number(at,n=8):return int.from_bytes(read(at,n),'little')
def gate12():
 manager=number(0x234b618);flag=bool(number(manager+0xb040,1)&0x20)
 if not flag:return False
 sentinel=manager+0xb148;node=number(manager+0xb150);candidate=sentinel;seen=set()
 for _ in range(64):
  if not node:break
  need(node not in seen,'GATE_TREE_CHANGED');seen.add(node)
  if 12<=number(node+0x20,1):candidate=node;node=number(node+0x10)
  else:node=number(node+0x18)
 else:raise RuntimeError('GATE_TREE_TOO_DEEP')
 return candidate!=sentinel and 12>=number(candidate+0x20,1)
try:
 # Pinned ADD1E0 native lookup uses this manager's RB-tree: root+10,
 # node key+20 and USERCONTEXT pointer+28. ADD2C0 then reads userdata+E8.
 manager=number(0x234b0c8);header=read(manager+8,40)
 root=number(manager+0x10);count=number(manager+0x28)
 need(count<=8,'NOT_A_SMALL_TEST_SESSION_POOL')
 todo=[root] if root else [];seen=set();rows=[]
 while todo:
  node=todo.pop();need(node not in seen and len(seen)<8,'SESSION_TREE_CHANGED');seen.add(node)
  data=read(node,48);left=int.from_bytes(data[16:24],'little');right=int.from_bytes(data[24:32],'little')
  if left:todo.append(left)
  if right:todo.append(right)
  context=int.from_bytes(data[40:48],'little');user=number(context+0xe8)
  if not user or not number(user+0x1570,4):continue
  account=number(user+0x890,4);character=number(user+0xa24,4)
  need(account and character//16==account,'SESSION_IDENTITY_DIFFERS')
  slots=[];saved=[]
  for slot in (12,33,34):
   at=user+0x4a60+slot*0x48;b=read(at,16);saved.append((at,b))
   kind=int.from_bytes(b[8:16],'little')
   slots.append(dict(slot=slot,index=int.from_bytes(b[:4],'little'),count=int.from_bytes(b[4:8],'little'),kind=kind))
  need(all(read(at,16)==b for at,b in saved),'EQUIPMENT_CHANGED_DURING_READ')
  rows.append(dict(character=character,slots=slots))
 need(len(seen)==count and read(manager+8,40)==header,'SESSION_TREE_CHANGED')
 print(json.dumps(dict(pid=int(p),native_slot12_gate_denied=gate12(),sessions=rows)))
 print('GUARDIAN_SLOT_STATE_READ_ONLY_COMPLETE')
finally:os.close(fd)
'''

def main():
    if os.geteuid()!=0 or Path('/sys/class/dmi/id/product_uuid').read_text().strip().lower()!='7632fb78-37a0-f645-97c0-dc322c50b002':
        raise SystemExit('WRONG_TEST_VM_OR_ROOT_REQUIRED')
    p=subprocess.run(['docker','exec','-i','cabal_main','python3','-'],input=INNER.encode())
    raise SystemExit(p.returncode)

if __name__=='__main__':main()
