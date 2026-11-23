#include "Client291MeritWire.h"
#include <array>
#include <cassert>
#include <cstdint>
#include <iostream>
using namespace diamond_v291::wire;
int main(){
  auto p=BuildOfflineClientRequest(0x11223344,0xaabbccdd);
  const std::array<std::uint8_t,18> expected{0xe2,0xb7,0x12,0,0,0,0,0,
    0xf3,9,0x44,0x33,0x22,0x11,0xdd,0xcc,0xbb,0xaa};
  assert(p==expected);
  RequestFields req{99,99,99};
  assert(ReadClientRequest(p.data(),p.size(),req)==Status::Ok);
  assert(req.transportField==0&&req.state118==0x11223344&&req.state11C==0xaabbccdd);
  for(std::size_t n=0;n<p.size();++n){
    assert(ReadClientRequest(p.data(),n,req)==Status::Short);
    assert(req.state118==0&&req.state11C==0);
  }
  assert(ReadClientRequest(p.data(),p.size()+1,req)==Status::LengthMismatch);
  auto wrong=p;wrong[8]=0;
  assert(ReadClientRequest(wrong.data(),wrong.size(),req)==Status::OpcodeMismatch);
  wrong=p;wrong[2]=0x13;
  assert(ReadClientRequest(wrong.data(),wrong.size(),req)==Status::LengthMismatch);
  wrong=p;wrong[0]=0;
  assert(ReadClientRequest(wrong.data(),wrong.size(),req)==Status::MagicMismatch);
  assert(ReadClientRequest(nullptr,18,req)==Status::Null);
  std::array<std::uint8_t,7> oldSuccess{0xe2,0xb7,7,0,0xf3,9,1};
  std::array<std::uint8_t,7> oldFailure{0xe2,0xb7,7,0,0xf3,9,0};
  assert(CheckServerResponseForClient291(oldSuccess.data(),7)==Status::ResponseRouteUnobserved);
  assert(CheckServerResponseForClient291(oldFailure.data(),7)==Status::ResponseRejected);
  std::array<std::uint8_t,11> candidate{0xe2,0xb7,11,0,0xf3,9,1,0,0,0,0};
  assert(CheckServerResponseForClient291(candidate.data(),candidate.size())==Status::ResponseSuccessShapeUnknown);
  assert(CheckServerResponseForClient291(nullptr,11)==Status::Null);
  assert(CheckServerResponseForClient291(candidate.data(),6)==Status::Short);
  candidate[2]=0;
  assert(CheckServerResponseForClient291(candidate.data(),11)==Status::LengthMismatch);
  std::cout<<"CLIENT291_C2S_09F3_18B=PASS\n";
  std::cout<<"WORLD_7B_SUCCESS_VS_CLIENT_CONDITIONAL_DWORD_PLUS7=RISK_CONFIRMED\n";
  std::cout<<"CLIENT291_S2C_SUCCESS_SEMANTICS=UNKNOWN;NO_LIVE_PATCH\n";
}
