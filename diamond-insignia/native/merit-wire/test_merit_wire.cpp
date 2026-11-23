#include "DiamondMeritWire.h"
#include <array>
#include <cassert>
#include <cstdint>
#include <iostream>
using namespace cabal::merit_wire;
int main() {
    const std::array<std::uint8_t,18> valid{
      0xE2,0xB7,0x12,0x00, 0xA5,0xA6,0xA7,0xA8,
      0xF3,0x09, 0x9F,0x00,0x00,0x00, 0x01,0x00,0x00,0x00};
    LegacyRequest parsed{99,99,99};
    assert(ParseLegacyRequest(valid.data(),valid.size(),parsed)==ParseStatus::Ok);
    assert(parsed.checksum==0xA8A7A6A5u && parsed.value0==159 && parsed.value1==1);
    assert(EncodeLegacyResult(true)==(std::array<std::uint8_t,7>{0xE2,0xB7,7,0,0xF3,9,1}));
    assert(EncodeLegacyResult(false)==(std::array<std::uint8_t,7>{0xE2,0xB7,7,0,0xF3,9,0}));
    auto bad=valid;
    assert(ParseLegacyRequest(nullptr,18,parsed)==ParseStatus::Null);
    assert(ParseLegacyRequest(valid.data(),10,parsed)==ParseStatus::WrongLength);
    assert(parsed.value0==0 && parsed.value1==0);
    bad[0]=0;
    assert(ParseLegacyRequest(bad.data(),bad.size(),parsed)==ParseStatus::WrongMagic);
    bad=valid;bad[2]=0x11;
    assert(ParseLegacyRequest(bad.data(),bad.size(),parsed)==ParseStatus::HeaderLengthMismatch);
    bad=valid;bad[8]=0x10;
    assert(ParseLegacyRequest(bad.data(),bad.size(),parsed)==ParseStatus::WrongCommand);
    for(size_t i=0;i<valid.size();++i) {
        assert(ParseLegacyRequest(valid.data(),i,parsed)==ParseStatus::WrongLength);
    }
    std::cout<<"WORLD_V14_LEGACY_MERIT_WIRE_TEST=PASS\n";
    std::cout<<"0x09F3_FIELDS_PROVEN_18B_EXACT_SIZE_UNVERIFIED;S2C_7B=PROVEN\n";
    std::cout<<"DIAMOND_V291_OPCODE_AND_REPLY=NOT_YET_PROVEN\n";
}
