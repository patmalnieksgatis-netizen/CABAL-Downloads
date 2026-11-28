#pragma once
#include "DiamondNativeRankUpV20.h"
#include <map>
#include <mutex>

namespace diamond_v291::completion {

// Implementations own an actual native lifetime/save lease. Acquisition must
// try rather than wait for a pending operation on the same account. Destruction
// must not release uncertain saves. The adapter has process lifetime.
class NativeSession : public NativePort {
public:
    // Stable for the lifetime of this lease.
    virtual Identity Owner() const noexcept=0;
    // Load trusted state only. This method must not perform a commit.
    virtual bool Populate(real_gamedata::RealServer01OdbcContext&,
                          real_gamedata::Real0BDAHost&) noexcept=0;
    virtual void CancelBeforeCommit() noexcept=0;
};
using AcquireSession = std::unique_ptr<NativeSession> (*)(
    void*,void*,const diamond_v19::ContextPrefix&) noexcept;

// Begin/finish and event ownership for the registered handler. Native events
// must run on the same account executor as Handle. The registry mutex permits
// different account executors to access different entries concurrently. It is
// never held during native calls or SQL and does not replace native exclusion.
class WorldSvrRankUpAdapter final {
    struct Pending {
        std::unique_ptr<NativeSession> session;
        std::unique_ptr<RankUpCompletion> completion;
        Identity owner{};
        const void* nativeUser=nullptr;
        RankUpCompletion* activeCompletion=nullptr;
        bool interrupted=false;
    };
public:
    WorldSvrRankUpAdapter(AcquireSession acquire,void* context,
                         diamond_v20::Binding verifiedHost={}) noexcept
        :acquire_(acquire),context_(context),binding_(verifiedHost) {
        binding_.context=this;
        binding_.begin=Begin;
        binding_.finish=Finish;
    }
    WorldSvrRankUpAdapter(const WorldSvrRankUpAdapter&)=delete;
    WorldSvrRankUpAdapter& operator=(const WorldSvrRankUpAdapter&)=delete;
    const diamond_v20::Binding& Binding() const noexcept {return binding_;}

    Result SaveRouted(const Identity& owner,std::uint32_t flags,
                     std::uint64_t epoch,std::uint32_t outstanding) noexcept {
        auto entry=Find(owner.userNum);
        if(!entry)return Result::IgnoredEvent;
        if(!entry->completion) {
            InterruptEntry(*entry);
            return Result::RecoveryRequired;
        }
        return entry->completion->OnSaveRouted(owner,flags,epoch,outstanding);
    }
    Result NativeSaveRouted(const Identity& owner,const void* packet,
                           std::size_t bytes,std::uint64_t epoch,
                           std::uint32_t outstanding) noexcept {
        auto entry=Find(owner.userNum);
        if(!entry)return Result::IgnoredEvent;
        if(!entry->completion) {
            InterruptEntry(*entry);
            return Result::RecoveryRequired;
        }
        return entry->completion->OnNativeSaveRouted(owner,packet,bytes,epoch,outstanding);
    }
    Result ItcSaveAck(const Identity& owner,const void* packet,std::size_t bytes,
                      std::uint64_t epoch,std::uint32_t outstanding) noexcept {
        auto entry=Find(owner.userNum);
        if(!entry)return Result::IgnoredEvent;
        if(!entry->completion) {
            InterruptEntry(*entry);
            return Result::RecoveryRequired;
        }
        const auto result=entry->completion->OnItcSaveAck(
            owner,packet,bytes,epoch,outstanding);
        if(result==Result::Completed)Remove(owner.userNum,entry);
        return result;
    }
    // Invoked for either disconnection or timeout of this operation. A new
    // session cannot release or take over the retained record and native lease.
    void Interrupt(const Identity& owner) noexcept {
        auto entry=Find(owner.userNum);
        if(!entry)return;
        const auto held=entry->owner;
        if(held.characterIdx!=owner.characterIdx ||
           held.sessionGeneration!=owner.sessionGeneration)return;
        InterruptEntry(*entry);
    }
    // Called on the account executor BEFORE native uninitialization changes
    // USERCONTEXT+E8 or resets USERDATACONTEXT. Compare only the stored address.
    // No lookup or dereference of a character that may already be recycling.
    void BeforeNativeUninitialize(const void* user) noexcept {
        if(!user)return;
        std::lock_guard<std::mutex> lock(registryMutex_);
        for(auto& pair:pending_)
            if(pair.second->nativeUser==user)InterruptEntry(*pair.second);
    }
    std::size_t PendingCount() const {
        std::lock_guard<std::mutex> lock(registryMutex_);
        return pending_.size();
    }
private:
    static void InterruptEntry(Pending& entry) noexcept {
        entry.interrupted=true;
        if(entry.activeCompletion)entry.activeCompletion->MarkInDoubt();
    }
    static bool Begin(void* context,void* layer,
                      const diamond_v19::ContextPrefix& native,
                      diamond_v20::Request& request) noexcept {
        return static_cast<WorldSvrRankUpAdapter*>(context)->BeginRequest(layer,native,request);
    }
    bool BeginRequest(void* layer,const diamond_v19::ContextPrefix& native,
                      diamond_v20::Request& request) noexcept {
        if(!acquire_ || !diamond_v20::Ready(binding_))return false;
        auto session=acquire_(context_,layer,native);
        if(!session)return false;
        const auto owner=session->Owner();
        if(!owner.userNum || !owner.characterIdx || !owner.sessionGeneration ||
           !owner.intent || !session->HeldSessionMatches(owner)) {
            session->CancelBeforeCommit();return false;
        }
        std::shared_ptr<Pending> entry;
        try {
            entry=std::make_shared<Pending>();
            entry->session=std::move(session);
            request.completion=std::make_unique<RankUpCompletion>(*entry->session,owner);
            entry->owner=owner;
            entry->nativeUser=native.user;
            entry->activeCompletion=request.completion.get();
            bool inserted=false;
            {
                std::lock_guard<std::mutex> lock(registryMutex_);
                inserted=pending_.emplace(owner.userNum,entry).second;
            }
            if(!inserted) {
                request.completion.reset();
                entry->session->CancelBeforeCommit();return false;
            }
        } catch(...) {
            request.completion.reset();
            if(entry && entry->session)entry->session->CancelBeforeCommit();
            else if(session)session->CancelBeforeCommit();
            return false;
        }
        // Registration and completion allocation precede all SQL. Retaining
        // an uncertain result in Finish requires no further allocation.
        if(!entry->session->Populate(request.transaction,request.bridge) ||
           entry->interrupted || !request.completion ||
           !request.completion->ReadyForCommit()) {
            request.completion.reset();
            entry->session->CancelBeforeCommit();
            Remove(owner.userNum,entry);return false;
        }
        request.bridge.transaction=&request.transaction;
        request.fenceToken=entry.get();
        return true;
    }
    static void Finish(void* context,diamond_v20::Request& request,
                       const gradeup0bda::GameActionResult& result) noexcept {
        auto& host=*static_cast<WorldSvrRankUpAdapter*>(context);
        if(!request.completion)return;
        const auto owner=request.completion->Owner();
        auto entry=host.Find(owner.userNum);
        if(!entry || entry.get()!=request.fenceToken)return;
        entry->completion=std::move(request.completion);
        if(entry->interrupted ||
           result.state==gradeup0bda::GameActionState::InDoubtRecoveryRequired) {
            entry->completion->MarkInDoubt();
            return;
        }
        if(result.state==gradeup0bda::GameActionState::CommittedPendingSaveProof)
            return;
        // Only a rejection before any commit can cancel the native lease.
        if(entry->completion->GetState()!=State::Prepared ||
           entry->completion->HasRetainedEvidence())return;
        entry->session->CancelBeforeCommit();
        host.Remove(owner.userNum,entry);
    }
    std::shared_ptr<Pending> Find(std::uint32_t user) const {
        std::lock_guard<std::mutex> lock(registryMutex_);
        auto it=pending_.find(user);
        return it==pending_.end()?nullptr:it->second;
    }
    void Remove(std::uint32_t user,const std::shared_ptr<Pending>& expected) {
        std::lock_guard<std::mutex> lock(registryMutex_);
        auto it=pending_.find(user);
        if(it!=pending_.end() && it->second==expected)pending_.erase(it);
    }
    AcquireSession acquire_=nullptr;
    void* context_=nullptr;
    diamond_v20::Binding binding_{};
    mutable std::mutex registryMutex_;
    std::map<std::uint32_t,std::shared_ptr<Pending>> pending_;
};
} // namespace diamond_v291::completion
