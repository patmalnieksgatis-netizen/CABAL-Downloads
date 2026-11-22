// Synthetic shared-object shim for GitHub CI only.
// Not the archived WorldSvr source, not a game module, never deploy.
#include "../DiamondBoundIngress.h"
#if !defined(DIAMOND_ENABLE_SHADOW_TRIAL)
#error Build only for the isolated synthetic ingress loader test.
#endif
extern "C" __attribute__((visibility("default")))
int cabal_diamond_proc_bind_shadow_clone_v2(
    const DiamondBoundIngress::Binding* b) {
  return DiamondBoundIngress::InstallOnce(b)?0:-1;
}
extern "C" __attribute__((visibility("default")))
int cabal_diamond_proc_test_ingress_clone_v2(
    const void* context,const void* packet,std::size_t size) {
  return static_cast<int>(DiamondBoundIngress::Process(context,packet,size));
}
