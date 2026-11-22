#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

// Source-pinned to CABAL v291 x64 SHA256 52e7956d... and existing
// WorldSvr SHA256 caec7772... . OFFLINE/READ-ONLY: NOT A GAME PATCH.
namespace diamond_v291::wire {
constexpr std::uint16_t kMagic=0xB7E2;
constexpr std::uint16_t kMeritOpcode=0x09F3;
constexpr std::size_t kClientC2SBytes=18;
constexpr std::size_t kServerLegacyS2CBytes=7;
constexpr std::size_t kClientSuccessMinBytes=11; // conditional DWORD at response+7

struct RequestFields {
  std::uint32_t transportField=0;
  std::uint32_t state118=0; // field from +0x118 in client singleton
  std::uint32_t state11C=0; // field from +0x11C in client singleton
};

enum class Status : std::uint8_t {
  Ok, Null, Short, LengthMismatch, MagicMismatch, OpcodeMismatch,
  ResponseRejected, ResponseTruncatedSuccess, ResponseSuccessShapeUnknown
};

// Exact client builder observed at RVA 0x6FF14C: checksum/transport slot
// [4..7] zeroed, two 32-bit singleton fields at +10 and +14.
std::array<std::uint8_t,kClientC2SBytes>
BuildOfflineClientRequest(std::uint32_t state118, std::uint32_t state11C) noexcept;

Status ReadClientRequest(const void* packet, std::size_t size,
                         RequestFields& out) noexcept;

// Risk-only compatibility checker, NEVER a producer of success replies.
// Client callback registered for 0x09F3 at RVA 0x6F84FC reads byte +6
// and, in conditional success paths, DWORD +7. 7B success from old
// WorldSvr cannot contain that DWORD. Unknown semantics prevent encoding it.
Status CheckServerResponseForClient291(const void* packet,
                                       std::size_t size) noexcept;
const char* Name(Status v) noexcept;
}
