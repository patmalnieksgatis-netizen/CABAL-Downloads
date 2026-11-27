#include "DiamondWarExpAccounting.h"
#include <cassert>
#include <cstdint>
#include <iostream>
#include <limits>
using namespace diamond_v291::real_gamedata;
int main() {
    const auto maximum=std::numeric_limits<std::int64_t>::max();
    for(const auto balance:{std::int64_t{30000},std::int64_t{40000},maximum}) {
        for(const auto used:{std::int64_t{0},std::int64_t{7},maximum-30000}) {
            const WarExpLedger before{balance,100000,used};
            const auto result=PlanWarExpDebit(before,30000);
            assert(result.valid && result.after.current==balance-30000 &&
                   result.after.earned==100000 && result.after.used==used+30000);
            assert(std::uint64_t(result.after.current)+std::uint64_t(result.after.used)==
                   std::uint64_t(balance)+std::uint64_t(used));
        }
    }
    assert(!PlanWarExpDebit({29999,0,0},30000).valid);
    assert(!PlanWarExpDebit({30000,0,maximum-29999},30000).valid);
    assert(!PlanWarExpDebit({-1,0,0},30000).valid);
    assert(!PlanWarExpDebit({30000,-1,0},30000).valid);
    assert(!PlanWarExpDebit({30000,0,-1},30000).valid);
    assert(!PlanWarExpDebit({30000,0,0},0).valid);
    assert(!PlanWarExpDebit({30000,0,0},-1).valid);
    std::cout<<"NATIVE_WEXP_CURRENT_USED_AND_EARNED_ACCOUNTING=PASS\n"
             <<"WEXP_BIGINT_OVERFLOW_UNDERFLOW_AND_NEGATIVE_INPUT_REJECTED=PASS\n";
}
