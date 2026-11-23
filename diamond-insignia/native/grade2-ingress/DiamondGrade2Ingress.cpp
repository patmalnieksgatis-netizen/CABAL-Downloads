#include "DiamondGrade2Ingress.h"
namespace diamond_v291::grade2 {
namespace {
std::uint16_t U16(const std::uint8_t* p) noexcept {
    return static_cast<std::uint16_t>(p[0]) |
           static_cast<std::uint16_t>(p[1])<<8;
}
std::uint32_t U32(const std::uint8_t* p) noexcept {
    return static_cast<std::uint32_t>(U16(p)) |
           static_cast<std::uint32_t>(U16(p+2))<<16;
}
} // namespace
CandidatePacket ParseC2s(const void* data,std::size_t size) noexcept {
    CandidatePacket out{};
    if(!data || size<10)return out;
    const auto* p=static_cast<const std::uint8_t*>(data);
    if(U16(p)!=0xB7E2u || U16(p+8)!=kSlotCancelCandidate) {
        out.kind=PacketKind::Other; // preserve Platinum 0x0B13 and others
        return out;
    }
    if(size!=kC2sBytes || U16(p+2)!=size)return out;
    const auto value=U32(p+10);
    if(value==kInvalidClientSelector)return out;
    out.kind=PacketKind::Grade2SlotCancelCandidate;
    out.rawClientSelector=value; // opaque; client data is never trusted
    return out;
}
Result ClassifyOnly(const void* data,std::size_t size) noexcept {
    const auto packet=ParseC2s(data,size);
    if(packet.kind==PacketKind::Other)return {Route::Original,false,false};
    if(packet.kind==PacketKind::Invalid)return {Route::Invalid,false,false};
    // There is NO transaction path for this probable slot-open cancel.
    // Macro switches cannot accidentally activate rank-up or S2C success.
    return {Route::Disabled,false,false};
}
} // namespace diamond_v291::grade2
