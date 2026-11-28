#include "Diamond0BDARealServer01Bridge.h"

namespace diamond_v291::real_gamedata {
diamond_v291::gradeup0bda::GameActionResult Execute0BDARealServer01(
    const void* worldUserCtx,const void* clientFrame,
    std::size_t verifiedFrameBytes,const Real0BDAHost& host,
    std::uint64_t reservedIntent) noexcept {
    using namespace diamond_v291::gradeup0bda;
    const auto candidate=ParseC2s(clientFrame,verifiedFrameBytes);
    if(candidate.state==PacketState::Other) {
        GameActionResult r{};r.state=GameActionState::NotDiamondCommand;
        return r;
    }
    if(candidate.state!=PacketState::Candidate) {
        GameActionResult r{};r.state=GameActionState::InvalidPacket;
        return r;
    }
    if(!host.authority || !host.transaction ||
       !host.ownerState.readLockedState ||
       !host.ownerState.exactWorldSvrLayoutAndHashVerified) {
        GameActionResult r{};r.state=GameActionState::MissingWorldAuthority;
        return r;
    }
    // All capability evidence is supplied by the trusted, locked WorldSvr
    // host. Nothing is derived from untrusted client packet bytes.
    AuthenticatedIngressHost native{};
    native.authority=host.authority;
    native.reservedIntent=reservedIntent;
    native.data=host.ownerState;
    native.game.abiVersion=1;
    native.game.context=host.transaction;
    native.game.commit=&CommitRealGameDataServer01;
    native.game.sql=host.sqlProof;
    // ExecuteAuthenticated0BDA owns the lease and retains it through
    // the GameData ODBC callback, which itself stages a copy, verifies
    // ownership and performs the 1-transaction SQL stored procedure.
    // Before returning PendingSaveProof, it verifies the durable receipt.
    // That is STILL NOT a cmd46/47 roundtrip, or a v291 S2C response.
    return ExecuteAuthenticated0BDA(
        worldUserCtx,clientFrame,verifiedFrameBytes,native);
}
} // namespace diamond_v291::real_gamedata
