#include "../DiamondBoundIngress.h"
#include <cassert>
#include <cstdlib>
#include <iostream>
int main(){
 setenv("CABAL_DIAMOND_SHADOW_TRIAL","ISOLATED_SYNTHETIC_USER_900001_ONLY",1);
 DiamondBoundIngress::Binding binding{};
 assert(!DiamondBoundIngress::InstallOnce(&binding));
 assert(DiamondBoundIngress::Process(reinterpret_cast<const void*>(1),nullptr,0)
        ==DiamondBoundIngress::Result::Disabled);
 std::cout<<"DIAMOND_DEFAULT_PLUGIN_CANNOT_WRITE=PASS\n";
}
