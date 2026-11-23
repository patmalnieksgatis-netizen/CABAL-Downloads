#include "Diamond0BDASaveReplyGate.h"
namespace diamond_v291::gradeup0bda {
ReplyGate StageCandidateSuccess(const DiamondWorldSaveBarrier& durableSave,
                                bool clientStatusReadAt6Verified,
                                bool matchingRuntimeS2cResponseAbiVerified) noexcept {
    ReplyGate result{};
    if(!durableSave.MaySendSuccess()) {
        result.result=ReplyGateResult::NoWorldSaveProof;
        return result;
    }
    if(!clientStatusReadAt6Verified ||
       !matchingRuntimeS2cResponseAbiVerified) {
        result.result=ReplyGateResult::MissingResponseAbiAttestation;
        return result;
    }
#ifndef DIAMOND_ENABLE_0BDA_CLONE_TRIAL
    result.result=ReplyGateResult::Blocked;
#else
    // Only a synthetic candidate. These bytes NEVER go to a socket in this
    // module, even under the clone trial macro. Actual server S2C ABI has
    // not yet been reproduced from a functioning grade-2 WorldSvr.
    result.bytes={0xE2,0xB7,0x07,0x00,0xDA,0x0B,0x01};
    result.result=ReplyGateResult::CloneCandidateEncoded;
#endif
    result.canSendToClient=false;
    return result;
}
} // namespace diamond_v291::gradeup0bda
