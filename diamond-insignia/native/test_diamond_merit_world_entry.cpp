#include "diamond_merit_world_entry.h"
#include "test_diamond_fixture.hpp"
#include <cassert>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>
namespace {
void u16(std::vector<uint8_t>& a,unsigned i,uint16_t v){a[i]=static_cast<uint8_t>(v);a[i+1]=static_cast<uint8_t>(v>>8);}
void u32(std::vector<uint8_t>& a,unsigned i,uint32_t v){for(unsigned j=0;j<4;j++)a[i+j]=static_cast<uint8_t>(v>>(j*8));}
std::vector<uint8_t> packet(unsigned cmd,uint32_t id){
 std::vector<uint8_t> p(18,0);
 u16(p,0,0xB7E2);u16(p,2,18);u16(p,8,static_cast<uint16_t>(cmd));u32(p,10,id);u32(p,14,999);
 return p;
}
struct Fake {
 int session_token=314;
 uint32_t user=70,revision=3,slot=159;
 int points=100,level=0,commits=0,aborts=0;
 bool fail=false;
 cabal_diamond_level_entry row{159,0};
};
struct Tx{Fake* store;};
int begin(void* ctx,const void* session,uint32_t user,void** out){
 auto& f=*static_cast<Fake*>(ctx);*out=nullptr;
 if(session!=&f.session_token||user!=f.user)return -1;
 *out=new Tx{&f};return 0;
}
int load(void*,void* opaque,cabal_diamond_state* out){
 auto& f=*static_cast<Tx*>(opaque)->store;
 *out={};out->abi_version=1;out->server_authoritative=1;out->badge_grade=2;
 out->revision=f.revision;out->platinum_badge=1;out->platinum_maxed=1;
 out->free_points=f.points;out->active_category_mask=1;
 out->server_open_mastery_ids=&f.slot;out->server_open_count=1;
 if(f.level>0){f.row.level=f.level;out->server_levels=&f.row;out->server_level_count=1;}
 return 0;
}
int commit(void*,void* opaque,const cabal_diamond_request* command,
           const cabal_diamond_evaluation* e){
 auto* tx=static_cast<Tx*>(opaque);auto& f=*tx->store;
 if(f.fail||command->expected_revision!=f.revision||e->new_revision!=f.revision+1||
    e->changed_mastery_id!=159 || e->changed_mastery_level!=f.level+1 ||
    !e->permitted)return -1;
 f.revision=e->new_revision;f.points=e->new_free_points;
 f.level=e->changed_mastery_level;++f.commits;
 delete tx;return 0;
}
void abort_tx(void*,void* opaque){auto* tx=static_cast<Tx*>(opaque);++tx->store->aborts;delete tx;}
}
int main(){
 const std::string source=fixture();
 cabal_diamond_engine* engine=nullptr;
 assert(cabal_diamond_engine_create(source.data(),source.size(),&engine)==0);
 cabal_merit_packet_view view{};
 auto legacy=packet(0x9f3,158),diamond=packet(0x9f3,159),
      last=packet(0x9f3,474),platinum=packet(0xb10,159);
 assert(cabal_diamond_merit_classify_c2s(legacy.data(),legacy.size(),&view)==0);
 assert(view.kind==CABAL_MERIT_PACKET_ORIGINAL);
 assert(cabal_diamond_merit_classify_c2s(diamond.data(),diamond.size(),&view)==0);
 assert(view.kind==CABAL_MERIT_PACKET_DIAMOND_CANDIDATE &&
        view.unknown_field_at_0x0e==999);
 assert(cabal_diamond_merit_classify_c2s(last.data(),last.size(),&view)==0);
 assert(view.kind==CABAL_MERIT_PACKET_DIAMOND_CANDIDATE);
 assert(cabal_diamond_merit_classify_c2s(platinum.data(),platinum.size(),&view)==0);
 assert(view.kind==CABAL_MERIT_PACKET_ORIGINAL);
 auto malformed=diamond;u16(malformed,2,17);
 assert(cabal_diamond_merit_classify_c2s(malformed.data(),malformed.size(),&view)==0);
 assert(view.kind==CABAL_MERIT_PACKET_INVALID);
 Fake f;
 cabal_diamond_world_callbacks cb{};cb.version=1;
 cb.begin_authenticated_locked=begin;cb.load_trusted_state=load;
 cb.commit_durable=commit;cb.abort_transaction=abort_tx;
 cabal_merit_route_result route{};cabal_diamond_world_result world{};
 cabal_diamond_merit_server_proof proof{
   CABAL_DIAMOND_MERIT_PROOF_VERSION,1,1,1,1,1
 };
 auto run=[&](const std::vector<uint8_t>& bytes,uint32_t rev,uint32_t enable) {
  return cabal_diamond_merit_verified_shadow_route(
    engine,bytes.data(),bytes.size(),&f.session_token,f.user,rev,
    &proof,&cb,&f,enable,&world,&route);
 };
 // The old unverified ABI never routes by ID alone, even in trial builds.
 assert(cabal_diamond_merit_shadow_route(engine,diamond.data(),diamond.size(),
   &f.session_token,f.user,3,&cb,&f,1,&world,&route)==0);
 assert(route==CABAL_MERIT_ROUTE_DISABLED && f.commits==0);
 for(unsigned i=1;i<=5;i++){
   auto changed=proof;
   (&changed.authenticated_session)[i-1]=0;
   assert(cabal_diamond_merit_verified_shadow_route(
     engine,diamond.data(),diamond.size(),&f.session_token,f.user,3,
     &changed,&cb,&f,1,&world,&route)==0);
   assert(route==CABAL_MERIT_ROUTE_DISABLED && f.commits==0);
 }
 assert(cabal_diamond_merit_verified_shadow_route(
   engine,diamond.data(),diamond.size(),&f.session_token,f.user,3,
   nullptr,&cb,&f,1,&world,&route)==0);
 assert(route==CABAL_MERIT_ROUTE_DISABLED && f.commits==0);
 auto wrongVersion=proof;
 wrongVersion.version=0;
 assert(cabal_diamond_merit_verified_shadow_route(
   engine,diamond.data(),diamond.size(),&f.session_token,f.user,3,
   &wrongVersion,&cb,&f,1,&world,&route)==0);
 assert(route==CABAL_MERIT_ROUTE_DISABLED && f.commits==0);
 assert(run(diamond,3,0)==0 && route==CABAL_MERIT_ROUTE_DISABLED);
 assert(run(legacy,3,1)==0 && route==CABAL_MERIT_ROUTE_ORIGINAL);
 assert(run(platinum,3,1)==0 && route==CABAL_MERIT_ROUTE_ORIGINAL);
 assert(f.commits==0);
 assert(run(diamond,3,1)==0 && route==CABAL_MERIT_ROUTE_SHADOW_APPLIED);
 assert(f.commits==1 && f.level==1 && f.revision==4 && f.points==95);
 assert(run(diamond,3,1)==0 && route==CABAL_MERIT_ROUTE_SHADOW_REJECTED);
 assert(f.commits==1);
 f.fail=true;
 assert(run(diamond,4,1)==0 && route==CABAL_MERIT_ROUTE_SHADOW_REJECTED);
 assert(world.evaluated.permitted==0 && f.commits==1);
 f.fail=false;
 assert(run(diamond,4,1)==0 && route==CABAL_MERIT_ROUTE_SHADOW_APPLIED);
 assert(f.commits==2 && f.level==2 && f.revision==5 && f.points==85);
 cabal_diamond_engine_destroy(engine);
 std::cout<<"DIAMOND_MERIT_C2S_TO_NATIVE_SHADOW=PASS\n"
          <<"PLATINUM_LEGACY_ROUTE_PRESERVED=PASS\n"\n          <<"UNVERIFIED_09F3_CANNOT_DEBIT=PASS\n";
}