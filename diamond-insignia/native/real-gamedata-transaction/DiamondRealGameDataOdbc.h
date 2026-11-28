#pragma once
// REAL Server01 GameData ODBC procedure adapter for EP36_291_TEST clone.
// Does not patch WorldSvr, install SQL or send S2C.
// Disabled until native WorldSvr owner lock, ItemOption B0 decoder,
// 0BDA inventory-to-physical slot map, independent WarExp accounting,
// and clone SQL approval have all been independently verified.
#include "../grade2-ingress/Diamond0BDAGameplayAction.h"
#include "../inventory-reconcile/DiamondB0SelectedDebit30.h"
#include "DiamondRankUpCommitRecord.h"
#include <cstddef>
#include <cstdint>
#include <string>
#include <memory>
#include <vector>

namespace diamond_v291::real_gamedata {
struct RealServer01OdbcContext {
    std::uint32_t attestedUserNum=0;
    std::uint32_t attestedCharacterIdx=0;
    const void* attestedWorldUserCtx=nullptr;
    std::uint64_t attestedSessionGeneration=0;
    bool verifiedRestorableTestClone=false;
    bool driverConfiguredForExactServer01=false;
    bool ownerLockStillHeld=false;
    bool independentWarExpAccountingVerified=false;
    bool actualDbOwnerRankRowProvisioned=false;
    // Contains credentials; never serialize, print or place in command line.
    std::string odbcConnectionString{};
    // Bytes freshly read from trusted original Server01 GameData.
    std::vector<std::uint8_t> inventoryBefore{};
    std::int64_t warExpEarnBefore=0;
    std::int64_t warExpUsedBefore=0;
    std::vector<diamond_v291::inventory::B0WorldToPersistedSlot> selectedSlots{};
    diamond_v291::inventory::B0SelectionPersistenceProof proof{};
    // Populated only after an actual commit AND independent receipt/game-row
    // readback. Transfer ownership to native completion before Request dies.
    std::unique_ptr<RankUpCommitRecord> committedRankUp{};
    // Installed before SQLExecute, retained if commit outcome/readback is
    // uncertain. Its existence is NOT proof of commit; never apply as success.
    std::unique_ptr<RankUpCommitRecord> recoveryRankUp{};
};
// MAY be plugged in as GameHost.commit only after a real server-owned
// Lease + verified clone state loader has populated this structure.
// A live SQL error after calling the stored procedure is IN-DOUBT;
// do not retry blindly or send client success. Returns COMMITTED_PENDING
// only after verifying the newly committed receipt on the same connection.
diamond_v291::gradeup0bda::AtomicCommitOutcome CommitRealGameDataServer01(
    void* trustedContext,const void* worldUserCtx,
    const diamond_v291::gradeup0bda::AtomicGradeUpRequest& request) noexcept;
// Fresh connection and one SELECT after native save ACK. Checks the receipt,
// actual full inventory blob, rank/revision, and every WExp counter together.
// It never writes SQL. false includes an unavailable/ambiguous readback.
bool VerifySavedRankUpServer01(const std::string& connectionString,
                              const RankUpCommitRecord& committed) noexcept;
} // namespace diamond_v291::real_gamedata
