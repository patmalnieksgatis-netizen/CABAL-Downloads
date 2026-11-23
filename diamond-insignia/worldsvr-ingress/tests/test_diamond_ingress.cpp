#include "../DiamondIngress.h"
#include <array>
#include <cassert>
#include <iostream>
using namespace DiamondIngress;
void u16(std::array<std::uint8_t,18>& a,unsigned i,std::uint16_t v){a[i]=v&0xff;a[i+1]=v>>8;}
void u32(std::array<std::uint8_t,18>& a,unsigned i,std::uint32_t v){for(unsigned j=0;j<4;++j)a[i+j]=static_cast<std::uint8_t>(v>>(j*8));}
int main(){
    std::array<std::uint8_t,18> b{};u16(b,0,kClassicMagic);u16(b,2,18);u16(b,8,kMasteryLevelUp);
    u32(b,10,159);u32(b,14,0xfeed01u);
    auto r=Inspect(b.data(),b.size());assert(r.candidate && r.mastery_id==159 && r.second_field==0xfeed01u);
    u32(b,10,474);assert(Inspect(b.data(),b.size()).candidate);
    u32(b,10,158);assert(!Inspect(b.data(),b.size()).candidate);
    u32(b,10,475);assert(!Inspect(b.data(),b.size()).candidate);
    u32(b,10,159);u16(b,8,0x0B10);assert(!Inspect(b.data(),b.size()).candidate);
    u16(b,8,kMasteryLevelUp);u16(b,2,17);assert(!Inspect(b.data(),b.size()).candidate);
    u16(b,2,18);u16(b,0,0xc8f3);assert(!Inspect(b.data(),b.size()).candidate);
    u16(b,0,kClassicMagic);assert(!Inspect(b.data(),17).candidate);
    assert(!Inspect(nullptr,18).candidate);
    assert(!Enabled());assert(!ShouldLog());
    std::cout<<"DIAMOND_PASSIVE_INGRESS_TEST=PASS\n";
}
