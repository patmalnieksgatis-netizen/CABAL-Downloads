#pragma once
#include <cstddef>
#include <cstdint>
namespace EventPassOwnerV282 {
static constexpr uint8_t kOwnerScopeAccount = 1;
static constexpr std::size_t kUserNumOffset = 0x0890;
static constexpr std::size_t kCharacterIdxOffset = 0x0A24;
struct OwnerIdentity {
    uint8_t ownerScope = kOwnerScopeAccount;
    uint32_t userNum = 0;
    uint32_t characterIdx = 0;
};
bool Resolve(const void* userData, OwnerIdentity* out);
}