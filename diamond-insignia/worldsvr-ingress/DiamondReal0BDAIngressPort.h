#pragma once
// CABAL v291: original WorldSvr ProcSystem::DoProcessDataCtx 0BDA hook port.
// This header has ZERO SQL, loading, sidecar, or in-game mutation functions.
// Default production mode NEVER consumes a packet; original WorldSvr handler
// always gets it. No v291 S2C ABI or cmd46/47 save proof currently exists.
// The opt-in ABI is SOURCE-ONLY until a vetted host implements both
// game-memory reconciliation and a verified client reply.
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace DiamondReal0BDAIngressPort {
constexpr std::uint16_t kOpcode=0x0BDAu;
constexpr std::uint16_t kMagic=0xB7E2u;
constexpr std::uint32_t kAbi=1u;
constexpr std::uint16_t U16(const unsigned char* p) noexcept {
    return static_cast<std::uint16_t>(p[0]) |
           static_cast<std::uint16_t>(p[1])<<8;
}
inline bool IsCandidate(const void* frame,std::size_t len) noexcept {
    if(!frame || len<14 || len>1054 || len%2!=0)return false;
    const auto* data=static_cast<const unsigned char*>(frame);
    if(U16(data)!=kMagic || U16(data+2)!=len ||
       U16(data+8)!=kOpcode)return false;
    const auto count=U16(data+10);
    return count>0 && count<=521 && len==12u+std::size_t(count)*2u;
}
enum class PortRoute : std::uint8_t {
    ForwardOriginal, ConsumedVerifiedReply, InDoubtNoReplay
};
struct HostBinding {
    std::uint32_t abi=kAbi;
    void* trustedHost=nullptr;
    // This callback is NOT provided in this repository. A future vetted
    // implementation must hold the original WorldSvr owner lease, prove
    // selection semantics and GameData coherence, atomically commit,
    // independently verify cmd46/47 AND send the exact known-good v291
    // reply BEFORE returning ConsumedVerifiedReply. It must not return
    // ForwardOriginal after any durable write/unknown SQL outcome.
    PortRoute (*handleVerified)(void* host,const void* worldUserCtx,
        const void* packet,std::size_t packetLen,int* nativeReturn) noexcept=nullptr;
};
#if defined(DIAMOND_0BDA_UNSAFE_EXPERIMENTAL_BINDING)
#error "Never enable unreviewed Diamond 0BDA binding in live WorldSvr"
#endif
// The v14 source clone intentionally has NO native binder until a
// separate verified response+memory adapter exists. This prevents SQL
// mutation followed by original opcode dispatch or missing client reply.
inline bool InstallVerifiedHost(const HostBinding*) noexcept {
    return false;
}
inline bool Process(const void*,const void*,std::size_t,int*) noexcept {
    return false; // ALWAYS FORWARD original unchanged
}
} // namespace DiamondReal0BDAIngressPort
