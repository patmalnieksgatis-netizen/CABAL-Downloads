#!/usr/bin/env python3
"""V16: fix candidate packet-length field width using the archived WORD ABI.
Recreate verified source copies, test the field width with nonzero adjacent
bytes, and build offline only. Runtime v291 width is not yet attested.
No live library replacement, SQL connection, VM restart or network change.
"""
import hashlib,importlib.util,pathlib,subprocess,sys,tempfile
sys.dont_write_bytecode=True
OLD=pathlib.Path("/tmp/cabal-diamond-gcc14-v14-pvb1trlo")
DEPS=OLD/"dependencies"
SRC=pathlib.Path("/root/CABAL_V282_LIVE_MERGE_CANDIDATE_v14/source_tree/src")
BLOBS={
"worldsvr-ingress/Build-DiamondV14Real0BDAOffline.py":"127df1593a669b9293480cd217af6e8cced60e8d",
"worldsvr-ingress/Apply-DiamondV14BoundClone.py":"68c656912544d184b28bcd0e41e594de1ba2a639",
"worldsvr-ingress/Apply-DiamondV14Real0BDAClone.py":"978d8296e63d0c8db96c73d598987bc45bf0a5b2",
"worldsvr-ingress/DiamondIngress.h":"9eabfd4340153c944d8da7abdb9d9a2c41fc4aec",
"worldsvr-ingress/DiamondBoundIngress.h":"3e6a18ecbd50c14dbdda4ecd4dbf1acf6f040610",
"worldsvr-ingress/DiamondReal0BDAIngressPort.h":"acca51f297e881444ae9b616480996c14c00168a",
"native/diamond_abi.h":"187db3ce8e588812eb5dfc291238ebad755feec0",
"native/diamond_world_bridge.h":"8750a6cf084a06f80ff5cc372ceaf49dcaad4b93",
"native/diamond_merit_world_entry.h":"34b6b941150992c6877d50df9e7bb534e7870b35",
"native/diamond_merit_world_entry.cpp":"488a6d1e9e1885c668fb53a711d93d064728f2ab",
"worldsvr-ingress/Build-DiamondV14-GCC14Candidates-V13.py":"dccc8d388251734baddca203b8c4326b1035a9c6",
}
TEST=r'''
#include "include/Types.h"
#include "hooks/Handlers/DiamondReal0BDAIngressPort.h"
#include <cassert>
#include <cstdint>
#include <cstring>
#include <type_traits>
int main(){
    static_assert(std::is_same<decltype(PROCESSDATACONTEXT::iLen),std::uint16_t>::value,"length is WORD");
    static_assert(offsetof(PROCESSDATACONTEXT,iLen)==16,"length offset");
    static_assert(sizeof(PROCESSDATACONTEXT)>=24,"context prefix size");
    PROCESSDATACONTEXT c{};
    const unsigned char lengthAndAdjacent[8]={14,0,0xA5,0x5A,0x34,0x12,0xEF,0xCD};
    std::memcpy(reinterpret_cast<unsigned char*>(&c)+16,lengthAndAdjacent,8);
    assert(c.iLen==14);
    unsigned char packet[14]={0xE2,0xB7,14,0,0,0,0,0,0xDA,0x0B,1,0,3,0};
    assert(DiamondReal0BDAIngressPort::IsCandidate(packet,c.iLen));
    assert(!DiamondReal0BDAIngressPort::IsCandidate(packet,13));
    packet[8]=0x10;
    assert(!DiamondReal0BDAIngressPort::IsCandidate(packet,c.iLen));
    int result=123;
    assert(!DiamondReal0BDAIngressPort::Process(nullptr,packet,c.iLen,&result));
    assert(result==123);
}
'''
def load(name):
    spec=importlib.util.spec_from_file_location(name.replace("-","_"),DEPS/"worldsvr-ingress"/name)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
def main():
    for rel,want in BLOBS.items():
        p=DEPS/rel
        if not p.is_file():raise RuntimeError("missing verified V14 dependency: "+str(p))
        data=p.read_bytes()
        if hashlib.sha1(("blob "+str(len(data))+"\0").encode()+data).hexdigest()!=want:
            raise RuntimeError("dependency hash mismatch: "+str(p))
    base=load("Apply-DiamondV14BoundClone.py")
    if base.manifest(SRC)!=(base.V14_FILE_COUNT,base.V14_TREE_SHA):
        raise RuntimeError("original V14 manifest mismatch")
    v4=load("Build-DiamondV14Real0BDAOffline.py")
    v13=load("Build-DiamondV14-GCC14Candidates-V13.py")
    work=pathlib.Path(tempfile.mkdtemp(prefix="cabal-diamond-gcc14-v16-",dir="/tmp"))
    stage=work/"stage";stage.mkdir()
    v4.minimal_pure_0bda_patch(SRC,stage/"minimal-source",base)
    v4.passive_observer_patch(stage/"minimal-source",stage/"observer-source")
    load("Apply-DiamondV14Real0BDAClone.py").patch(SRC,stage/"source")
    for p in (stage/"observer-source",stage/"source"):
        f=p/"include/Types.h";s=f.read_text()
        if s.count("std::size_t iLen;")!=1:raise RuntimeError("unexpected context declaration "+str(f))
        f.write_text(s.replace("std::size_t iLen;","std::uint16_t iLen;",1))
    tests=work/"tests";tests.mkdir()
    (tests/"context_test.cpp").write_text(TEST)
    for key in ("observer-source","source"):
        path=stage/key
        exe="/tests/context-"+key
        mount=["docker","run","--rm","--network","none","--read-only","--tmpfs","/tmp:rw,nosuid,size=128m",
               "--mount","type=bind,src="+str(path)+",dst=/source,readonly",
               "--mount","type=bind,src="+str(tests)+",dst=/tests",v13.IMAGE]
        v13.run(mount+["g++-14","-std=c++17","-O2","-I/source","/tests/context_test.cpp","-o",exe],timeout=90)
        v13.run(mount+[exe],timeout=30)
        print("DIAMOND_V16_LENGTH_WIDTH_SYNTHETIC_PASS="+key,flush=True)
    v13.STAGE=stage;v13.OUT=work/"build"
    v13.main()
    if base.manifest(SRC)!=(base.V14_FILE_COUNT,base.V14_TREE_SHA):raise RuntimeError("original source changed")
    print("DIAMOND_V16_RESULT_PATH="+str(v13.OUT),flush=True)
    print("DIAMOND_V16_RUNTIME_LENGTH_ATTESTED=NO")
    print("DIAMOND_V16_INSTALL_ALLOWED=NO")
    print("DIAMOND_V16=OFFLINE_CONTEXT_WIDTH_BUILD_COMPLETE")
if __name__=="__main__":
    try:main()
    except Exception as e:
        print("DIAMOND_V16=STOP: "+str(e),file=sys.stderr)
        sys.exit(2)
