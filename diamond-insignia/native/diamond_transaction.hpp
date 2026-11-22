// CABAL v291 Diamond: gameplay command integration seam with one-user atomic backend.
// Deliberately NO packet IDs, SQL table names, inventory offsets or live hook addresses.
#pragma once
#include "diamond_rules.hpp"
#include <cstdint>
#include <functional>
#include <utility>
namespace diamond {
enum class CommandType { RankUp, MasteryLevelUp };
struct Session {
  // Only the authenticated WorldSvr session adapter may construct these fields.
  std::uint32_t user_num = 0;
  std::uint64_t session_nonce = 0;
};
struct Command {
  CommandType type = CommandType::RankUp;
  std::uint32_t expected_revision = 0; // advisory client revision, verified in store
  int mastery_id = 0;
};
enum class OperationStatus {
  Applied, Rejected, Unauthenticated, StorageUnavailable,
  CommitConflict, StorageFailure
};
struct OperationResult {
  OperationStatus status = OperationStatus::StorageFailure;
  Error rule = Error::InvalidConfig;
  std::uint32_t new_revision = 0;
};
// The backend must:
//  - validate session belongs to user_num inside trusted server state;
//  - start a single authoritative user/character transaction and lock row;
//  - load grade, max Platinum flag, WExp, item-ID 33554961 count,
//    unlocked categories, opened slots and mastery levels from SERVER data;
//  - run decide() *inside* lock after loading, never on client-supplied stats;
//  - atomically save proposal.after and debit its WExp/inventory differences;
//  - rollback EVERYTHING if any write, inventory change or SQL update fails;
//  - compare against expected_revision in same transaction to reject replay;
//  - return Applied only after successful durable commit.
// This is the only integration boundary intended for the original WorldSvr.
class IAtomicWorldState {
 public:
  virtual ~IAtomicWorldState() = default;
  using Decision = std::function<TransactionProposal(const TrustedState&)>;
  virtual OperationResult apply(const Session& session,
                                const Command& command,
                                const Decision& decide) = 0;
};
class DiamondCommandService {
 public:
  explicit DiamondCommandService(IAtomicWorldState& backend,
                                const std::map<int,Mastery>& specs)
      : backend_(backend), specs_(specs) {}
  OperationResult handle(const Session& session, const Command& command) const {
    if (session.user_num==0 || session.session_nonce==0)
      return {OperationStatus::Unauthenticated,Error::Untrusted,0};
    if (command.type==CommandType::MasteryLevelUp &&
        (command.mastery_id<159 || command.mastery_id>474))
      return {OperationStatus::Rejected,Error::UnknownMastery,0};
    const auto decide=[&](const TrustedState& authoritative) -> TransactionProposal {
      if (command.type==CommandType::RankUp)
        return rank_up(authoritative,command.expected_revision);
      return mastery_level_up(authoritative,specs_,command.mastery_id,
                              command.expected_revision);
    };
    return backend_.apply(session,command,decide);
  }
 private:
  IAtomicWorldState& backend_;
  const std::map<int,Mastery>& specs_;
};
}  // namespace diamond
