#include "../DiamondIngress.h"
#include <cassert>
#include <iostream>
int main(){
 assert(DiamondIngress::Enabled());
 for(int i=0;i<16;++i)assert(DiamondIngress::ShouldLog());
 assert(!DiamondIngress::ShouldLog());
 std::cout<<"DIAMOND_INGRESS_RATE_LIMIT_TEST=PASS\n";
}
