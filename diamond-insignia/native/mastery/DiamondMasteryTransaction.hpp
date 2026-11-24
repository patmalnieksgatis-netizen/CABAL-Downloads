#pragma once
// Host-neutral Diamond mastery service. Pure gameplay rules plus a storage
// contract. No packet parsing, binary hooks, SQL, sockets or live installation.
// The authenticated owner and request ID must come from the authorized host.
#include "../diamond_rules.hpp"
#include <cstdint>

namespace diamond::mastery {
struct Request {
    std::uint32_t user=0;
    std::uint64_t intent=0;
    std::uint32_t revision=0;
    int mastery_id=0;
};
struct Operation {
    Request request{};
    TrustedState before{};
    TrustedState after{};
};
enum class StorageStatus { Rejected, Committed, Uncertain };
struct Receipt {
    StorageStatus status=StorageStatus::Rejected;
    std::uint32_t user=0;
    std::uint64_t intent=0;
    std::uint32_t revision=0;
    int mastery_id=0;
    int level=0;
    int remaining_points=0;
};
class Store {
public:
    virtual ~Store()=default;
    // Read must return the authoritative current user state.
    virtual bool Read(std::uint32_t user,TrustedState& out)=0;
    // Implementations MUST compare the entire relevant before-state,
    // enforce unique (user,intent), and commit level, points, revision
    // and receipt together. An uncertain write is never retried here.
    virtual Receipt Commit(const Operation& operation)=0;
};
enum class Status { Rejected, CommittedPendingSync, RecoveryRequired };
struct Result {
    Status status=Status::Rejected;
    Error rule=Error::Untrusted;
    Receipt receipt{};
};
inline Result Execute(Store& store,const Request& req,
                      const std::map<int,Mastery>& catalog) {
    Result result{};
    if(!req.user || !req.intent || !req.revision)return result;
    Operation operation{};
    operation.request=req;
    if(!store.Read(req.user,operation.before))return result;
    const auto proposal=mastery_level_up(operation.before,catalog,
                                         req.mastery_id,req.revision);
    result.rule=proposal.result;
    if(proposal.result!=Error::Ok || !proposal.requires_atomic_commit)
        return result;
    operation.after=proposal.after;
    try {
        result.receipt=store.Commit(operation);
    } catch(...) {
        // Storage may have committed before throwing. No automatic retry.
        result.status=Status::RecoveryRequired;
        return result;
    }
    const auto& r=result.receipt;
    if(r.status==StorageStatus::Rejected)return result;
    if(r.status!=StorageStatus::Committed ||
       r.user!=req.user || r.intent!=req.intent ||
       r.revision!=operation.after.revision ||
       r.mastery_id!=req.mastery_id ||
       r.level!=operation.after.levels.at(req.mastery_id) ||
       r.remaining_points!=operation.after.free_points) {
        result.status=Status::RecoveryRequired;
        return result;
    }
    // A receipt alone does not establish online WorldSvr/client state.
    result.status=Status::CommittedPendingSync;
    return result;
}
} // namespace diamond::mastery
