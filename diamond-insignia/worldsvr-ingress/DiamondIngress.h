#pragma once
// CABAL v291 WorldSvr C2S Merit ingress observer.
// Passive-only by design: does not consume a packet, send a response, hook
// any address, change the server state, or call a DB/client. Fail-open to
// the original Gold/Platinum/other Merit dispatcher on every input.
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <atomic>
namespace DiamondIngress {
constexpr std::uint16_t kClassicMagic=0xB7E2;
constexpr std::uint16_t kMasteryLevelUp=0x09F3;
constexpr std::size_t kHeaderSize=10;
constexpr std::size_t kObservedLevelUpSize=18;
struct Observation {
    bool candidate=false;
    std::uint32_t mastery_id=0;
    std::uint32_t second_field=0; // unknown ABI; never used for authorization
};
inline std::uint16_t U16(const std::uint8_t* b) noexcept {
    return static_cast<std::uint16_t>(b[0]) |
           static_cast<std::uint16_t>(static_cast<std::uint16_t>(b[1]) << 8);
}
inline std::uint32_t U32(const std::uint8_t* b) noexcept {
    return static_cast<std::uint32_t>(b[0]) |
           (static_cast<std::uint32_t>(b[1])<<8) |
           (static_cast<std::uint32_t>(b[2])<<16) |
           (static_cast<std::uint32_t>(b[3])<<24);
}
inline Observation Inspect(const void* bytes,std::size_t trusted_byte_count) noexcept {
    Observation r;
    if (!bytes || trusted_byte_count!=kObservedLevelUpSize) return r;
    const auto* p=static_cast<const std::uint8_t*>(bytes);
    if (U16(p)!=kClassicMagic || U16(p+2)!=trusted_byte_count ||
        U16(p+8)!=kMasteryLevelUp) return r;
    const auto candidate=U32(p+10);
    if (candidate<159 || candidate>474) return r;
    r.candidate=true;
    r.mastery_id=candidate;
    r.second_field=U32(p+14);
    return r;
}
inline bool Enabled() noexcept {
    static const bool enabled=[](){
        const char* s=std::getenv("CABAL_DIAMOND_PASSIVE_OBSERVE");
        return s && std::strcmp(s,"1")==0;
    }();
    return enabled;
}
inline bool ShouldLog() noexcept {
    if(!Enabled())return false;
    static std::atomic<unsigned> counter{0};
    return counter.fetch_add(1,std::memory_order_relaxed)<16;
}
} // namespace DiamondIngress
