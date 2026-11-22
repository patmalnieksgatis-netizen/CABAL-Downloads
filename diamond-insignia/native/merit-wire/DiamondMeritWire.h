#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

// Evidence-pinned legacy CABAL Merit C2S/S2C 0x09F3 packet layer.
// This is NOT proof that the v291 Diamond rank-up uses this command.
namespace cabal::merit_wire {
inline constexpr std::uint16_t kMagic = 0xB7E2;
inline constexpr std::uint16_t kLegacyMeritCommand = 0x09F3;
inline constexpr std::size_t kLegacyRequestBytes = 18;
inline constexpr std::size_t kLegacyResultBytes = 7;

struct LegacyRequest {
    std::uint32_t checksum = 0; // transport-owned; NOT authenticated by this parser
    std::uint32_t value0 = 0; // +0x0A; semantic role NOT yet confirmed
    std::uint32_t value1 = 0; // +0x0E; semantic role NOT yet confirmed
};

enum class ParseStatus : std::uint8_t {
    Ok, Null, WrongLength, WrongMagic, WrongCommand, HeaderLengthMismatch
};

// Caller must validate/authorize an actual WorldSvr session before using data.
// Packet buffer must point to the complete transport-validated C2S frame.
ParseStatus ParseLegacyRequest(const void* bytes, std::size_t length,
                               LegacyRequest& out) noexcept;

// Existing 7-byte S2C Merit result shape observed in the specific archived
// WorldSvr binary branch. Success flag MUST be based on durable game commit.
std::array<std::uint8_t, kLegacyResultBytes>
EncodeLegacyResult(bool committed) noexcept;

// Never conflate this legacy status-only result with an unverified v291
// Diamond-specific update packet. The latter is still unknown.
const char* ParseStatusName(ParseStatus s) noexcept;
} // namespace cabal::merit_wire
