#include "DiamondCommitGate.h"
#include <limits>

namespace diamond_v291 {
namespace {
class ReleaseGuard {
    Backend& backend_;
    bool committed_ = false;
public:
    explicit ReleaseGuard(Backend& backend) : backend_(backend) {}
    ~ReleaseGuard(){ backend_.release(committed_); }
    void markCommitted() noexcept {committed_=true;}
    ReleaseGuard(const ReleaseGuard&)=delete;
    ReleaseGuard& operator=(const ReleaseGuard&)=delete;
};
bool Valid(const Request& request) {
    if(request.expectedRevision==std::numeric_limits<std::uint32_t>::max()) return false;
    if(request.command==CABAL_DIAMOND_RANK_UP) return request.masteryId==0;
    if(request.command==CABAL_DIAMOND_MASTERY_LEVEL_UP)
        return request.masteryId>=159 && request.masteryId<=474;
    return false;
}
}
Result Execute(const cabal_diamond_engine* engine, Backend& backend,
               const void* authenticatedWorldSession, const Request& request) {
    Result output{};
    if(!engine || !authenticatedWorldSession || !Valid(request)) return output;
    Identity owner{};
    if(!backend.begin(authenticatedWorldSession, owner)) {
        output.status=Status::AuthFailure;
        return output;
    }
    ReleaseGuard guard(backend);
    if(owner.userNum==0 || owner.characterIdx==0) {
        output.status=Status::AuthFailure;
        return output;
    }
    Receipt found{};
    switch(backend.receipt(request.expectedRevision, request, found)) {
        case Lookup::SameCommitted:
            // The receipt itself is authoritative, not recomputed from
            // a now-changed wallet. A replay NEVER charges resources again.
            if(found.request.expectedRevision!=request.expectedRevision ||
               found.request.command!=request.command ||
               found.request.masteryId!=request.masteryId ||
               found.applied.abi_version!=CABAL_DIAMOND_ABI_VERSION ||
               !found.applied.permitted || !found.applied.requires_atomic_commit ||
               found.applied.new_revision!=request.expectedRevision+1) {
                output.status=Status::BackendFailure;
                return output;
            }
            output.status=Status::Replayed;
            output.evaluation=found.applied;
            return output;
        case Lookup::ConflictingCommitted:
            output.status=Status::RevisionConflict;
            return output;
        case Lookup::Failure:
            output.status=Status::BackendFailure;
            return output;
        case Lookup::Fresh: break;
    }
    cabal_diamond_state trusted{};
    if(!backend.trustedState(trusted) ||
       trusted.abi_version!=CABAL_DIAMOND_ABI_VERSION ||
       trusted.server_authoritative!=1) {
        output.status=Status::BackendFailure;
        return output;
    }
    if(trusted.revision!=request.expectedRevision) {
        output.status=Status::RevisionConflict;
        return output;
    }
    cabal_diamond_request cmd{};
    cmd.abi_version=CABAL_DIAMOND_ABI_VERSION;
    cmd.command=request.command;
    cmd.expected_revision=request.expectedRevision;
    cmd.mastery_id=request.masteryId;
    cabal_diamond_evaluation proposed{};
    if(cabal_diamond_evaluate(engine,&trusted,&cmd,&proposed)!=0 ||
       proposed.abi_version!=CABAL_DIAMOND_ABI_VERSION) {
        output.status=Status::EngineFailure;
        return output;
    }
    output.ruleError=proposed.rule_error;
    if(!proposed.permitted) {
        output.status=Status::RuleRejected;
        return output;
    }
    // Only an actually committed revision increment can be acknowledged.
    if(proposed.requires_atomic_commit!=1 ||
       proposed.new_revision!=request.expectedRevision+1 ||
       proposed.new_wexp>trusted.wexp ||
       proposed.new_ticket_count>trusted.verified_exchange_ticket_count) {
        output.status=Status::EngineFailure;
        return output;
    }
    if(!backend.commitAll(owner,request,proposed)) {
        output.status=Status::BackendFailure;
        return output;
    }
    guard.markCommitted();
    output.status=Status::Applied;
    output.evaluation=proposed;
    return output;
}
const char* StatusName(Status s) noexcept {
    switch(s){
      case Status::Applied:return "Applied";
      case Status::Replayed:return "Replayed";
      case Status::RuleRejected:return "RuleRejected";
      case Status::RevisionConflict:return "RevisionConflict";
      case Status::AuthFailure:return "AuthFailure";
      case Status::BackendFailure:return "BackendFailure";
      case Status::BadArgument:return "BadArgument";
      case Status::EngineFailure:return "EngineFailure";
    }
    return "Unknown";
}
} // namespace diamond_v291
