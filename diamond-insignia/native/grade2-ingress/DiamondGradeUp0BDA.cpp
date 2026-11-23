#include "DiamondGradeUp0BDA.h"
namespace diamond_v291::gradeup0bda {
namespace {
std::uint16_t U16(const std::uint8_t* p) noexcept {
    return static_cast<std::uint16_t>(p[0]) |
           static_cast<std::uint16_t>(p[1])<<8;
}
bool Authorized(const Candidate& packet,const WorldProof& proof) noexcept {
    if(!proof.authenticatedSession ||
       !proof.grade2ServerCatalogVerified ||
       !proof.gradeUpSemanticsVerified ||
       !proof.entriesAuthoritativelyMatched ||
       !proof.actualGameDataWexpBackendVerified ||
       proof.boundWorldSession==nullptr || !proof.userNum ||
       !proof.sessionNonce || !proof.revision ||
       proof.expectedCount!=packet.count)return false;
    for(std::size_t i=0;i<packet.count;++i) {
        if(packet.rawEntries[i]!=proof.serverEntries[i])return false;
    }
    return true;
}
}
Candidate ParseC2s(const void* ptr,std::size_t size) noexcept {
    Candidate result{};
    if(!ptr || size<10)return result;
    const auto* b=static_cast<const std::uint8_t*>(ptr);
    if(U16(b)!=0xB7E2u || U16(b+8)!=kOpcode) {
        result.state=PacketState::Other; // do NOT touch Platinum 0B10
        return result;
    }
    if(size<14 || U16(b+2)!=size || size>65535)return result;
    const auto count=U16(b+10);
    if(count==0 || count>kMaxAttestableEntries)return result;
    // Original client: count zero produces 14 bytes; positive count uses
    // 12+2*count (with count==1 also 14). Reject noncanonical layouts.
    const std::size_t expected=12+std::size_t(count)*2;
    if(expected!=size)return result;
    result.count=count;
    for(std::size_t i=0;i<count;++i)result.rawEntries[i]=U16(b+12+i*2);
    result.state=PacketState::Candidate;
    return result;
}
Result ExecuteCandidate(const void* packet,std::size_t size,
                        const WorldProof& proof,
                        diamond::DiamondCommandService& service) noexcept {
    Result result{};
    const auto parsed=ParseC2s(packet,size);
    if(parsed.state==PacketState::Other) {
        result.route=Route::Original;
        return result;
    }
    if(parsed.state!=PacketState::Candidate) {
        result.route=Route::Invalid;
        return result;
    }
    if(!Authorized(parsed,proof)) {
        result.route=Route::Disabled;
        return result;
    }
#if !defined(DIAMOND_ENABLE_0BDA_CLONE_TRIAL)
    (void)service;
    result.route=Route::Disabled;
#else
    try {
        // The client's checksum/list is not a user ID, revision, proof of
        // ticket count or of grade2 entitlement. Trusted state comes from
        // the session-bound server backend while it holds the owner lock.
        const diamond::Session session{proof.userNum,proof.sessionNonce};
        const diamond::Command command{
            diamond::CommandType::RankUp,proof.revision,0};
        result.transaction=service.handle(session,command);
        result.route=(result.transaction.status==diamond::OperationStatus::Applied)
            ? Route::CloneBackendAppliedPendingSaveProof : Route::Rejected;
    }catch(...) {
        result.route=Route::Rejected;
    }
#endif
    // CRITICAL: No S2C until a real cmd46/47 save, independent persisted
    // GameData inventory/WExp audit and a committed receipt are verified.
    // The exact 0BDA success response ABI remains unverified.
    result.maySendS2cSuccess=false;
    return result;
}
} // namespace diamond_v291::gradeup0bda
