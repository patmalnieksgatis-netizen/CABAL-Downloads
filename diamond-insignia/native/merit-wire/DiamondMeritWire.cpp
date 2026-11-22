#include "DiamondMeritWire.h"
#include <cstring>
namespace cabal::merit_wire {
namespace {
std::uint16_t Read16(const std::uint8_t* p) noexcept {
    return std::uint16_t(p[0]) | (std::uint16_t(p[1]) << 8);
}
std::uint32_t Read32(const std::uint8_t* p) noexcept {
    return std::uint32_t(Read16(p)) | (std::uint32_t(Read16(p+2)) << 16);
}
}
ParseStatus ParseLegacyRequest(const void* bytes, std::size_t length,
                               LegacyRequest& out) noexcept {
    out = {};
    if (!bytes) return ParseStatus::Null;
    // Exact-size requirement before ANY read: 10-byte C2S header + 8 bytes.
    if (length != kLegacyRequestBytes) return ParseStatus::WrongLength;
    const auto* p = static_cast<const std::uint8_t*>(bytes);
    if (Read16(p) != kMagic) return ParseStatus::WrongMagic;
    if (Read16(p+2) != kLegacyRequestBytes) return ParseStatus::HeaderLengthMismatch;
    if (Read16(p+8) != kLegacyMeritCommand) return ParseStatus::WrongCommand;
    LegacyRequest result{};
    result.checksum = Read32(p+4);
    result.value0 = Read32(p+10);
    result.value1 = Read32(p+14);
    out = result;
    return ParseStatus::Ok;
}
std::array<std::uint8_t,kLegacyResultBytes>
EncodeLegacyResult(bool committed) noexcept {
    // The same 7-byte shape appears at 0xA3B544/0xA3B5CA in WorldSvr.
    return {0xE2,0xB7,0x07,0x00,0xF3,0x09,static_cast<std::uint8_t>(committed ? 1 : 0)};
}
const char* ParseStatusName(ParseStatus s) noexcept {
    switch(s) {
        case ParseStatus::Ok:return "Ok";
        case ParseStatus::Null:return "Null";
        case ParseStatus::WrongLength:return "WrongLength";
        case ParseStatus::WrongMagic:return "WrongMagic";
        case ParseStatus::WrongCommand:return "WrongCommand";
        case ParseStatus::HeaderLengthMismatch:return "HeaderLengthMismatch";
    }
    return "Unknown";
}
} // namespace cabal::merit_wire
