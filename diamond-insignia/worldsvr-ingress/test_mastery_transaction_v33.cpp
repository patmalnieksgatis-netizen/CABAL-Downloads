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
    bool Read(std::uint32_t user,TrustedState& out) override {
        if(user!=7)return false;
        out=state;return true;
    }
    Receipt Commit(const Operation& o) override {
        ++commits;
        if(o.before.revision!=state.revision || !intents.insert(o.request.intent).second)
            return {};
        if(uncertain)return {StorageStatus::Uncertain};
        state=o.after;
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
    assert(Execute(f,q,specs).rule==Error::Stale && f.commits==1);
    assert(Execute(f,{8,92,9,159},specs).status==Status::Rejected && f.commits==1);
    auto u=fixture();u.uncertain=true;
    assert(Execute(u,q,specs).status==Status::RecoveryRequired && u.commits==1);
    auto w=fixture();w.wrong_receipt=true;
    assert(Execute(w,q,specs).status==Status::RecoveryRequired && w.commits==1);
    auto t=fixture();t.throw_commit=true;
    assert(Execute(t,q,specs).status==Status::RecoveryRequired && t.commits==1);
    assert(t.state.revision==9);
    std::puts("DIAMOND_MASTERY_TRANSACTION_FIXTURE=PASS");
}
