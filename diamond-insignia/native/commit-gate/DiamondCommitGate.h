#pragma once
// Diamond Insignia v291: authoritative WorldSvr commit gate, ABI-independent.
// Does not parse client packets, modify WorldSvr, open SQL connections or
// ever accept the UserNum from client-controlled bytes.
#include "diamond_abi.h"
#include <cstdint>

namespace diamond_v291 {
struct Request {
    std::uint32_t expectedRevision = 0;
    std::uint32_t command = 0;
    std::int32_t masteryId = 0;
};
struct Identity {
    std::uint32_t userNum = 0;
    std::uint32_t characterIdx = 0;
};
// The persisted receipt and every resource write MUST share the *same* DB
// transaction. It is not safe to use this contract with asynchronous DBA
// inventory persistence until a durable recovery/outbox bridge is implemented.
struct Receipt {
    Request request;
    cabal_diamond_evaluation applied{};
};
enum class Lookup : std::uint8_t { Fresh, SameCommitted, ConflictingCommitted, Failure };
enum class Status : std::uint8_t {
    Applied, Replayed, RuleRejected, RevisionConflict, AuthFailure,
    BackendFailure, BadArgument, EngineFailure
};
struct Result {
    Status status = Status::BadArgument;
    int ruleError = 0;
    cabal_diamond_evaluation evaluation{};
};
class Backend {
public:
    virtual ~Backend() = default;
    // Verify the opaque in-memory WorldSvr session, exclusively lock its
    // authoritative account, and start a DB transaction. Return a trusted
    // account/character; never derive identity from the client request.
    virtual bool begin(const void* trustedWorldSession, Identity& owner) = 0;
    // Lookup committed operations for (trusted UserNum, expectedRevision).
    // Returns SameCommitted only when command + masteryId ALSO match.
    virtual Lookup receipt(std::uint32_t expectedRevision, const Request& request,
                           Receipt& committed) = 0;
    // Under the same lock, load actual authoritative WExp, ticket item ID
    // 33554961 count, Gold/Platinum, opened slots, mastery levels, revision.
    // All pointer members in state must live until the transaction ends.
    virtual bool trustedState(cabal_diamond_state& state) = 0;
    // ONE durable COMMIT of all server inventory and WExp debits, Diamond
    // progression, mastery levels, revision and Receipt. If not achievable,
    // fail without mutation. No success response before durable commit.
    virtual bool commitAll(const Identity& owner, const Request& request,
                           const cabal_diamond_evaluation& proposed) = 0;
    // Releases the exclusive lock and transaction. Must be safe following
    // failure or success. An actual backend must rollback after failures.
    virtual void release(bool committed) noexcept = 0;
};

// The caller MUST only provide a WorldSvr-authenticated session pointer.
Result Execute(const cabal_diamond_engine* engine, Backend& backend,
               const void* authenticatedWorldSession, const Request& request);
const char* StatusName(Status status) noexcept;
} // namespace diamond_v291
