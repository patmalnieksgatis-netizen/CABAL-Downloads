#include "Client291MeritWire.h"
#include <array>
#include <cassert>
#include <cstdint>
#include <iostream>
using namespace diamond_v291::wire;
int main() {
  const std::array<std::uint8_t,7> legacy{
      0xe2,0xb7,7,0,0xf3,9,1};
  const std::array<std::uint8_t,7> rejected{
      0xe2,0xb7,7,0,0xf3,9,0};
  const std::array<std::uint8_t,11> shaped{
      0xe2,0xb7,11,0,0xf3,9,1,0x78,0x56,0x34,0x12};
  const ClientLookupCalls absent{};
  assert(ClassifyClientSuccessDwordPath(absent)==SuccessDwordPath::Unobserved);
  assert(CheckServerResponseForObservedClientRoute(
      legacy.data(),7,absent)==Status::ResponseRouteUnobserved);
  assert(CheckServerResponseForClient291(
      legacy.data(),7)==Status::ResponseRouteUnobserved); // strict legacy
  for(std::int32_t first=-3;first<=3;++first) {
    for(std::int32_t second=-3;second<=3;++second) {
      for(std::int32_t third=-3;third<=3;++third) {
        const ClientLookupCalls calls{true,first,true,second,true,third};
        const auto path=ClassifyClientSuccessDwordPath(calls);
        const auto expected=first==0 ? SuccessDwordPath::ReadAt6F8585 :
            (second==1 || third==2) ? SuccessDwordPath::ReadAt6F85B9 :
                                      SuccessDwordPath::NoDwordReadOnObservedPath;
        assert(path==expected);
        const auto result=CheckServerResponseForObservedClientRoute(
            legacy.data(),legacy.size(),calls);
        if(path==SuccessDwordPath::NoDwordReadOnObservedPath)
          assert(result==Status::ResponseLegacyNoDwordReadOnObservedPath);
        else
          assert(result==Status::ResponseTruncatedSuccess);
        // Runtime routing must not make S2C success contents authoritative.
        assert(CheckServerResponseForObservedClientRoute(
            shaped.data(),shaped.size(),calls)==
            Status::ResponseSuccessShapeUnknown);
        assert(CheckServerResponseForObservedClientRoute(
            rejected.data(),rejected.size(),calls)==Status::ResponseRejected);
      }
    }
  }
  // The handler invokes lookup again if first was nonzero. It may change.
  assert(ClassifyClientSuccessDwordPath(
      {true,8,false,0,false,0})==SuccessDwordPath::Unobserved);
  assert(ClassifyClientSuccessDwordPath(
      {true,8,true,8,false,0})==SuccessDwordPath::Unobserved);
  assert(ClassifyClientSuccessDwordPath(
      {true,8,true,1,false,0})==SuccessDwordPath::ReadAt6F85B9);
  assert(ClassifyClientSuccessDwordPath(
      {true,8,true,5,true,2})==SuccessDwordPath::ReadAt6F85B9);
  assert(ClassifyClientSuccessDwordPath(
      {true,8,true,2,true,1})==SuccessDwordPath::NoDwordReadOnObservedPath);
  auto malformed=legacy;
  malformed[4]=0;
  assert(CheckServerResponseForObservedClientRoute(
      malformed.data(),malformed.size(),
      {true,8,true,8,true,8})==Status::OpcodeMismatch);
  assert(CheckServerResponseForObservedClientRoute(
      nullptr,7,{true,8,true,8,true,8})==Status::Null);
  assert(CheckServerResponseForObservedClientRoute(
      legacy.data(),6,{true,8,true,8,true,8})==Status::Short);
  std::cout<<"CLIENT291_S2C_BRANCH_RVA_6F84FC=OFFLINE_CLASSIFIED\n"
           <<"LEGACY_7B_SUCCESS_CONDITIONALLY_READS_DWORD=PASS\n"
           <<"ALL_CLIENT_RETURN_VALUES_AND_MISSING_LOOKUPS=PASS\n"
           <<"S2C_DIAMOND_SUCCESS_SEMANTICS=UNKNOWN;NO_GAME_PATCH\n";
}
