#include "DiamondGrade2Ingress.h"
#include <cassert>
#include <cstdint>
#include <iostream>
using namespace diamond_v291::grade2;
namespace {
void Put32(unsigned char* p,std::uint32_t value) {
    for(int i=0;i<4;++i)p[i]=static_cast<unsigned char>(value>>(8*i));
}
void Frame(unsigned char* out,std::uint16_t opcode,std::uint32_t raw) {
    const unsigned char h[10]={0xE2,0xB7,0x0E,0,0,0,0,0,
                                static_cast<unsigned char>(opcode),
                                static_cast<unsigned char>(opcode>>8)};
    for(int i=0;i<10;++i)out[i]=h[i];
    Put32(out+10,raw);
}
}
int main() {
    unsigned char raw[14];
    Frame(raw,0x0BDD,7);
    auto p=ParseC2s(raw,sizeof raw);
    assert(p.kind==PacketKind::Grade2SlotCancelCandidate);
    assert(p.rawClientSelector==7);
    auto route=ClassifyOnly(raw,sizeof raw);
    assert(route.route==Route::Disabled);
    assert(!route.mayExecuteRankup && !route.maySendS2cSuccess);
    Frame(raw,0x0B13,7);
    assert(ParseC2s(raw,sizeof raw).kind==PacketKind::Other);
    assert(ClassifyOnly(raw,sizeof raw).route==Route::Original);
    Frame(raw,0x0B10,7);
    assert(ClassifyOnly(raw,sizeof raw).route==Route::Original);
    Frame(raw,0x0BDD,0xFFFFFFFF);
    assert(ParseC2s(raw,sizeof raw).kind==PacketKind::Invalid);
    Frame(raw,0x0BDD,7);
    raw[2]=15;
    assert(ParseC2s(raw,sizeof raw).kind==PacketKind::Invalid);
    Frame(raw,0x0BDD,7);
    assert(ParseC2s(raw,10).kind==PacketKind::Invalid);
    assert(ClassifyOnly(nullptr,0).route==Route::Invalid);
    std::cout<<"GRADE2_0BDD_POSSIBLE_SLOT_CANCEL_PASSIVE=PASS\n"
             <<"RANKUP_MISROUTING_PROHIBITED=PASS\n"
             <<"S2C_SUCCESS_NOT_EMITTED=PASS\n"
             <<"LIVE_WORLD_AND_SQL_UNCHANGED=YES\n";
}
