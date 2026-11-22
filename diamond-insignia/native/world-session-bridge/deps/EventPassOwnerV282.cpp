#include "EventPassOwnerV282.h"
#include <cstring>
namespace EventPassOwnerV282 {
bool Resolve(const void* userData, OwnerIdentity* out) {
    if (!out) return false;
    *out=OwnerIdentity{};
    if (!userData) return false;
    const auto* p=static_cast<const unsigned char*>(userData);
    std::memcpy(&out->userNum,p+kUserNumOffset,sizeof(out->userNum));
    std::memcpy(&out->characterIdx,p+kCharacterIdxOffset,sizeof(out->characterIdx));
    return out->userNum!=0 && out->characterIdx!=0;
}
}