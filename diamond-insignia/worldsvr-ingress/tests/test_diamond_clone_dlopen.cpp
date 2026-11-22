#include "../DiamondBoundIngress.h"
#include "../../native/test_diamond_fixture.hpp"
#include <cassert>
#include <cstdlib>
#include <cstdint>
#include <iostream>
#include <dlfcn.h>
#include <string>
#include <vector>
using namespace DiamondBoundIngress;
struct UserContext {int secret=4567;};
struct Store {
 UserContext user;
 int session=88;
 std::uint32_t revision=10,slot=159;
 int points=50,level=0,commits=0,aborts=0;
 bool fail=false;
 cabal_diamond_level_entry row{159,0};
};
struct Tx {Store* store;};
int begin(void* host,const void* session,std::uint32_t user,void** out) {
 auto& h=*static_cast<Store*>(host);*out=nullptr;
 if(session!=&h.session || user!=kSyntheticUserNum)return -1;
 *out=new Tx{&h};return 0;
}
int load(void*,void* token,cabal_diamond_state* s) {
 auto& h=*static_cast<Tx*>(token)->store;
 *s={};s->abi_version=1;s->server_authoritative=1;
 s->badge_grade=2;s->platinum_badge=1;s->platinum_maxed=1;
 s->revision=h.revision;s->free_points=h.points;
 s->active_category_mask=1;s->server_open_mastery_ids=&h.slot;s->server_open_count=1;
 if(h.level){h.row.level=h.level;s->server_levels=&h.row;s->server_level_count=1;}
 return 0;
}
int commit(void*,void* token,const cabal_diamond_request* request,
           const cabal_diamond_evaluation* proposal) {
 auto* tx=static_cast<Tx*>(token);auto& h=*tx->store;
 if(h.fail || !proposal->permitted || request->expected_revision!=h.revision ||
    proposal->new_revision!=h.revision+1 || proposal->changed_mastery_id!=159 ||
    proposal->changed_mastery_level!=h.level+1)return -1;
 h.revision=proposal->new_revision;h.points=proposal->new_free_points;
 h.level=proposal->changed_mastery_level;++h.commits;delete tx;return 0;
}
void abort_tx(void*,void* token){auto* tx=static_cast<Tx*>(token);++tx->store->aborts;delete tx;}
int resolve(void* host,const void* user_context,
            const DiamondIngress::Observation* observed,VerifiedIdentity* id){
 auto& h=*static_cast<Store*>(host);
 if(!observed || user_context!=&h.user || h.user.secret!=4567)return -1;
 // Synthetic host only: explicitly match BOTH legacy payload fields. This
 // deliberately does not constitute evidence of the real game's ABI.
 if(observed->mastery_id!=159 || observed->second_field!=999)return -1;
 id->authenticated_session=&h.session;id->user_num=kSyntheticUserNum;
 id->expected_revision=h.revision;
 id->server_catalog_grade_two_confirmed=1;
 id->server_selector_confirms_diamond=1;
 id->first_payload_dword_authoritatively_matched=1;
 id->second_payload_dword_authoritatively_matched=1;
 id->matched_first_payload_dword=159;
 id->matched_second_payload_dword=999;
 return 0;
}
std::vector<std::uint8_t> packet(unsigned opcode,unsigned mastery){
 std::vector<std::uint8_t> p(18,0);
 p[0]=0xe2;p[1]=0xb7;p[2]=18;p[8]=static_cast<std::uint8_t>(opcode);
 p[9]=static_cast<std::uint8_t>(opcode>>8);
 for(unsigned j=0;j<4;++j)p[10+j]=static_cast<std::uint8_t>(mastery>>(j*8));
 p[14]=0xE7;p[15]=0x03; // synthetic second DWORD=999
 return p;
}
int main(int argc,char**argv){
 assert(argc==2);
 void* handle=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
 if(!handle) {std::cerr<<"DIAMOND_OFFLINE_DLOPEN_ERROR="<<dlerror()<<"\n";return 1;}
 using Binder=int (*)(const Binding*);
 using Handler=int (*)(const void*,const void*,std::size_t);
 auto bind=reinterpret_cast<Binder>(dlsym(handle,"cabal_diamond_proc_bind_shadow_clone_v2"));
 auto invoke=reinterpret_cast<Handler>(dlsym(handle,"cabal_diamond_proc_test_ingress_clone_v2"));
 assert(bind && invoke && !dlsym(handle,"cabal_diamond_proc_bind_shadow_clone_v1"));

 const std::string scp=fixture();cabal_diamond_engine* engine=nullptr;
 assert(cabal_diamond_engine_create(scp.data(),scp.size(),&engine)==0);
 Store h;auto diamond=packet(0x09f3,159),gold=packet(0x09f3,158),platinum=packet(0x0b10,159);
 assert(invoke(&h.user,diamond.data(),diamond.size())==Result::Disabled);
 setenv("CABAL_DIAMOND_SHADOW_TRIAL","ISOLATED_SYNTHETIC_USER_900001_ONLY",1);
 Binding binding{};binding.engine=engine;binding.backend_context=&h;
 binding.resolve=resolve;binding.resolver_context=&h;
 binding.callbacks.version=1;binding.callbacks.begin_authenticated_locked=begin;
 binding.callbacks.load_trusted_state=load;binding.callbacks.commit_durable=commit;
 binding.callbacks.abort_transaction=abort_tx;
 Binding oldAbi=binding;oldAbi.abi=1; // prior unsafe resolver signature
 assert(!bind(&oldAbi));
 assert(bind(&binding));assert(!bind(&binding));
 assert(invoke(&h.user,gold.data(),gold.size())==Result::Unchanged);
 assert(invoke(&h.user,platinum.data(),platinum.size())==Result::Unchanged);
 UserContext attacker;assert(invoke(&attacker,diamond.data(),diamond.size())==Result::AuthRefused);
 auto changedSecond=diamond;changedSecond[14]^=1;
 assert(invoke(&h.user,changedSecond.data(),changedSecond.size())==Result::AuthRefused);
 auto changedFirst=packet(0x09f3,319);
 assert(invoke(&h.user,changedFirst.data(),changedFirst.size())==Result::AuthRefused);
 assert(h.commits==0);
 assert(invoke(&h.user,diamond.data(),diamond.size())==Result::ShadowApplied);
 assert(h.level==1 && h.points==45 && h.revision==11 && h.commits==1);
 h.fail=true;
 assert(invoke(&h.user,diamond.data(),diamond.size())==Result::ShadowRejected);
 assert(h.level==1 && h.points==45 && h.revision==11 && h.commits==1 && h.aborts>0);
 h.fail=false;
 assert(invoke(&h.user,diamond.data(),diamond.size())==Result::ShadowApplied);
 assert(h.level==2 && h.points==35 && h.revision==12 && h.commits==2);
 unsetenv("CABAL_DIAMOND_SHADOW_TRIAL");
 assert(invoke(&h.user,diamond.data(),diamond.size())==Result::Disabled);
 cabal_diamond_engine_destroy(engine);
 dlclose(handle);
 std::cout<<"DIAMOND_LINKED_OFFLINE_CLONE_DLOPEN=PASS\n"
          <<"TRUSTED_SESSION_RESOLVER_REQUIRED=PASS\n"
          <<"GOLD_PLATINUM_PASS_THROUGH=PASS\n"
          <<"PRODUCTION_GAME_OR_DB_ACCESSED=NO\n";
}
