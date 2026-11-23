// Offline test of WorldSvr integration boundary, using a serialized account transaction.
// NO live WorldSvr, SQL, network packets, or user data are touched.
#include "diamond_transaction.hpp"
#include <cassert>
#include <cstdint>
#include <iostream>
#include <limits>
#include <map>
#include <mutex>
#include <utility>
using namespace diamond;
class FakeStore final : public IAtomicWorldState {
 public:
  TrustedState state;
  std::uint64_t accepted_nonce = 13579;
  std::uint32_t accepted_user = 7;
  bool fail_before_commit = false;
  int durable_commits = 0;
  int rollback_count = 0;
  OperationResult apply(const Session& s,const Command& c,
                        const Decision& decide) override {
    std::lock_guard<std::mutex> lock(mutex_);
    if (s.user_num!=accepted_user || s.session_nonce!=accepted_nonce)
      return {OperationStatus::Unauthenticated,Error::Untrusted,state.revision};
    const TrustedState snapshot=state;
    const TransactionProposal proposal=decide(snapshot);
    if (proposal.result!=Error::Ok || !proposal.requires_atomic_commit) {
      ++rollback_count;
      return {OperationStatus::Rejected,proposal.result,state.revision};
    }
    if (c.expected_revision!=state.revision ||
        proposal.expected_revision!=state.revision ||
        proposal.after.revision!=state.revision+1 ||
        !proposal.after.authoritative || !state.authoritative) {
      ++rollback_count;
      return {OperationStatus::CommitConflict,Error::Stale,state.revision};
    }
    // Important: injected inventory/SQL failure rolls back the *entire* snapshot.
    if (fail_before_commit) {
      ++rollback_count;
      return {OperationStatus::StorageFailure,Error::InvalidConfig,state.revision};
    }
    state=proposal.after;
    ++durable_commits;
    return {OperationStatus::Applied,Error::Ok,state.revision};
  }
 private:
  std::mutex mutex_;
};
int main() {
  FakeStore store;
  store.state.authoritative=true;
  store.state.badge_grade=1;
  store.state.platinum_badge=true;
  store.state.platinum_maxed=true;
  store.state.wexp=40000;
  store.state.tickets=105;
  store.state.revision=4;
  const Session owner{7,13579};
  const Session attacker{8,13579};
  const Command rank{CommandType::RankUp,4,0};
  std::map<int,Mastery> specs;
  Mastery m;m.id=159;m.category=11;m.max_level=2;
  m.level_cost={10,20};specs.emplace(159,m);
  DiamondCommandService service(store,specs);
  auto denied=service.handle(attacker,rank);
  assert(denied.status==OperationStatus::Unauthenticated && store.durable_commits==0);
  store.fail_before_commit=true;
  auto failure=service.handle(owner,rank);
  assert(failure.status==OperationStatus::StorageFailure);
  assert(store.state.badge_grade==1 && store.state.wexp==40000 &&
         store.state.tickets==105 && store.state.revision==4);
  store.fail_before_commit=false;
  auto good=service.handle(owner,rank);
  assert(good.status==OperationStatus::Applied && good.new_revision==5);
  assert(store.state.badge_grade==2 && store.state.wexp==10000 &&
         store.state.tickets==5 && store.state.revision==5);
  // Same original packet repeated must not debit twice.
  auto replay=service.handle(owner,rank);
  assert(replay.status==OperationStatus::Rejected &&
         replay.rule==Error::Stale && store.state.wexp==10000 &&
         store.state.tickets==5 && store.durable_commits==1);
  auto invalid=service.handle(owner,{CommandType::MasteryLevelUp,5,666});
  assert(invalid.status==OperationStatus::Rejected &&
         invalid.rule==Error::UnknownMastery);
  store.state.free_points=50;
  store.state.active_categories.insert(11);
  store.state.server_open_slots.insert(159);
  auto purchase=service.handle(owner,{CommandType::MasteryLevelUp,5,159});
  assert(purchase.status==OperationStatus::Applied && purchase.new_revision==6);
  assert(store.state.free_points==40 && store.state.levels.at(159)==1);
  store.fail_before_commit=true;
  auto fail_purchase=service.handle(owner,{CommandType::MasteryLevelUp,6,159});
  assert(fail_purchase.status==OperationStatus::StorageFailure);
  assert(store.state.revision==6 && store.state.free_points==40 &&
         store.state.levels.at(159)==1);
  store.fail_before_commit=false;
  auto second=service.handle(owner,{CommandType::MasteryLevelUp,6,159});
  assert(second.status==OperationStatus::Applied);
  assert(store.state.free_points==20 && store.state.levels.at(159)==2);
  assert(store.durable_commits==3 && store.rollback_count>=3);
  {auto c=specs;c.at(159).linked_id=160;
   // a new eligible purchase to check fail-closed linked relationships
   FakeStore test;
   test.state=store.state;
   test.state.levels[159]=1;
   test.accepted_user=7;
   DiamondCommandService linked(test,c);
   const auto res=linked.handle(owner,{CommandType::MasteryLevelUp,7,159});
   assert(res.status==OperationStatus::Rejected &&
          res.rule==Error::LinkedSemanticsUnverified &&
          test.durable_commits==0);
  }
  std::cout<<"DIAMOND_WORLD_COMMAND_TRANSACTION_TESTS=PASS\n";
}
