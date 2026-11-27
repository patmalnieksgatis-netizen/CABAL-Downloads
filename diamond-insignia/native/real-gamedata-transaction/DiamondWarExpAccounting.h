#pragma once
// Matched WorldSvr spending path: current -= cost, used += cost; earned
// is unchanged. World packer -> DBAgent named bind order is verified by
// verify_native_host_contract.py. This header never touches RAM or SQL.
#include <cstdint>
#include <limits>

namespace diamond_v291::real_gamedata {
struct WarExpLedger {
    std::int64_t current=0;
    std::int64_t earned=0;
    std::int64_t used=0;
};
struct WarExpDebit {
    bool valid=false;
    WarExpLedger after{};
};
inline WarExpDebit PlanWarExpDebit(const WarExpLedger& before,
                                   std::int64_t cost) noexcept {
    if(before.current<0 || before.earned<0 || before.used<0 || cost<=0 ||
       before.current<cost ||
       before.used>std::numeric_limits<std::int64_t>::max()-cost)
        return {};
    return {true,{before.current-cost,before.earned,before.used+cost}};
}
} // namespace diamond_v291::real_gamedata
