#include "Client291MeritWire.h"
namespace diamond_v291::wire {
namespace {
std::uint16_t R16(const std::uint8_t* p) noexcept {
  return static_cast<std::uint16_t>(p[0])|
    (static_cast<std::uint16_t>(p[1])<<8);
}
std::uint32_t R32(const std::uint8_t* p) noexcept {
  return static_cast<std::uint32_t>(R16(p))|
    (static_cast<std::uint32_t>(R16(p+2))<<16);
}
void W16(std::uint8_t* p,std::uint16_t x) noexcept {
  p[0]=static_cast<std::uint8_t>(x);
  p[1]=static_cast<std::uint8_t>(x>>8);
}
void W32(std::uint8_t* p,std::uint32_t x) noexcept {
  W16(p,static_cast<std::uint16_t>(x));
  W16(p+2,static_cast<std::uint16_t>(x>>16));
}
}
std::array<std::uint8_t,kClientC2SBytes>
BuildOfflineClientRequest(std::uint32_t state118,std::uint32_t state11C) noexcept {
  std::array<std::uint8_t,kClientC2SBytes> p{};
  W16(p.data(),kMagic);W16(p.data()+2,kClientC2SBytes);
  W16(p.data()+8,kMeritOpcode);
  W32(p.data()+10,state118);W32(p.data()+14,state11C);
  return p;
}
Status ReadClientRequest(const void* packet,std::size_t size,RequestFields& out) noexcept {
  out={};
  if (!packet) return Status::Null;
  if (size<kClientC2SBytes) return Status::Short;
  if (size!=kClientC2SBytes) return Status::LengthMismatch;
  const auto* p=static_cast<const std::uint8_t*>(packet);
  if (R16(p)!=kMagic) return Status::MagicMismatch;
  if (R16(p+2)!=kClientC2SBytes) return Status::LengthMismatch;
  if (R16(p+8)!=kMeritOpcode) return Status::OpcodeMismatch;
  out.transportField=R32(p+4);
  out.state118=R32(p+10);
  out.state11C=R32(p+14);
  return Status::Ok;
}
Status CheckServerResponseForClient291(const void* packet,std::size_t size) noexcept {
  if (!packet) return Status::Null;
  if (size<kServerLegacyS2CBytes) return Status::Short;
  const auto* p=static_cast<const std::uint8_t*>(packet);
  if(R16(p)!=kMagic) return Status::MagicMismatch;
  if(R16(p+2)!=size) return Status::LengthMismatch;
  if(R16(p+4)!=kMeritOpcode) return Status::OpcodeMismatch;
  if(p[6]!=1) return Status::ResponseRejected;
  if(size<kClientSuccessMinBytes) return Status::ResponseTruncatedSuccess;
  // At least 11B exist; exact success payload meaning, fields, and effects
  // NOT known. Do NOT emit or interpret as a confirmed Diamond success.
  return Status::ResponseSuccessShapeUnknown;
}
SuccessDwordPath ClassifyClientSuccessDwordPath(
    const ClientLookupCalls& c) noexcept {
  // Verified exact original v291 handler RVA 0x6F84FC:
  // 0x6F857C: map lookup #1; 0 => read DWORD [packet+7] at 0x6F8585.
  // Nonzero => 0x6F859B lookup #2; 1 => read at 0x6F85B9.
  // Otherwise 0x6F85AA lookup #3; 2 => read at 0x6F85B9.
  // Other outcomes skip the TWO reads in this handler.
  // No assumption the repeated map lookups return the same value.
  if(!c.hasFirst) return SuccessDwordPath::Unobserved;
  if(c.first==0) return SuccessDwordPath::ReadAt6F8585;
  if(!c.hasSecond) return SuccessDwordPath::Unobserved;
  if(c.second==1) return SuccessDwordPath::ReadAt6F85B9;
  if(!c.hasThird) return SuccessDwordPath::Unobserved;
  if(c.third==2) return SuccessDwordPath::ReadAt6F85B9;
  return SuccessDwordPath::NoDwordReadOnObservedPath;
}
Status CheckServerResponseForObservedClientRoute(
    const void* packet,std::size_t size,
    const ClientLookupCalls& calls) noexcept {
  // Preserve the existing conservative/strict parser for header, size,
  // opcode, status, and 11B success. Only refine the 7B risk classification.
  const auto basic=CheckServerResponseForClient291(packet,size);
  if(basic!=Status::ResponseTruncatedSuccess)return basic;
  const auto branch=ClassifyClientSuccessDwordPath(calls);
  if(branch==SuccessDwordPath::Unobserved)
    return Status::ResponseRouteUnobserved;
  if(branch==SuccessDwordPath::NoDwordReadOnObservedPath)
    return Status::ResponseLegacyNoDwordReadOnObservedPath;
  return Status::ResponseTruncatedSuccess;
}
const char* Name(Status s) noexcept {
  switch(s){
    case Status::Ok:return "Ok";
    case Status::Null:return "Null";
    case Status::Short:return "Short";
    case Status::LengthMismatch:return "LengthMismatch";
    case Status::MagicMismatch:return "MagicMismatch";
    case Status::OpcodeMismatch:return "OpcodeMismatch";
    case Status::ResponseRejected:return "ResponseRejected";
    case Status::ResponseTruncatedSuccess:return "ResponseTruncatedSuccess";
    case Status::ResponseSuccessShapeUnknown:return "ResponseSuccessShapeUnknown";
    case Status::ResponseRouteUnobserved:return "ResponseRouteUnobserved";
    case Status::ResponseLegacyNoDwordReadOnObservedPath:return "ResponseLegacyNoDwordReadOnObservedPath";
  }
  return "Unknown";
}
}
