// CABAL v291 / EP39 Diamond — native, offline-validated rules core.
// No WorldSvr packet binding or SQL side effects. Never trust client-supplied state.
// Real server must populate TrustedState, authorize, and commit atomically.
// License: project-local integration scaffold.
#pragma once
#include <cstdint>
#include <cstddef>
#include <map>
#include <set>
#include <vector>
#include <limits>
namespace diamond {
enum class Error {
  Ok, Untrusted, Stale, AlreadyDiamond, PlatinumNotMaxed, MissingPlatinum,
  MissingWExp, MissingTickets, InvalidConfig, NotDiamond, UnknownMastery,
  LockedCategory, SlotNotOpen, LinkedSemanticsUnverified, MaxLevel,
  InvalidProgress, MissingPrerequisite, InsufficientPoints
};
struct Mastery {
  int id = 0, category = 0, max_level = 0;
  int prerequisite_id = 0, prerequisite_level = 0, linked_id = 0;
  std::vector<int> level_cost;
};
struct TrustedState {
  bool authoritative = false;    // Set only by WorldSvr, never client packet
  bool platinum_maxed = false;    // Verified from authoritative Platinum state
  bool platinum_badge = false;
  int badge_grade = 1;
  uint32_t revision = 0;
  uint64_t wexp = 0;
  uint32_t tickets = 0;
  int free_points = 0;
  std::set<int> active_categories;
  std::set<int> server_open_slots;
  std::map<int,int> levels;
};
struct TransactionProposal {
  Error result = Error::InvalidConfig;
  TrustedState after;
  // *Only* a proposal. Caller must debit/commit all resources atomically.
  bool requires_atomic_commit = false;
  uint32_t expected_revision = 0;
};
constexpr uint64_t kDiamondRankWExp = 30000;
constexpr uint32_t kDiamondRankTickets = 100;
constexpr uint32_t kRequiredDonorItemId = 33554961;
// 4 main categories and their 12 mutually exclusive subcategories.
// The category unlock packets, layout, and effects are NOT yet established.
inline int category_root(int c) {
  if (c == 11 || c == 12 || c == 13 || c == 14) return 11;
  if (c == 15 || c == 16 || c == 17 || c == 18) return 15;
  if (c == 19 || c == 20 || c == 21 || c == 22) return 19;
  if (c == 23 || c == 24 || c == 25 || c == 26) return 23;
  return -1;
}
inline bool valid_categories(const std::set<int>& categories) {
  std::map<int,int> chosen;
  for (int c: categories) {
    const int root = category_root(c);
    if (root == -1) return false;
    if (c != root && ++chosen[root] > 1) return false;
  }
  return true;
}
inline bool valid_levels(const TrustedState& s,const std::map<int,Mastery>& specs) {
  for (const auto& entry: s.levels) {
    const auto it = specs.find(entry.first);
    if (it == specs.end() || entry.second < 0 || entry.second > it->second.max_level)
      return false;
  }
  return true;
}
inline TransactionProposal rank_up(const TrustedState& s,uint32_t expected_revision) {
  TransactionProposal r; r.after=s; r.expected_revision=expected_revision;
  if (!s.authoritative) {r.result=Error::Untrusted; return r;}
  if (s.revision!=expected_revision || s.revision>=static_cast<uint32_t>(std::numeric_limits<int32_t>::max()))
    {r.result=Error::Stale;return r;}
  if (s.badge_grade==2){r.result=Error::AlreadyDiamond;return r;}
  if (s.badge_grade!=1 || !s.platinum_badge) {r.result=Error::MissingPlatinum;return r;}
  if (!s.platinum_maxed){r.result=Error::PlatinumNotMaxed;return r;}
  if (s.wexp<kDiamondRankWExp){r.result=Error::MissingWExp;return r;}
  if (s.tickets<kDiamondRankTickets){r.result=Error::MissingTickets;return r;}
  r.after.wexp-=kDiamondRankWExp;
  r.after.tickets-=kDiamondRankTickets;
  r.after.badge_grade=2;
  ++r.after.revision;
  r.result=Error::Ok; r.requires_atomic_commit=true;
  return r;
}
inline TransactionProposal mastery_level_up(const TrustedState& s,
                       const std::map<int,Mastery>& specs, int id, uint32_t expected_revision) {
  TransactionProposal r; r.after=s; r.expected_revision=expected_revision;
  if (!s.authoritative){r.result=Error::Untrusted;return r;}
  if (s.revision!=expected_revision || s.revision==std::numeric_limits<uint32_t>::max())
    {r.result=Error::Stale;return r;}
  if (s.badge_grade!=2){r.result=Error::NotDiamond;return r;}
  if (!valid_categories(s.active_categories) || !valid_levels(s,specs) || s.free_points<0)
    {r.result=Error::InvalidProgress;return r;}
  auto it=specs.find(id);
  if (it==specs.end() || id<159 || id>474){r.result=Error::UnknownMastery;return r;}
  const Mastery& m=it->second;
  if (m.id!=id || category_root(m.category)==-1 || m.max_level<1 ||
      m.level_cost.size()!=static_cast<std::size_t>(m.max_level)){
    r.result=Error::InvalidConfig; return r;
  }
  if (s.active_categories.count(m.category)==0){r.result=Error::LockedCategory;return r;}
  if (s.server_open_slots.count(id)==0){r.result=Error::SlotNotOpen;return r;}
  // Important: 108 linked mastery interactions are not yet known.
  if (m.linked_id!=0){r.result=Error::LinkedSemanticsUnverified;return r;}
  const auto levelit=s.levels.find(id);
  const int level=levelit==s.levels.end()?0:levelit->second;
  if (level>=m.max_level){r.result=Error::MaxLevel;return r;}
  if (m.prerequisite_id!=0){
    auto pre=s.levels.find(m.prerequisite_id);
    if (pre==s.levels.end() || pre->second<m.prerequisite_level){
      r.result=Error::MissingPrerequisite;return r;
    }
  }
  const int cost=m.level_cost[static_cast<size_t>(level)];
  if (cost<0){r.result=Error::InvalidConfig;return r;}
  if (s.free_points<cost){r.result=Error::InsufficientPoints;return r;}
  r.after.free_points-=cost;
  r.after.levels[id]=level+1;
  ++r.after.revision;
  r.result=Error::Ok;r.requires_atomic_commit=true;
  return r;
}
} // namespace diamond
