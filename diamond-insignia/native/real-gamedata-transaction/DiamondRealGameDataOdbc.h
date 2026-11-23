#pragma once
// REAL Server01 GameData ODBC procedure adapter for EP36_291_TEST clone.
// Does not patch WorldSvr, install SQL or send S2C.
// Disabled until native WorldSvr owner lock, ItemOption B0 decoder,
// 0BDA inventory-to-physical slot map, independent WarExp accounting,
// and clone SQL approval have all been independently verified.
#include "../grade2-ingress/Diamond0BDAGameplayAction.h"
#include "../inventory-reconcile/DiamondB0SelectedDebit30.h"
#include <cstddef>
#include <cstdint>
#include <string>
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
};
// MAY be plugged in as GameHost.commit only after a real server-owned
// Lease + verified clone state loader has populated this structure.
// A live SQL error after calling the stored procedure is IN-DOUBT;
// do not retry blindly or send client success. Returns COMMITTED_PENDING
// only after verifying the newly committed receipt on the same connection.
diamond_v291::gradeup0bda::AtomicCommitOutcome CommitRealGameDataServer01(
    void* trustedContext,const void* worldUserCtx,
    const diamond_v291::gradeup0bda::AtomicGradeUpRequest& request) noexcept;
} // namespace diamond_v291::real_gamedata
