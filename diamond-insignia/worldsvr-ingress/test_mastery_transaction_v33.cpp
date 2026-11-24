#include "../native/mastery/DiamondMasteryTransaction.hpp"
#include <cassert>
#include <cstdio>
#include <stdexcept>
using namespace diamond;
using namespace diamond::mastery;
struct Fixture final : Store {
    TrustedState state;
    unsigned commits=0;
    bool uncertain=false, wrong_receipt=false, throw_commit=false;
    std::set<std::uint64_t> intents;
    ReadStatus pending=ReadStatus::Ready;
    ReadStatus Read(std::uint32_t user,TrustedState& out) override {
        if(user!=7)return ReadStatus::Missing;
        if(pending!=ReadStatus::Ready)return pending;
        out=state;return ReadStatus::Ready;
    }
    Receipt Commit(const Operation& o) override {
        ++commits;
        if(pending!=ReadStatus::Ready || o.before.revision!=state.revision || !intents.insert(o.request.intent).second)
            return {};
        if(uncertain){
            pending=ReadStatus::PendingRecovery;
            return {StorageStatus::Uncertain};
        }
        state=o.after;
        pending=(throw_commit || wrong_receipt)?ReadStatus::PendingRecovery:ReadStatus::PendingSync;
        if(throw_commit)throw std::runtime_error("synthetic storage disconnect");
        return {StorageStatus::Committed,o.request.user,o.request.intent,
                state.revision,o.request.mastery_id,
                state.levels.at(o.request.mastery_id),
                state.free_points+(wrong_receipt?1:0)};
    }
};
static Fixture fixture() {
    Fixture f;
    f.state.authoritative=true;f.state.badge_grade=2;
    f.state.revision=8;f.state.free_points=5;
    f.state.active_categories={11};f.state.server_open_slots={159};
    return f;
}
int main() {
    const std::map<int,Mastery> specs{{159,{159,11,2,0,0,0,{2,3}}}};
    const Request q{7,91,8,159};
    auto f=fixture();
    auto r=Execute(f,q,specs);
    assert(r.status==Status::CommittedPendingSync);
    assert(f.state.free_points==3 && f.state.revision==9 && f.commits==1);
    assert(Execute(f,{7,92,9,159},specs).status==Status::RecoveryRequired && f.commits==1);
    // Synthetic independent reconciliation completed.
    f.pending=ReadStatus::Ready;
    assert(Execute(f,q,specs).rule==Error::Stale && f.commits==1);
    assert(Execute(f,{8,92,9,159},specs).status==Status::Rejected && f.commits==1);
    auto u=fixture();u.uncertain=true;
    assert(Execute(u,q,specs).status==Status::RecoveryRequired && u.commits==1);
    auto w=fixture();w.wrong_receipt=true;
    assert(Execute(w,q,specs).status==Status::RecoveryRequired && w.commits==1);
    auto t=fixture();t.throw_commit=true;
    assert(Execute(t,q,specs).status==Status::RecoveryRequired && t.commits==1);
    assert(t.state.revision==9);
    assert(Execute(u,{7,93,8,159},specs).status==Status::RecoveryRequired && u.commits==1);
    assert(Execute(w,{7,94,9,159},specs).status==Status::RecoveryRequired && w.commits==1);
    assert(Execute(t,{7,95,9,159},specs).status==Status::RecoveryRequired && t.commits==1);
    std::puts("DIAMOND_MASTERY_TRANSACTION_FIXTURE=PASS");
}
