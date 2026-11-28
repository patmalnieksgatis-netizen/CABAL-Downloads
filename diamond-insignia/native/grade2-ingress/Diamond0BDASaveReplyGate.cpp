#include "Diamond0BDASaveReplyGate.h"
namespace diamond_v291::gradeup0bda {
ReplyGate StageCandidateSuccess(const DiamondWorldSaveBarrier& durableSave,
                                bool clientStatusReadAt6Verified,
                                bool matchingNativeSendAbiVerified) noexcept {
    ReplyGate result{};
    if(!durableSave.MaySendSuccess()) {
        result.result=ReplyGateResult::NoWorldSaveProof;
        return result;
    }
    if(!clientStatusReadAt6Verified ||
       !matchingNativeSendAbiVerified) {
        result.result=ReplyGateResult::MissingResponseAbiAttestation;
        return result;
    }
#ifndef DIAMOND_ENABLE_0BDA_CLONE_TRIAL
    result.result=ReplyGateResult::Blocked;
#else
    // The exact v291 reader consumes status at +6; the original native
    // sender call accepts (USERCONTEXT*, bytes, 7). A matched host must
    // still own the live session/fence before passing bytes to transport.
    result.bytes={0xE2,0xB7,0x07,0x00,0xDA,0x0B,0x01};
    result.result=ReplyGateResult::CloneCandidateEncoded;
    result.canSendToClient=true;
#endif
    return result;
}
} // namespace diamond_v291::gradeup0bda
