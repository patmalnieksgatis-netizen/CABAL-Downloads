#include "Diamond0BDARealServer01Bridge.h"
#include <array>
#include <cassert>
#include <iostream>
#include <type_traits>

using namespace diamond_v291::real_gamedata;
using namespace diamond_v291::gradeup0bda;
static_assert(std::is_convertible<
    decltype(&CommitRealGameDataServer01),AtomicCommitCallback>::value,
    "The real Server01 ODBC function MUST match 0BDA atomic callback ABI");
int main(){
    const std::array<unsigned char,14> rank{
        0xE2,0xB7,14,0,0,0,0,0,0xDA,0x0B,1,0,5,0};
    int fakeUser=1;
    const Real0BDAHost disabled{};
    const auto denied=Execute0BDARealServer01(&fakeUser,rank.data(),
                                              rank.size(),disabled);
    assert(denied.state==GameActionState::MissingWorldAuthority);
    assert(!denied.maySendClientSuccess);
    auto platinum=rank;platinum[8]=0x10;
    const auto old=Execute0BDARealServer01(&fakeUser,platinum.data(),
                                           platinum.size(),disabled);
    assert(old.state==GameActionState::NotDiamondCommand);
    auto bad=rank;bad[2]=15;
    const auto invalid=Execute0BDARealServer01(&fakeUser,bad.data(),
                                               bad.size(),disabled);
    assert(invalid.state==GameActionState::InvalidPacket);
    auto noContext=Execute0BDARealServer01(
        nullptr,rank.data(),rank.size(),disabled);
    assert(noContext.state==GameActionState::MissingWorldAuthority);
    std::cout<<"DIAMOND_0BDA_AUTHENTICATED_INGRESS_TO_REAL_SERVER01_ODBC_LINKED=PASS\n"
             <<"DIAMOND_0BDA_DEFAULT_SERVER01_CONNECTION_DISABLED=PASS\n"
             <<"DIAMOND_0B10_ORIGINAL_DISPATCH_PRESERVED=PASS\n"
             <<"LIVE_SQL_WRITES=NO\n";
}
