#pragma once
// Cabal v291 0BDA clone-only WorldSvr command ingress integration.
// PacketManager.h from owner's archived WorldSvrRealm has:
//   PROCESSDATACONTEXT { int* pUserCtx; char* cpPacket; WORD iLen; int iUniqIdx; ... };
// Exact real WorldSvr Platinum 0B10 handler reads [rsi+0] and [rsi+8].
// This adapter has NO live command registry hooks or S2C serializer.
#include "DiamondGradeUp0BDA.h"
#include <cstddef>
#include <cstdint>
namespace diamond_v291::gradeup0bda {
// Opaque layout mirrored from the owner's independent archive.
// Content and session identity MUST be checked by the host adapter.
// The five integer fields are never used for authorization.
struct ProcessDataContext {
    const void* pUserCtx=nullptr;
    const std::uint8_t* cpPacket=nullptr;
    std::uint16_t iLen=0;
    std::int32_t iUniqIdx=0;
    std::int32_t _iData0=0;
    std::int32_t _iData1=0;
    std::int32_t _iData2=0;
};
static_assert(sizeof(void*)==8,"original WorldSvr requires x86_64");
static_assert(offsetof(ProcessDataContext,pUserCtx)==0,"WorldSvr user pointer ABI");
static_assert(offsetof(ProcessDataContext,cpPacket)==8,"WorldSvr packet pointer ABI");
static_assert(offsetof(ProcessDataContext,iLen)==16,"WorldSvr packet length ABI");
static_assert(offsetof(ProcessDataContext,iUniqIdx)==20,"WorldSvr uniqueness ABI");
static_assert(sizeof(ProcessDataContext)==40,"WorldSvr context size ABI");
constexpr std::uint32_t kHostProofAdapterVersion=1;
// Obtain proof through server-owned, trusted WorldSvr state only, while the
// host holds a character-scoped lock. The raw packet entries may be used as
// proposed slot selectors, NEVER as values of ticket quantity or entitlement.
// This callback is not implemented by the library: real-game ABI unknown.
using AttestWorldProof = bool(*)(void* hostContext,
                                const void* authenticatedWorldSession,
                                std::uint32_t verifiedProcessLayer,
                                const Candidate& untrustedC2s,
                                WorldProof& outServerProof) noexcept;
struct HostAdapter {
    std::uint32_t version=0;
    AttestWorldProof attest=nullptr;
    void* context=nullptr;
};
enum class DispatchState : std::uint8_t {
    Original, InvalidFrame, Disabled, CloneBackendAppliedPendingSaveProof,
    CloneBackendRejected
};
struct DispatchResult {
    DispatchState state=DispatchState::InvalidFrame;
    bool maySendS2cSuccess=false;
    bool hostStateWasChanged=false; // shadow-only diagnostic; NEVER a durable claim
};
// transportSizeVerified is the *network-validated* complete frame byte count,
// not one of the client bytes. The host verifies checksum/MAC before calling;
// this code does not know how the proprietary original checksum is validated.
DispatchResult Dispatch(const ProcessDataContext* ctx,
                        std::size_t transportSizeVerified,
                        bool originalTransportIntegrityVerified,
                        std::uint32_t verifiedProcessLayer,
                        const HostAdapter& trustedHost,
                        diamond::DiamondCommandService& service) noexcept;
} // namespace diamond_v291::gradeup0bda
