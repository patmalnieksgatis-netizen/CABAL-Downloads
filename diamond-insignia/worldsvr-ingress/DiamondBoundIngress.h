#pragma once
// CABAL Diamond WorldSvr source binding. NOT a production game feature.
// Compile-time and run-time lab gates, synthetic UserNum=900001 only.
// Always preserves the original WorldSvr C2S dispatcher/response semantics.
#include "DiamondIngress.h"
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <mutex>

#if defined(DIAMOND_ENABLE_SHADOW_TRIAL)
#include "diamond_merit_world_entry.h"
#endif

namespace DiamondBoundIngress {
constexpr std::uint32_t kSyntheticUserNum=900001u;
constexpr std::uint32_t kBindingABI=3u; // acquire/release lifetime lease is mandatory

enum class Result : int {
  Unchanged=0, Disabled=1, CandidateNoHost=2, ShadowApplied=3,
  ShadowRejected=4, AuthRefused=5, BadEngine=6
};

#if defined(DIAMOND_ENABLE_SHADOW_TRIAL)
struct VerifiedIdentity {
  const void* authenticated_session=nullptr;
  std::uint32_t user_num=0;
  std::uint32_t expected_revision=0;
  // Supplied only by trusted, server-owned catalog/session lookups.
  // These booleans alone are insufficient: matched values must bind to packet.
  std::uint32_t server_catalog_grade_two_confirmed=0;
  std::uint32_t server_selector_confirms_diamond=0;
  std::uint32_t first_payload_dword_authoritatively_matched=0;
  std::uint32_t second_payload_dword_authoritatively_matched=0;
  std::uint32_t matched_first_payload_dword=0;
  std::uint32_t matched_second_payload_dword=0;
};
// Host must first acquire an AUTHENTICATED, EXCLUSIVE session lease.
// The lease keeps WorldSvr context and its server catalog state alive
// through WorldBridge's complete commit/abort. A mere lookup is unsafe.
// Both first/second DWORDs are UNTRUSTED inputs, not proof by themselves.
using TrustedAcquireLease=int (*)(void* authority_context,
                                  const void* server_owned_user_context,
                                  const DiamondIngress::Observation* observed,
                                  void** out_lease,VerifiedIdentity* output);
using TrustedReleaseLease=void (*)(void* authority_context,void* lease) noexcept;
struct Binding {
  std::uint32_t abi=kBindingABI;
  const cabal_diamond_engine* engine=nullptr;
  cabal_diamond_world_callbacks callbacks{};
  void* backend_context=nullptr;
  TrustedAcquireLease acquire_exclusive=nullptr;
  TrustedReleaseLease release_exclusive=nullptr;
  void* authority_context=nullptr;
};
struct ScopedLease {
  const Binding& host;
  void* token=nullptr;
  explicit ScopedLease(const Binding& binding) noexcept:host(binding){}
  ~ScopedLease() noexcept {
    if(token && host.release_exclusive)
      host.release_exclusive(host.authority_context,token);
  }
  ScopedLease(const ScopedLease&)=delete;
  ScopedLease& operator=(const ScopedLease&)=delete;
};
inline std::mutex& BindingMutex() {static std::mutex m;return m;}
inline Binding& BindingSlot() {static Binding b{};return b;}
inline bool& Installed() {static bool x=false;return x;}
inline bool ExactCloneOptIn() noexcept {
  const char* s=std::getenv("CABAL_DIAMOND_SHADOW_TRIAL");
  return s && std::strcmp(s,"ISOLATED_SYNTHETIC_USER_900001_ONLY")==0;
}
inline bool InstallOnce(const Binding* source) noexcept {
  if(!ExactCloneOptIn()||!source||source->abi!=kBindingABI||
     !source->engine||!source->acquire_exclusive||
     !source->release_exclusive||
     source->callbacks.version!=CABAL_DIAMOND_WORLD_BRIDGE_VERSION||
     !source->callbacks.begin_authenticated_locked||
     !source->callbacks.load_trusted_state||
     !source->callbacks.commit_durable||
     !source->callbacks.abort_transaction)return false;
  std::lock_guard<std::mutex> lock(BindingMutex());
  if(Installed())return false;
  BindingSlot()=*source;
  Installed()=true;
  return true;
}
inline Result Process(const void* server_owned_user_context,
                      const void* packet,std::size_t length) noexcept {
  if(!ExactCloneOptIn())return Result::Disabled;
  const auto observed=DiamondIngress::Inspect(packet,length);
  if(!observed.candidate)return Result::Unchanged;
  Binding b{};
  {
    std::lock_guard<std::mutex> lock(BindingMutex());
    if(!Installed())return Result::CandidateNoHost;
    b=BindingSlot();
  }
  if(!server_owned_user_context)return Result::AuthRefused;
  VerifiedIdentity identity{};
  ScopedLease lease(b); // destroyed after callback commit/abort on all paths
  try {
    const int obtained=b.acquire_exclusive(
      b.authority_context,server_owned_user_context,&observed,
      &lease.token,&identity);
    if(obtained!=0 || !lease.token ||
       !identity.authenticated_session ||
       identity.user_num!=kSyntheticUserNum ||
       identity.expected_revision==0 ||
       identity.server_catalog_grade_two_confirmed!=1 ||
       identity.server_selector_confirms_diamond!=1 ||
       identity.first_payload_dword_authoritatively_matched!=1 ||
       identity.second_payload_dword_authoritatively_matched!=1 ||
       identity.matched_first_payload_dword!=observed.mastery_id ||
       identity.matched_second_payload_dword!=observed.second_field)
       return Result::AuthRefused;
    cabal_diamond_world_result decision{};
    cabal_merit_route_result route=CABAL_MERIT_ROUTE_INVALID;
    const cabal_diamond_merit_server_proof proof{
      CABAL_DIAMOND_MERIT_PROOF_VERSION,
      1u,
      identity.server_catalog_grade_two_confirmed,
      identity.server_selector_confirms_diamond,
      identity.first_payload_dword_authoritatively_matched,
      identity.second_payload_dword_authoritatively_matched,
      identity.authenticated_session,
      identity.user_num,
      identity.expected_revision,
      identity.matched_first_payload_dword,
      identity.matched_second_payload_dword
    };
    const int status=cabal_diamond_merit_verified_shadow_route(
      b.engine,packet,length,identity.authenticated_session,
      identity.user_num,identity.expected_revision,&proof,
      &b.callbacks,b.backend_context,1u,&decision,&route);
    if(status!=0)return Result::BadEngine;
    return route==CABAL_MERIT_ROUTE_SHADOW_APPLIED ? Result::ShadowApplied :
           route==CABAL_MERIT_ROUTE_SHADOW_REJECTED ? Result::ShadowRejected :
           Result::BadEngine;
  }catch(...){return Result::BadEngine;}
}
#else
// Default archived extension builds have no DiamondNative dependency and no
// ability to mutate even synthetic shadow SQL. Deliberately unbindable.
struct Binding {std::uint32_t abi=kBindingABI;};
inline bool InstallOnce(const Binding*) noexcept {return false;}
inline Result Process(const void*,const void*,std::size_t) noexcept {
  return Result::Disabled;
}
#endif
} // namespace DiamondBoundIngress
