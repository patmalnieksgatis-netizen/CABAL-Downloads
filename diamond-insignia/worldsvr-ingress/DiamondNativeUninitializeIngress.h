#pragma once
#include "DiamondWorldSvrRankUpAdapter.h"

namespace diamond_v291::lifecycle {
// Pinned WorldSvr registers A4A130 in user opcode 143 at 8EF24B..8EF28D.
// That handler reaches 7DF520, which resets character data through AD6060.
// This binding covers character-selection uninitialization. Transport close,
// forced removal and reset callers outside opcode 143 require separate routes.
inline constexpr std::size_t kUninitialize=143;
inline constexpr std::uintptr_t kNativeUninitialize=0xa4a130;
inline completion::WorldSvrRankUpAdapter* adapter=nullptr;
inline diamond_v19::Handler original=nullptr;

inline int Handle(void* layer,diamond_v19::ContextPrefix* context) noexcept {
    if(context && context->user)adapter->BeforeNativeUninitialize(context->user);
    return original(layer,context);
}

// Called once under the same pre-dispatch startup barrier used for Diamond.
// The adapter and wrapper remain loaded for the entire process lifetime.
// Preserve the native procedure object, locking byte and original return code.
inline bool Install(const diamond_v19::Host& host,
                    completion::WorldSvrRankUpAdapter& target,
                    diamond_v19::Handler expectedOriginal=
                        reinterpret_cast<diamond_v19::Handler>(kNativeUninitialize)) noexcept {
    if(adapter || !host.exactElfVerified || !host.startupBeforeAnyDispatch ||
       !host.nativeObjectLifetimeVerified || !host.userTable ||
       host.readableSlots<=kUninitialize || !expectedOriginal)return false;
    auto* map=host.userTable[kUninitialize];
    if(!map || diamond_v19::Read<std::uint8_t>(map,0x20)!=1)return false;
    auto* first=diamond_v19::Read<diamond_v19::Handler*>(map,0);
    auto* end=diamond_v19::Read<diamond_v19::Handler*>(map,8);
    if(!first || end!=first+1 || *first!=expectedOriginal)return false;
    original=*first;
    adapter=&target;
    *first=&Handle;
    return true;
}
} // namespace diamond_v291::lifecycle
