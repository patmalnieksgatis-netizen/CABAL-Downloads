#pragma once
// SQL -> leased native mutation -> cmd46/47 -> fresh SQL -> single reply.
// The native host must retain this object and its real fence after Handle
// returns. No USERCONTEXT pointer is retained in the committed record.
#include "../native/real-gamedata-transaction/DiamondRealGameDataOdbc.h"
#include "../native/grade2-ingress/Diamond0BDASaveReplyGate.h"
#include <memory>
#include <string>

namespace diamond_v291::completion {
struct Identity {
    std::uint32_t userNum=0,characterIdx=0;
    std::uint64_t sessionGeneration=0,intent=0;
};
struct SaveReservation {
    std::uint32_t flags=0,outstandingBefore=0;
    std::uint64_t epoch=0;
};
// This is the remaining exact-native boundary, not a synthetic lock. The
// real host owns the fence, port and owner executor until explicit Release.
// All completion calls must be serialized on that owner executor. Native
// hooks queue ACKs to it by Identity, including competing saves for the
// same session. Never retain an unleased raw user pointer or discard a
// competing ACK just because its flags or request ID differ.
class NativePort {
public:
    virtual ~NativePort()=default;
    virtual bool HeldSessionMatches(const Identity&) noexcept=0;
    // Compare the complete before state under the native fence, then apply
    // the selected debit and all WExp counters through verified native APIs.
    // False includes partial/uncertain application and MUST retain the fence.
    virtual bool ApplyCommitted(const real_gamedata::RankUpCommitRecord&) noexcept=0;
    // Reserve/observe the native save BEFORE publication, excluding every
    // competing save. Publish queues its ACK; no reentrant completion call.
    virtual bool ReserveSave(SaveReservation&) noexcept=0;
    virtual bool PublishSave(const SaveReservation&) noexcept=0;
    virtual bool ReplyAbiVerified() const noexcept=0;
    virtual bool SendRankUpSuccess(const Identity&,
        const std::array<std::uint8_t,7>&) noexcept=0;
    virtual void ReleaseAfterReconciliation(const Identity&) noexcept=0;
};
enum class State : std::uint8_t {
    Prepared, WaitingForAck, RecoveryRequired, ReconciledReplyBlocked, Completed
};
enum class Result : std::uint8_t {
    WaitingForAck, WrongPhase, IgnoredAck, RecoveryRequired,
    ReplyBlocked, Completed
};
class RankUpCompletion final {
public:
    RankUpCompletion(NativePort& port,Identity identity) noexcept
        :port_(port),identity_(identity){}
    RankUpCompletion(const RankUpCompletion&)=delete;
    RankUpCompletion& operator=(const RankUpCompletion&)=delete;
    static constexpr bool CloneEnabled() noexcept {
#ifdef DIAMOND_ENABLE_0BDA_CLONE_TRIAL
        return true;
#else
        return false;
#endif
    }
    bool ReadyForCommit() noexcept;
    Result AcceptCommitted(std::unique_ptr<real_gamedata::RankUpCommitRecord>,
                           std::string connectionString) noexcept;
    Result OnSaveAck(const Identity&,const void* packet,std::size_t bytes,
                     std::uint64_t receiveEpoch,
                     std::uint32_t outstandingAtAck) noexcept;
    void MarkInDoubt() noexcept;
    void MarkInDoubt(std::unique_ptr<real_gamedata::RankUpCommitRecord>,
                     std::string connectionString) noexcept;
    bool HasRetainedEvidence() const noexcept {return committed_!=nullptr;}
    State GetState() const noexcept {return state_;}
    const Identity& Owner() const noexcept {return identity_;}
    // Destruction does not unlock the host fence. Pending/recovery ownership
    // MUST be retained by the host, including on timeout and disconnect.
private:
    Result Recover() noexcept;
    NativePort& port_;
    Identity identity_{};
    State state_=State::Prepared;
    DiamondWorldSaveBarrier barrier_{};
    std::unique_ptr<real_gamedata::RankUpCommitRecord> committed_{};
    std::string connectionString_{}; // private process memory; never logged
    bool replyAttempted_=false;
};
} // namespace diamond_v291::completion
