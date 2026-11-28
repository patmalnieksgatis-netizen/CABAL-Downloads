#pragma once
// CABAL v291 Diamond Insignia. Offline-only WorldSvr/DBAgent persistence barrier.
// NO WorldSvr hooks, game-data DB writes, or S2C packet in this module.
// Attested state MUST originate from trusted live WorldSvr and persisted DB.
#include <cstddef>
#include <cstdint>
#include "../real-gamedata-transaction/DiamondWarExpAccounting.h"

namespace diamond_v291 {
constexpr std::uint16_t kIpcUpdateChDat = 46;
constexpr std::uint16_t kIpcResultUpdateChDat = 47;
constexpr std::uint16_t kIpcMagic = 0xB7E2;
constexpr std::size_t kIpcResultSize = 18;
constexpr std::uint32_t kSaveInventory = 0x02;

struct Operation {
    std::uint64_t durableIntent = 0;
    std::uint32_t userNum = 0;
    std::uint32_t characterIdx = 0;
    std::uint32_t expectedRevision = 0;
    std::uint32_t appliedRevision = 0;
    std::uint32_t command = 0;
    std::int32_t masteryId = 0;
    std::int32_t newMasteryLevel = 0;
    std::uint32_t newBadgeGrade = 0;
    // All three native/saved counters are required. Missing host reads fail
    // validation rather than silently treating earned/used as zero.
    real_gamedata::WarExpLedger beforeWexp{-1,-1,-1};
    real_gamedata::WarExpLedger afterWexp{-1,-1,-1};
    std::uint32_t newTickets = 0; // item 33554961 actual inventory count
};

struct DurableSnapshot {
    bool verifiedGameInventory = false;
    bool verifiedGameWexp = false;
    bool receiptCommitted = false;
    std::uint64_t durableIntent = 0;
    std::uint32_t userNum = 0;
    std::uint32_t characterIdx = 0;
    std::uint32_t revision = 0;
    std::uint32_t badgeGrade = 0;
    real_gamedata::WarExpLedger wexp{-1,-1,-1};
    std::uint32_t tickets = 0;
    std::int32_t masteryId = 0;
    std::int32_t masteryLevel = 0;
};

enum class Phase : std::uint8_t {
    Empty, IntentDurable, NativeMutationApplied, SaveSent,
    AckObserved, Reconciled, RecoveryRequired
};
enum class Verdict : std::uint8_t {
    Ok, Invalid, IllegalPhase, ForeignAck, StaleAck,
    AmbiguousSave, DuplicateAck, NeedRecovery, SnapshotMismatch
};

class DiamondWorldSaveBarrier final {
public:
    // Requires external authentication and evidence of a DURABLY saved intent.
    Verdict Begin(const Operation& op, bool sessionAttested,
                  bool durableIntentVerified) noexcept;
    Verdict MarkNativeMutationApplied(bool appliedUnderOwnerLock) noexcept;
    Verdict MarkSaveSent(std::uint32_t packFlags, std::uint64_t sendEpoch,
                         std::uint32_t outstandingBeforeSend) noexcept;
    Verdict ObserveIpcResult47(const void* packet, std::size_t size,
                               std::uint64_t receiveEpoch,
                               std::uint32_t outstandingAtAck) noexcept;
    // Requires fresh independent persisted game state, not merely a cmd47 ACK.
    Verdict Reconcile(const DurableSnapshot& snapshot) noexcept;
    Verdict MarkTimeout() noexcept;
    bool MaySendSuccess() const noexcept;
    Phase GetPhase() const noexcept {return phase_;}
    std::uint64_t Intent() const noexcept {return operation_.durableIntent;}
private:
    // Single-threaded per instance: host must lock character across operation.
    // NO Reset: failed/ambiguous transaction requires durable recovery, not
    // discarding its state from RAM.
    Operation operation_{};
    Phase phase_ = Phase::Empty;
    std::uint32_t packFlags_ = 0;
    std::uint64_t sendEpoch_ = 0;
};
const char* WorldSavePhaseName(Phase p) noexcept;
const char* WorldSaveVerdictName(Verdict v) noexcept;
} // namespace diamond_v291
