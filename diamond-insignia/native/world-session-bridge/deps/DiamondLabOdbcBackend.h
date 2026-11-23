#pragma once
#include "DiamondCommitGate.h"
#include <sql.h>
#include <sqlext.h>
#include <cstdint>
#include <string>
#include <vector>
namespace diamond_v291 {
// !! SYNTHETIC CLONE ONLY !!
// WorldSvr must attest the session independently; NEVER extract UserNum,
// CharacterIdx or session nonce from an untrusted client C2S payload.
struct VerifiedSession {
    std::uint32_t userNum = 0;
    std::uint32_t characterIdx = 0;
    std::int64_t shadowNonce = 0;
};
using AttestSession = bool (*)(const void* trustedWorldSession,
                               VerifiedSession& result, void* context) noexcept;
class DiamondLabOdbcBackend final : public Backend {
public:
    DiamondLabOdbcBackend(std::string odbcConnectionString,
                          AttestSession attest, void* attestorContext) noexcept;
    ~DiamondLabOdbcBackend() override;
    DiamondLabOdbcBackend(const DiamondLabOdbcBackend&)=delete;
    DiamondLabOdbcBackend& operator=(const DiamondLabOdbcBackend&)=delete;
    bool begin(const void* trustedWorldSession, Identity& owner) override;
    Lookup receipt(std::uint32_t expectedRevision,const Request& request,
                   Receipt& committed) override;
    bool trustedState(cabal_diamond_state& state) override;
    bool commitAll(const Identity& owner, const Request& request,
                   const cabal_diamond_evaluation& proposed) override;
    void release(bool committed) noexcept override;
private:
    struct Wallet {
        int badgeGrade=0;
        int platinumBadge=0;
        int platinumMaxed=0;
        std::int64_t wexp=0;
        int tickets=0;
        int freePoints=0;
        int categories=0;
        int revision=0;
    };
    bool connectAndBegin();
    bool verifyDatabase();
    bool lockWallet();
    bool loadMasteryAndSlots();
    bool updateWallet(const cabal_diamond_evaluation& e);
    bool updateMastery(const Request& r,const cabal_diamond_evaluation& e);
    bool insertReceipt(const Request& r,const cabal_diamond_evaluation& e);
    void closeHandles() noexcept;
    std::string connection_;
    AttestSession attest_=nullptr;
    void* attestContext_=nullptr;
    SQLHENV env_=SQL_NULL_HENV;
    SQLHDBC dbc_=SQL_NULL_HDBC;
    bool transaction_=false;
    bool ready_=false;
    bool stateLoaded_=false;
    bool committed_=false;
    VerifiedSession session_{};
    Wallet wallet_{};
    std::vector<std::uint32_t> slots_;
    std::vector<cabal_diamond_level_entry> levels_;
};
} // namespace diamond_v291