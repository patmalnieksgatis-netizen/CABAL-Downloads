#include "../DiamondReal0BDAIngressPort.h"
#include <array>
#include <cassert>
#include <cstdint>
#include <iostream>
using namespace DiamondReal0BDAIngressPort;

int main(){
    std::array<unsigned char,14> b{
        0xE2,0xB7,0x0E,0,0,0,0,0,0xDA,0x0B,1,0,5,0
    };
    int ret=1234;int fakeUser=4;
    assert(IsCandidate(b.data(),b.size()));
    assert(!Process(&fakeUser,b.data(),b.size(),&ret));
    assert(ret==1234);
    HostBinding fake{};
    fake.trustedHost=&fakeUser;
    assert(!InstallVerifiedHost(&fake));
    b[8]=0x10; // Platinum 0B10
    assert(!IsCandidate(b.data(),b.size()));
    assert(!Process(&fakeUser,b.data(),b.size(),&ret));
    b[8]=0xF3;b[9]=0x09; // old Merit Mastery 09F3
    assert(!IsCandidate(b.data(),b.size()));
    b[8]=0xDA;b[9]=0x0B;
    b[2]=0x0F;
    assert(!IsCandidate(b.data(),b.size())); // bad frame length
    b[2]=0x0E;b[10]=0;
    assert(!IsCandidate(b.data(),b.size())); // no slots
    b[10]=1;b[0]=0xE3;
    assert(!IsCandidate(b.data(),b.size())); // wrong packet magic
    b[0]=0xE2;
    assert(!IsCandidate(nullptr,b.size()));
    assert(!IsCandidate(b.data(),13)); // malformed
    assert(ret==1234);
    std::cout<<"V14_SOURCE_0BDA_OPCODE_MATCH_WITH_ORIGINAL_PASSTHROUGH=PASS\n"
             <<"V14_SOURCE_PUBLISHABLE_HOOK_DEFAULT_BINDER_UNAVAILABLE=PASS\n"
             <<"V14_SOURCE_PLATINUM_AND_MERIT_NOT_CONSUMED=PASS\n"
             <<"LIVE_GAME_SQL_MUTATIONS=NO\n";
}
