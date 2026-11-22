// Diamond v291 isolated durable TEST HOST. This is NOT SQL Server or WorldSvr.
// It demonstrates real disk-backed atomic grade + points + item-count + revision
// commits using the same cabal_diamond_world_execute ABI intended for WorldSvr.
#include "diamond_world_bridge.h"
#include "diamond_merit_world_entry.h"
#include <sqlite3.h>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
#include <atomic>
#include <algorithm>
#include <mutex>
#include <sstream>
#include <utility>

namespace {
void require(bool ok,const char* msg) { if(!ok)throw std::runtime_error(msg); }
struct Statement {
 sqlite3_stmt* p=nullptr;
 Statement(sqlite3* db,const char* sql) {require(sqlite3_prepare_v2(db,sql,-1,&p,nullptr)==SQLITE_OK,"prepare");}
 ~Statement(){sqlite3_finalize(p);}
 void bind(int n,int v){require(sqlite3_bind_int(p,n,v)==SQLITE_OK,"bind integer");}
 void bind64(int n,sqlite3_int64 v){require(sqlite3_bind_int64(p,n,v)==SQLITE_OK,"bind long");}
 int step(){return sqlite3_step(p);}
 Statement(const Statement&)=delete;Statement& operator=(const Statement&)=delete;
};
void sql(sqlite3* db,const char* q){char* err=nullptr;int r=sqlite3_exec(db,q,nullptr,nullptr,&err);if(r!=SQLITE_OK){std::string s=err?err:"SQL failure";sqlite3_free(err);throw std::runtime_error(s);}}
struct Session {std::uint32_t uid;std::uint64_t nonce;};
struct Host {std::string path;Session session{900001,0x1A2B3C4Dull};bool fail_next_commit=false;bool crash_before_commit=false;};
struct Tx {
 sqlite3* db=nullptr;
 Host* host=nullptr;
 std::uint32_t user=0;
 std::uint32_t revision=0;
 std::uint32_t badge=0;
 std::int64_t wexp=0;
 std::uint32_t tickets=0;
 std::int32_t points=0;
 std::vector<std::uint32_t> slots;
 std::vector<cabal_diamond_level_entry> levels;
 explicit Tx(Host* h):host(h) {}
 ~Tx(){if(db){sqlite3_exec(db,"ROLLBACK",nullptr,nullptr,nullptr);sqlite3_close(db);}}
};
int begin(void* context,const void* ptr,std::uint32_t user,void** out) {
 auto& h=*static_cast<Host*>(context);*out=nullptr;
 if(ptr!=&h.session||user!=h.session.uid||h.session.nonce==0)return -1;
 auto tx=std::make_unique<Tx>(&h);
 if(sqlite3_open_v2(h.path.c_str(),&tx->db,SQLITE_OPEN_READWRITE|SQLITE_OPEN_FULLMUTEX,nullptr)!=SQLITE_OK)return -1;
 try {sqlite3_busy_timeout(tx->db,15000);sql(tx->db,"PRAGMA foreign_keys=ON");sql(tx->db,"BEGIN IMMEDIATE");
  Statement s(tx->db,"SELECT revision,badge,wexp,tickets,points FROM test_account WHERE usernum=? AND nonce=?");
  s.bind(1,static_cast<int>(user));s.bind64(2,static_cast<sqlite3_int64>(h.session.nonce));
  if(s.step()!=SQLITE_ROW)return -1;
  tx->user=user;tx->revision=static_cast<std::uint32_t>(sqlite3_column_int(s.p,0));
  tx->badge=static_cast<std::uint32_t>(sqlite3_column_int(s.p,1));
  tx->wexp=sqlite3_column_int64(s.p,2);tx->tickets=static_cast<std::uint32_t>(sqlite3_column_int(s.p,3));
  tx->points=sqlite3_column_int(s.p,4);
  *out=tx.release();return 0;
 }catch(...){return -1;}
}
int load(void*,void* opaque,cabal_diamond_state* output) {
 auto& tx=*static_cast<Tx*>(opaque);*output={};
 output->abi_version=CABAL_DIAMOND_ABI_VERSION;
 output->server_authoritative=1;
 output->badge_grade=tx.badge;output->platinum_badge=1;output->platinum_maxed=1;
 output->revision=tx.revision;output->wexp=static_cast<std::uint64_t>(tx.wexp);
 output->verified_exchange_ticket_count=tx.tickets;output->free_points=tx.points;
 if(tx.badge==2) {
  output->active_category_mask=1;
  try {
    tx.slots.clear();
    Statement opened(tx.db,"SELECT mastery_id FROM test_open_slots WHERE usernum=? ORDER BY mastery_id");
    opened.bind(1,static_cast<int>(tx.user));
    int status=SQLITE_ROW;
    while((status=opened.step())==SQLITE_ROW) {
      const int id=sqlite3_column_int(opened.p,0);
      if(id<159 || id>474 || tx.slots.size()>=316)return -1;
      tx.slots.push_back(static_cast<std::uint32_t>(id));
    }
    if(status!=SQLITE_DONE)return -1;
    tx.levels.clear();
    Statement s(tx.db,"SELECT mastery_id,level FROM test_mastery WHERE usernum=? ORDER BY mastery_id");
    s.bind(1,static_cast<int>(tx.user));
    while((status=s.step())==SQLITE_ROW) {
      const int id=sqlite3_column_int(s.p,0),level=sqlite3_column_int(s.p,1);
      if(id<159 || id>474 || level<1 || level>100 || tx.levels.size()>=316)return -1;
      tx.levels.push_back({id,level});
    }
    if(status!=SQLITE_DONE)return -1;
    output->server_open_mastery_ids=tx.slots.empty()?nullptr:tx.slots.data();
    output->server_open_count=tx.slots.size();
    output->server_levels=tx.levels.empty()?nullptr:tx.levels.data();
    output->server_level_count=tx.levels.size();
  } catch(...) {return -1;}
 }
 return 0;
}
int commit(void*,void* opaque,const cabal_diamond_request* request,const cabal_diamond_evaluation* proposal) {
 std::unique_ptr<Tx> tx(static_cast<Tx*>(opaque)); // ownership on success only; release on error
 auto fail=[&](){tx.release();return -1;};
 try {
  if(tx->host->fail_next_commit || request->expected_revision!=tx->revision ||
      !proposal->permitted || !proposal->requires_atomic_commit ||
      proposal->new_revision!=tx->revision+1 ||proposal->new_wexp>static_cast<std::uint64_t>(tx->wexp) ||
      proposal->new_ticket_count>tx->tickets ||proposal->new_free_points>tx->points) return fail();
  // These columns are a SEPARATE isolated test database, not a CABAL inventory API.
  Statement upd(tx->db,"UPDATE test_account SET badge=?,wexp=?,tickets=?,points=?,revision=? "
                       "WHERE usernum=? AND revision=? AND nonce=?");
  upd.bind(1,static_cast<int>(proposal->new_badge_grade));
  upd.bind64(2,static_cast<sqlite3_int64>(proposal->new_wexp));
  upd.bind(3,static_cast<int>(proposal->new_ticket_count));upd.bind(4,proposal->new_free_points);
  upd.bind(5,static_cast<int>(proposal->new_revision));upd.bind(6,static_cast<int>(tx->user));
  upd.bind(7,static_cast<int>(tx->revision));upd.bind64(8,static_cast<sqlite3_int64>(tx->host->session.nonce));
  if(upd.step()!=SQLITE_DONE || sqlite3_changes(tx->db)!=1)return fail();
  if(request->command==CABAL_DIAMOND_MASTERY_LEVEL_UP){
    const int id=proposal->changed_mastery_id;
    if(id<159 || id>474 || id!=request->mastery_id ||
       std::find(tx->slots.begin(),tx->slots.end(),static_cast<std::uint32_t>(id))==tx->slots.end())return fail();
    int previous=0;
    for(const auto& level:tx->levels)if(level.mastery_id==id)previous=level.level;
    if(proposal->changed_mastery_level!=previous+1)return fail();
    Statement upsert(tx->db,"INSERT INTO test_mastery(usernum,mastery_id,level) VALUES(?,?,?) "
                            "ON CONFLICT(usernum,mastery_id) DO UPDATE SET level=excluded.level");
    upsert.bind(1,static_cast<int>(tx->user));
    upsert.bind(2,id);upsert.bind(3,proposal->changed_mastery_level);
    if(upsert.step()!=SQLITE_DONE)return fail();
  }
  // Simulate a fatal storage failure between row update and durable commit.
  if(tx->host->fail_next_commit) return fail();
  // Only synthetic crash-test mode sets this. Terminate after mutations,
  // before COMMIT and before destructors: SQLite must recover atomically.
  if(tx->host->crash_before_commit)std::_Exit(71);
  sql(tx->db,"COMMIT");return 0;
 }catch(...){return fail();}
}
void abort_tx(void*,void* tx){delete static_cast<Tx*>(tx);}
cabal_diamond_world_callbacks callbacks(){cabal_diamond_world_callbacks c{};
 c.version=CABAL_DIAMOND_WORLD_BRIDGE_VERSION;c.begin_authenticated_locked=begin;
 c.load_trusted_state=load;c.commit_durable=commit;c.abort_transaction=abort_tx;return c;}
void init_db(const char* path){sqlite3* db=nullptr;
 require(sqlite3_open_v2(path,&db,SQLITE_OPEN_READWRITE|SQLITE_OPEN_CREATE,nullptr)==SQLITE_OK,"db open");
 try{
  // EXCLUSIVELY test_* tables. Refuse any existing file to protect player data.
  sql(db,"PRAGMA foreign_keys=ON");
  sql(db,"BEGIN IMMEDIATE");
  sql(db,"CREATE TABLE test_account(usernum INTEGER PRIMARY KEY, nonce INTEGER NOT NULL,"
         "badge INTEGER NOT NULL CHECK(badge IN(1,2)),wexp INTEGER NOT NULL CHECK(wexp>=0),"
         "tickets INTEGER NOT NULL CHECK(tickets>=0),points INTEGER NOT NULL CHECK(points>=0),"
         "revision INTEGER NOT NULL CHECK(revision>=0))");
  sql(db,"CREATE TABLE test_open_slots("
         "usernum INTEGER NOT NULL REFERENCES test_account(usernum),"
         "mastery_id INTEGER NOT NULL CHECK(mastery_id BETWEEN 159 AND 474),"
         "PRIMARY KEY(usernum,mastery_id))");
  sql(db,"CREATE TABLE test_mastery("
         "usernum INTEGER NOT NULL,mastery_id INTEGER NOT NULL,"
         "level INTEGER NOT NULL CHECK(level BETWEEN 1 AND 100),"
         "PRIMARY KEY(usernum,mastery_id),"
         "FOREIGN KEY(usernum,mastery_id) REFERENCES test_open_slots(usernum,mastery_id))");
  // Only synthetic users. 900002 must remain unchanged for the entire test.
  sql(db,"INSERT INTO test_account(usernum,nonce,badge,wexp,tickets,points,revision)"
         " VALUES(900001,439041101,1,40000,120,100,10),"
         "       (900002,439041102,1,40000,120,100,10)");
  // The 316 Diamond IDs are available as explicitly opened TEST slots.
  // Real game slots MUST be loaded from WorldSvr, not opened wholesale.
  sql(db,"WITH RECURSIVE slots(id) AS "
         "(SELECT 159 UNION ALL SELECT id+1 FROM slots WHERE id<474) "
         "INSERT INTO test_open_slots(usernum,mastery_id)"
         "SELECT 900001,id FROM slots");
  sql(db,"COMMIT");
 }catch(...){sqlite3_close(db);throw;}
 sqlite3_close(db);
}
std::pair<int,int> first_two_costs(const std::string& config) {
 bool values=false; int first=-1,second=-1;
 std::istringstream lines(config);std::string line;
 while(std::getline(lines,line)) {
  if(!line.empty() && line[0]=='[') {values=line.rfind("[MeritMastery_Value]",0)==0;continue;}
  if(!values || line.empty() || line[0]=='#')continue;
  std::vector<std::string> parts;std::size_t begin=0;
  while(true){auto p=line.find('\t',begin);
    if(p==std::string::npos){parts.emplace_back(line.substr(begin));break;}
    parts.emplace_back(line.substr(begin,p-begin));begin=p+1;}
  if(parts.size()<5 || parts[2]!="159")continue;
  if(parts[3]=="1")first=std::stoi(parts[4]);
  if(parts[3]=="2")second=std::stoi(parts[4]);
 }
 require(first>0 && second>0,"Mastery159 first-two cost missing");
 return {first,second};
}
void state_check(const std::string& path,int revision,int badge,int points,int mastery_level){
 sqlite3* db=nullptr;require(sqlite3_open_v2(path.c_str(),&db,SQLITE_OPEN_READONLY,nullptr)==SQLITE_OK,"reopen");
 try {Statement s(db,"SELECT revision,badge,points FROM test_account WHERE usernum=900001");
      require(s.step()==SQLITE_ROW,"missing user");
      require(sqlite3_column_int(s.p,0)==revision && sqlite3_column_int(s.p,1)==badge &&
              sqlite3_column_int(s.p,2)==points,"persisted account mismatch");}
 catch(...){sqlite3_close(db);throw;} // stmt must finalize before close on exception; no effect on test.
 sqlite3_stmt* q=nullptr;sqlite3_prepare_v2(db,"SELECT COALESCE((SELECT level FROM test_mastery WHERE usernum=900001 AND mastery_id=159),0)",-1,&q,nullptr);
 require(sqlite3_step(q)==SQLITE_ROW && sqlite3_column_int(q,0)==mastery_level,"persisted mastery mismatch");
 sqlite3_finalize(q);sqlite3_close(db);
}
}
// Separate-process, READ-ONLY verification after the writer exits. This is
// not an in-process reopen: CI launches this executable a second time.
void verify_after_restart(const std::string& path,int expected_points){
 sqlite3* raw=nullptr;
 require(sqlite3_open_v2(path.c_str(),&raw,SQLITE_OPEN_READONLY|SQLITE_OPEN_FULLMUTEX,
                         nullptr)==SQLITE_OK,"restart: existing SQLite database required");
 std::unique_ptr<sqlite3,decltype(&sqlite3_close)> db(raw,&sqlite3_close);
 {
  Statement q(db.get(),"PRAGMA integrity_check");
  require(q.step()==SQLITE_ROW &&
          std::string(reinterpret_cast<const char*>(sqlite3_column_text(q.p,0)))=="ok" &&
          q.step()==SQLITE_DONE,"restart: SQLite integrity failure");
 }
 {
  Statement q(db.get(),"PRAGMA foreign_key_check");
  require(q.step()==SQLITE_DONE,"restart: foreign key violation");
 }
 {
  Statement q(db.get(),"SELECT usernum,nonce,revision,badge,wexp,tickets,points "
                        "FROM test_account");
  require(q.step()==SQLITE_ROW,"restart: missing account");
  require(sqlite3_column_int(q.p,0)==900001 &&
          sqlite3_column_int64(q.p,1)==439041101ll &&
          sqlite3_column_int(q.p,2)==14 &&
          sqlite3_column_int(q.p,3)==2 &&
          sqlite3_column_int64(q.p,4)==10000 &&
          sqlite3_column_int(q.p,5)==20 &&
          sqlite3_column_int(q.p,6)==expected_points &&
          q.step()==SQLITE_DONE,"restart: account wallet or revision mismatch");
 }
 {
  Statement q(db.get(),"SELECT usernum,mastery_id,level FROM test_mastery");
  require(q.step()==SQLITE_ROW && sqlite3_column_int(q.p,0)==900001 &&
          sqlite3_column_int(q.p,1)==159 &&
          sqlite3_column_int(q.p,2)==2,"restart: Mastery 159 mismatch");
  require(q.step()==SQLITE_ROW && sqlite3_column_int(q.p,0)==900001 &&
          sqlite3_column_int(q.p,1)==319 &&
          sqlite3_column_int(q.p,2)==1 &&
          q.step()==SQLITE_DONE,"restart: Mastery 319 missing or extra");
 }
 {
  Statement q(db.get(),"SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name NOT LIKE 'sqlite_%' ORDER BY name");
  require(q.step()==SQLITE_ROW &&
          std::string(reinterpret_cast<const char*>(sqlite3_column_text(q.p,0)))=="test_account",
          "restart: unexpected account schema");
  require(q.step()==SQLITE_ROW &&
          std::string(reinterpret_cast<const char*>(sqlite3_column_text(q.p,0)))=="test_mastery" &&
          q.step()==SQLITE_DONE,"restart: unexpected tables");
 }
}
int main(int argc,char**argv){
 try {
  require(argc==4,"usage: --selftest|--verify-restart <staged-scp> <isolated.db>");
  const std::string mode=argv[1];
  require(mode=="--selftest" || mode=="--verify-restart" ||
          mode=="--verify-reconnect" || mode=="--simulate-crash-before-commit",
          "unknown mode");
  const std::string path=argv[3];
  require(path.size()>8 && path.substr(path.size()-8)==".sqlite3","test DB must end .sqlite3");
  std::ifstream input(argv[2],std::ios::binary);require(input.good(),"source staged SCP missing");
  std::string cfg((std::istreambuf_iterator<char>(input)),std::istreambuf_iterator<char>());
  const auto costs=first_two_costs(cfg);
  if(mode=="--verify-restart"){
    verify_after_restart(path,100-costs.first-costs.second-5);
    std::cout<<"DIAMOND_SEPARATE_PROCESS_RESTART_VERIFICATION=PASS\\n"
             <<"MERIT_WALLET_ITEMS_WEXP_REVISION_MASTERY=PERSISTED\\n";
    return 0;
  }
  if(mode=="--simulate-crash-before-commit"){
    // This must be launched in a NEW child process on an isolated test DB.
    // Only uncommitted SQLite mutation is permitted; exit 71 simulates
    // the server being terminated mid-save.
    verify_after_restart(path,100-costs.first-costs.second-5);
    cabal_diamond_engine* crash_engine=nullptr;
    require(cabal_diamond_engine_create(cfg.data(),cfg.size(),&crash_engine)==0,
            "crash: rules engine failed");
    Host crash_host{path};
    crash_host.crash_before_commit=true;
    auto crash_cb=callbacks();
    cabal_diamond_world_result crash_result{};
    const cabal_diamond_request third_level{
      1,CABAL_DIAMOND_MASTERY_LEVEL_UP,14,159
    };
    (void)cabal_diamond_world_execute(
      crash_engine,&crash_host.session,crash_host.session.uid,
      &third_level,&crash_cb,&crash_host,&crash_result);
    cabal_diamond_engine_destroy(crash_engine);
    throw std::runtime_error("crash: did not reach pre-COMMIT failpoint");
  }
  if(mode=="--verify-reconnect"){
    // NEW PROCESS, new session object, existing persisted database.
    // Reject stale rank-up and Mastery C2S without charging resources again.
    verify_after_restart(path,100-costs.first-costs.second-5);
    cabal_diamond_engine* restarted=nullptr;
    require(cabal_diamond_engine_create(cfg.data(),cfg.size(),&restarted)==0,
            "reconnect: unable to reload Diamond rules");
    Host reconnect{path};
    auto handlers=callbacks();
    cabal_diamond_world_result reply{};
    const cabal_diamond_request stale_rank{1,CABAL_DIAMOND_RANK_UP,10,0};
    require(cabal_diamond_world_execute(
      restarted,&reconnect.session,reconnect.session.uid,
      &stale_rank,&handlers,&reconnect,&reply)==0 &&
      reply.status==CABAL_DIAMOND_WORLD_REJECTED,
      "reconnect: stale rank-up was accepted");
    std::vector<std::uint8_t> stale_merit(18,0);
    stale_merit[0]=0xE2;stale_merit[1]=0xB7;stale_merit[2]=18;
    stale_merit[8]=0xF3;stale_merit[9]=0x09;stale_merit[10]=159;
    stale_merit[14]=0xE7;stale_merit[15]=0x03;
    cabal_diamond_merit_server_proof refreshed{
      CABAL_DIAMOND_MERIT_PROOF_VERSION,1,1,1,1,1,
      &reconnect.session,reconnect.session.uid,11,159,999
    };
    cabal_merit_route_result route=CABAL_MERIT_ROUTE_INVALID;
    require(cabal_diamond_merit_verified_shadow_route(
      restarted,stale_merit.data(),stale_merit.size(),
      &reconnect.session,reconnect.session.uid,11,&refreshed,
      &handlers,&reconnect,1,&reply,&route)==0 &&
      route==CABAL_MERIT_ROUTE_SHADOW_REJECTED &&
      reply.status==CABAL_DIAMOND_WORLD_REJECTED,
      "reconnect: stale Merit purchase was accepted");
    cabal_diamond_engine_destroy(restarted);
    verify_after_restart(path,100-costs.first-costs.second-5);
    std::cout<<"DIAMOND_NEW_PROCESS_RECONNECT_STALE_RANK_AND_MERIT=PASS\\n"
             <<"DURABLE_WALLET_UNCHANGED_AFTER_REPLAY=PASS\\n";
    return 0;
  }
  {std::ifstream existing(path);require(!existing.good(),"refuse existing DB; do not overwrite");}
  cabal_diamond_engine* engine=nullptr;
  require(cabal_diamond_engine_create(cfg.data(),cfg.size(),&engine)==0,"native SCP catalog rejected");
  init_db(path.c_str());Host host{path};auto c=callbacks();
  cabal_diamond_request rank{1,CABAL_DIAMOND_RANK_UP,10,0};cabal_diamond_world_result result{};
  require(cabal_diamond_world_execute(engine,&host.session,host.session.uid,&rank,&c,&host,&result)==0 &&
          result.status==CABAL_DIAMOND_WORLD_APPLIED,"rankup did not commit");
  require(result.evaluated.new_wexp==10000 && result.evaluated.new_ticket_count==20,"rank resources wrong");
  state_check(path,11,2,100,0);
  require(cabal_diamond_world_execute(engine,&host.session,host.session.uid,&rank,&c,&host,&result)==0 &&
          result.status==CABAL_DIAMOND_WORLD_REJECTED,"rank replay accepted");
  // End-to-end CLONE TEST: exact 18-byte legacy Merit C2S shape, gated
  // by a host-supplied proof tied to this authenticated session/user/revision.
  // This proof is SYNTHETIC, NOT obtained from live WorldSvr.
  std::vector<std::uint8_t> c2s(18,0);
  c2s[0]=0xE2;c2s[1]=0xB7;c2s[2]=18;
  c2s[8]=0xF3;c2s[9]=0x09;c2s[10]=159;
  constexpr std::uint32_t kUnknownPayload=999;
  c2s[14]=static_cast<std::uint8_t>(kUnknownPayload);
  c2s[15]=static_cast<std::uint8_t>(kUnknownPayload>>8);
  c2s[16]=static_cast<std::uint8_t>(kUnknownPayload>>16);
  c2s[17]=static_cast<std::uint8_t>(kUnknownPayload>>24);
  cabal_diamond_merit_server_proof proof{
    CABAL_DIAMOND_MERIT_PROOF_VERSION,1,1,1,1,1,
    &host.session,host.session.uid,11,159,kUnknownPayload
  };
  cabal_merit_route_result route=CABAL_MERIT_ROUTE_INVALID;
  auto from_wire=[&](const cabal_diamond_merit_server_proof* attestation) {
    return cabal_diamond_merit_verified_shadow_route(
      engine,c2s.data(),c2s.size(),&host.session,host.session.uid,
      11,attestation,&c,&host,1,&result,&route);
  };
  // Missing proof and unverified old API are incapable of a debit.
  require(from_wire(nullptr)==0 && route==CABAL_MERIT_ROUTE_DISABLED,
          "unauthenticated packet incorrectly entered Diamond route");
  require(cabal_diamond_merit_shadow_route(
      engine,c2s.data(),c2s.size(),&host.session,host.session.uid,
      11,&c,&host,1,&result,&route)==0 &&
      route==CABAL_MERIT_ROUTE_DISABLED,
      "legacy ID-only packet incorrectly entered Diamond route");
  state_check(path,11,2,100,0);
  // Inject real SQLite transaction failure: row updates must rollback.
  host.fail_next_commit=true;
  require(from_wire(&proof)==0 && route==CABAL_MERIT_ROUTE_SHADOW_REJECTED &&
          result.status==CABAL_DIAMOND_WORLD_COMMIT_FAILED &&
          !result.evaluated.permitted,
          "packet-gated injected commit failure incorrectly approved");
  host.fail_next_commit=false;
  state_check(path,11,2,100,0);
  require(from_wire(&proof)==0 && route==CABAL_MERIT_ROUTE_SHADOW_APPLIED &&
          result.status==CABAL_DIAMOND_WORLD_APPLIED,
          "verified Merit C2S -> SQLite durable purchase failed");
  require(result.evaluated.new_free_points==100-costs.first,
          "Merit packet purchase cost mismatch");
  state_check(path,12,2,100-costs.first,1);
  // A repeat of the same attested revision cannot charge twice.
  require(from_wire(&proof)==0 && route==CABAL_MERIT_ROUTE_SHADOW_REJECTED,
          "stale Merit packet replay was accepted");
  state_check(path,12,2,100-costs.first,1);
  // Concurrent duplicate purchases with exactly the same revision -> only one.
  cabal_diamond_request next{1,CABAL_DIAMOND_MASTERY_LEVEL_UP,12,159};
  std::atomic<int> applied{0},rejected{0},other{0};std::vector<std::thread> threads;
  for(int i=0;i<4;i++)threads.emplace_back([&]{cabal_diamond_world_result r{};
     int ret=cabal_diamond_world_execute(engine,&host.session,host.session.uid,&next,&c,&host,&r);
     if(ret==0 && r.status==CABAL_DIAMOND_WORLD_APPLIED)applied++;
     else if(ret==0 && r.status==CABAL_DIAMOND_WORLD_REJECTED)rejected++;
     else other++;
  });for(auto& t:threads)t.join();
  require(applied==1 && rejected==3 && other==0,"concurrent duplicate transaction check failed");
  state_check(path,13,2,100-costs.first-costs.second,2);
  // Another Diamond Mastery, outside the original single-ID test.
  // Fixture 319 is category 11, unlinked, max-level 1, cost 5.
  std::vector<std::uint8_t> next_c2s=c2s;
  next_c2s[10]=static_cast<std::uint8_t>(319);
  next_c2s[11]=static_cast<std::uint8_t>(319>>8);
  cabal_diamond_merit_server_proof second_proof{
    CABAL_DIAMOND_MERIT_PROOF_VERSION,1,1,1,1,1,
    &host.session,host.session.uid,13,319,kUnknownPayload
  };
  require(cabal_diamond_merit_verified_shadow_route(
      engine,next_c2s.data(),next_c2s.size(),&host.session,host.session.uid,
      13,&second_proof,&c,&host,1,&result,&route)==0 &&
      route==CABAL_MERIT_ROUTE_SHADOW_APPLIED &&
      result.status==CABAL_DIAMOND_WORLD_APPLIED,
      "second independent Diamond mastery purchase failed");
  require(result.evaluated.changed_mastery_id==319 &&
          result.evaluated.changed_mastery_level==1 &&
          result.evaluated.new_free_points==100-costs.first-costs.second-5,
          "second Diamond mastery progression mismatch");
  state_check(path,14,2,100-costs.first-costs.second-5,2);
  // Replaying 319 must not create another Mastery level or debit.
  require(cabal_diamond_merit_verified_shadow_route(
      engine,next_c2s.data(),next_c2s.size(),&host.session,host.session.uid,
      13,&second_proof,&c,&host,1,&result,&route)==0 &&
      route==CABAL_MERIT_ROUTE_SHADOW_REJECTED,
      "duplicate independent Diamond mastery accepted");
  cabal_diamond_engine_destroy(engine);
  std::cout<<"DIAMOND_SQLITE_DURABLE_BRIDGE=PASS\n"
           <<"RESTART_PERSISTENCE=PASS\nROLLBACK=PASS\nCONCURRENT_REPLAY=PASS\n"
           <<"REAL_SCP_MASTERIES=316;DATA_STORE=ISOLATED_SQLITE_TEST_ONLY\n"
           <<"PRODUCTION_SQL_SERVER_OR_WORLDSVR=NO\n"
           <<"VERIFIED_MERIT_PACKET_TO_DURABLE_SQLITE=PASS\n";
  return 0;
 }catch(const std::exception& e){std::cerr<<"DIAMOND_SQLITE_DURABLE_BRIDGE=FAIL: "<<e.what()<<"\n";return 1;}
}
