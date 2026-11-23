#pragma once
// v291 0x0BDD is a strong grade-2 counterpart to original Platinum
// 0x0B13 MASTERY_SLOT_OPEN_CANCEL, NOT a verified Diamond rank-up.
// All behavior is read-only and no backend call/packet emission is allowed.
#include <cstddef>
#include <cstdint>
namespace diamond_v291::grade2 {
constexpr std::uint16_t kSlotCancelCandidate=0x0BDDu;
constexpr std::size_t kC2sBytes=14;
constexpr std::uint32_t kInvalidClientSelector=0xFFFFFFFFu;
enum class PacketKind : std::uint8_t { Other, Invalid, Grade2SlotCancelCandidate };
struct CandidatePacket {
    PacketKind kind=PacketKind::Invalid;
    std::uint32_t rawClientSelector=0;
};
CandidatePacket ParseC2s(const void*,std::size_t) noexcept;
enum class Route : std::uint8_t { Original, Invalid, Disabled };
struct Result {
    Route route=Route::Invalid;
    bool mayExecuteRankup=false;
    bool maySendS2cSuccess=false;
};
// Deprecated attempted rank-up bridge has been permanently replaced with a
// passive classifier, including if DIAMOND_ENABLE_GRADE2_CLONE_TRIAL is defined.
Result ClassifyOnly(const void*,std::size_t) noexcept;
} // namespace diamond_v291::grade2
