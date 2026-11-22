// Real ODBC SQL Server transactions, but only on Server01_DiamondLab shadows.
// NOT a CABAL inventory backend. NO network listener, game hook or packet parser.
#include "diamond_mssql_shadow_bridge.h"
#include <sql.h>
#include <sqlext.h>
#include <algorithm>
#include <cstdint>
#include <cstring>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
constexpr const char* kSafeDatabase="Server01_DiamondLab";
struct CheckError:std::runtime_error{using std::runtime_error::runtime_error;};
void insist(bool v){if(!v)throw CheckError("odbc-failed");}
struct Query {
 SQLHSTMT h=SQL_NULL_HSTMT;
 explicit Query(SQLHDBC db){
  insist(SQL_SUCCEEDED(SQLAllocHandle(SQL_HANDLE_STMT,db,&h)));
 }
 Query(const Query&)=delete;Query& operator=(const Query&)=delete;
 ~Query(){if(h!=SQL_NULL_HSTMT)SQLFreeHandle(SQL_HANDLE_STMT,h);}
 void run(const std::string& sql) {
  insist(SQL_SUCCEEDED(SQLExecDirectA(h,
    reinterpret_cast<SQLCHAR*>(const_cast<char*>(sql.c_str())),SQL_NTS)));
 }
 bool next(){const SQLRETURN code=SQLFetch(h);if(code==SQL_NO_DATA)return false;
   insist(SQL_SUCCEEDED(code));return true;}
 std::int64_t number(SQLUSMALLINT column) {
  SQLBIGINT v=0;SQLLEN ind=0;
  insist(SQL_SUCCEEDED(SQLGetData(h,column,SQL_C_SBIGINT,&v,sizeof(v),&ind)));
  insist(ind!=SQL_NULL_DATA);return static_cast<std::int64_t>(v);
 }
 std::string text(SQLUSMALLINT column) {
  char buf[256]{};SQLLEN ind=0;
  insist(SQL_SUCCEEDED(SQLGetData(h,column,SQL_C_CHAR,buf,sizeof(buf),&ind)));
  insist(ind!=SQL_NULL_DATA && ind>=0 && ind<static_cast<SQLLEN>(sizeof(buf)));
  return std::string(buf);
 }
 void updated_one(){
  SQLLEN n=0;insist(SQL_SUCCEEDED(SQLRowCount(h,&n)) && n==1);
 }
};
struct Transaction {
 SQLHENV env=SQL_NULL_HENV;
 SQLHDBC db=SQL_NULL_HDBC;
 bool in_transaction=false;
 std::int64_t nonce=0;
 std::uint32_t user=0,revision=0,grade=0,tickets=0,platinum_badge=0,platinum_maxed=0;
 std::int64_t wexp=0;
 std::int32_t points=0;
 std::uint32_t active_categories=0;
 std::vector<uint32_t> open_slots;
 std::vector<cabal_diamond_level_entry> levels;
 Transaction()=default;
 Transaction(const Transaction&)=delete;Transaction& operator=(const Transaction&)=delete;
 ~Transaction(){
  if(db!=SQL_NULL_HDBC){
   if(in_transaction)SQLEndTran(SQL_HANDLE_DBC,db,SQL_ROLLBACK);
   SQLDisconnect(db);SQLFreeHandle(SQL_HANDLE_DBC,db);
  }
  if(env!=SQL_NULL_HENV)SQLFreeHandle(SQL_HANDLE_ENV,env);
 }
 void connect(const char* connection) {
  insist(SQL_SUCCEEDED(SQLAllocHandle(SQL_HANDLE_ENV,SQL_NULL_HANDLE,&env)));
  insist(SQL_SUCCEEDED(SQLSetEnvAttr(env,SQL_ATTR_ODBC_VERSION,
     reinterpret_cast<SQLPOINTER>(SQL_OV_ODBC3),0)));
  insist(SQL_SUCCEEDED(SQLAllocHandle(SQL_HANDLE_DBC,env,&db)));
  // This connection string must be set by the host, NEVER from a client packet.
  insist(connection && std::strlen(connection)<4096);
  insist(SQL_SUCCEEDED(SQLSetConnectAttr(db,SQL_LOGIN_TIMEOUT,
     reinterpret_cast<SQLPOINTER>(5),0)));
  insist(SQL_SUCCEEDED(SQLDriverConnectA(db,nullptr,
    reinterpret_cast<SQLCHAR*>(const_cast<char*>(connection)),SQL_NTS,
    nullptr,0,nullptr,SQL_DRIVER_NOPROMPT)));
  // Critical: connection's active DB may differ from configured DSN.
  // Query only DB_NAME(); no transaction or write until exact safe match.
  {
   Query q(db);q.run("SELECT DB_NAME()");
   insist(q.next() && q.text(1)==kSafeDatabase && !q.next());
  }
  insist(SQL_SUCCEEDED(SQLSetConnectAttr(db,SQL_ATTR_TXN_ISOLATION,
    reinterpret_cast<SQLPOINTER>(SQL_TXN_SERIALIZABLE),0)));
  insist(SQL_SUCCEEDED(SQLSetConnectAttr(db,SQL_ATTR_AUTOCOMMIT,
    reinterpret_cast<SQLPOINTER>(SQL_AUTOCOMMIT_OFF),0)));
  in_transaction=true;
  {Query q(db);q.run("SET LOCK_TIMEOUT 5000");}
 }
 void account_load(std::uint32_t user_id,std::int64_t nonce_id) {
  // UPDLOCK,HOLDLOCK preserves this snapshot against a same-user transaction.
  Query q(db);
  q.run("SELECT UserNum,SessionNonce,PlatinumBadge,PlatinumMaxed,BadgeGrade,"
        "WExp,MedalItemCount,FreePoints,ActiveCategoryMask,RowRevision "
        "FROM dbo.cabal_diamond_bridge_wallet_v2 WITH (UPDLOCK,HOLDLOCK) WHERE UserNum="
        +std::to_string(user_id)+" AND SessionNonce="+std::to_string(nonce_id));
  insist(q.next());
  user=static_cast<std::uint32_t>(q.number(1));
  nonce=q.number(2);
  platinum_badge=static_cast<std::uint32_t>(q.number(3));
  platinum_maxed=static_cast<std::uint32_t>(q.number(4));
  grade=static_cast<std::uint32_t>(q.number(5));
  wexp=q.number(6);
  tickets=static_cast<std::uint32_t>(q.number(7));
  points=static_cast<std::int32_t>(q.number(8));
  active_categories=static_cast<std::uint32_t>(q.number(9));
  revision=static_cast<std::uint32_t>(q.number(10));
  insist(!q.next() && user==user_id && nonce==nonce_id &&
         revision<static_cast<uint32_t>(std::numeric_limits<int32_t>::max()) &&
         (grade==1||grade==2) && (platinum_badge<=1) && (platinum_maxed<=1) &&
         wexp>=0 && tickets<=static_cast<uint32_t>(std::numeric_limits<int32_t>::max()) &&
         points>=0 && (active_categories&0xffff0000u)==0);
 }
 void load_children(){
  {Query q(db);
   q.run("SELECT MasteryID FROM dbo.cabal_diamond_bridge_slot_v2 "
         "WITH (UPDLOCK,HOLDLOCK) WHERE UserNum="+std::to_string(user)+" ORDER BY MasteryID");
   while(q.next()){
     const auto id=q.number(1);
     insist(id>=159 && id<=474 && open_slots.size()<316);
     open_slots.push_back(static_cast<std::uint32_t>(id));
   }}
  {Query q(db);
   q.run("SELECT MasteryID,MasteryLevel FROM dbo.cabal_diamond_bridge_mastery_v2 "
         "WITH (UPDLOCK,HOLDLOCK) WHERE UserNum="+std::to_string(user)+" ORDER BY MasteryID");
   while(q.next()){
     const auto id=q.number(1),level=q.number(2);
     insist(id>=159 && id<=474 && level>=1 && level<=100 && levels.size()<316);
     levels.push_back({static_cast<int32_t>(id),static_cast<int32_t>(level)});
   }}
 }
 int previous_level(int id) const {
  for(const auto& p:levels)if(p.mastery_id==id)return p.level;
  return 0;
 }
 void guarded_commit(const cabal_diamond_request& cmd,const cabal_diamond_evaluation& e){
  insist(cmd.expected_revision==revision &&
         revision<static_cast<uint32_t>(std::numeric_limits<int32_t>::max()) &&
         e.permitted==1 && e.requires_atomic_commit==1 &&
         e.abi_version==CABAL_DIAMOND_ABI_VERSION && e.new_revision==revision+1 &&
         e.new_ticket_count<=tickets && e.new_wexp<=static_cast<uint64_t>(wexp) &&
         e.new_free_points>=0 && e.new_free_points<=points);
  if(cmd.command==CABAL_DIAMOND_RANK_UP){
   insist(grade==1 && platinum_badge==1 && platinum_maxed==1 &&
          e.new_badge_grade==2 &&
          static_cast<uint64_t>(wexp)-e.new_wexp==30000 &&
          tickets-e.new_ticket_count==100 &&
          e.new_free_points==points &&
          e.changed_mastery_id==0);
  } else if(cmd.command==CABAL_DIAMOND_MASTERY_LEVEL_UP) {
   insist(grade==2 && e.new_badge_grade==2 && e.new_wexp==static_cast<uint64_t>(wexp) &&
          e.new_ticket_count==tickets &&
          e.changed_mastery_id==cmd.mastery_id &&
          cmd.mastery_id>=159 && cmd.mastery_id<=474 &&
          e.changed_mastery_level==previous_level(cmd.mastery_id)+1);
  }else throw CheckError("not authorized");
  // Only shadow tables. Account and mastery rows remain in same serializable transaction.
  {
   Query q(db);
   q.run("UPDATE dbo.cabal_diamond_bridge_wallet_v2 SET "
     "BadgeGrade="+std::to_string(e.new_badge_grade)+
     ",WExp="+std::to_string(e.new_wexp)+
     ",MedalItemCount="+std::to_string(e.new_ticket_count)+
     ",FreePoints="+std::to_string(e.new_free_points)+
     ",RowRevision="+std::to_string(e.new_revision)+
     " WHERE UserNum="+std::to_string(user)+
     " AND SessionNonce="+std::to_string(nonce)+
     " AND RowRevision="+std::to_string(revision)+
     " AND BadgeGrade="+std::to_string(grade)+
     " AND WExp="+std::to_string(wexp)+
     " AND MedalItemCount="+std::to_string(tickets)+
     " AND FreePoints="+std::to_string(points));
   q.updated_one();
  }
  if(cmd.command==CABAL_DIAMOND_MASTERY_LEVEL_UP){
   const auto id=cmd.mastery_id;
   const int prev=previous_level(id);
   Query q(db);
   if(prev==0){
    q.run("INSERT INTO dbo.cabal_diamond_bridge_mastery_v2(UserNum,MasteryID,MasteryLevel) "
      "VALUES("+std::to_string(user)+","+std::to_string(id)+","+
      std::to_string(e.changed_mastery_level)+")");
   }else{
    q.run("UPDATE dbo.cabal_diamond_bridge_mastery_v2 SET MasteryLevel="+
      std::to_string(e.changed_mastery_level)+" WHERE UserNum="+std::to_string(user)+
      " AND MasteryID="+std::to_string(id)+
      " AND MasteryLevel="+std::to_string(prev));
   }
   q.updated_one();
  }
  insist(SQL_SUCCEEDED(SQLEndTran(SQL_HANDLE_DBC,db,SQL_COMMIT)));
  in_transaction=false;
 }
};
int begin(void* context,const void* session,std::uint32_t user,void** out) {
 if(!out)return -1;*out=nullptr;
 auto* c=static_cast<cabal_diamond_mssql_shadow_config*>(context);
 if(!c||c->abi_version!=CABAL_DIAMOND_MSSQL_SHADOW_ABI||
    !c->active_authenticated_session||session!=c->active_authenticated_session||
    !c->odbc_connection_string||user==0)
   return -1;
 const auto* s=c->active_authenticated_session;
 if(s->tag!=CABAL_DIAMOND_MSSQL_SHADOW_SESSION_TAG ||
    s->user_num!=user||s->nonce==0||
    s->nonce>static_cast<uint64_t>(std::numeric_limits<std::int64_t>::max()))
   return -1;
 try {
  std::unique_ptr<Transaction> tx(new Transaction);
  tx->connect(c->odbc_connection_string);
  tx->account_load(user,static_cast<std::int64_t>(s->nonce));
  *out=tx.release();
  return 0;
 } catch(...) {return -1;}
}
int load(void*,void* ptr,cabal_diamond_state* result){
 if(!ptr||!result)return -1;
 try{
  auto& tx=*static_cast<Transaction*>(ptr);
  tx.load_children();*result={};
  result->abi_version=CABAL_DIAMOND_ABI_VERSION;
  result->server_authoritative=1; // shadow state authenticated and locked
  result->badge_grade=tx.grade;
  result->platinum_badge=tx.platinum_badge;
  result->platinum_maxed=tx.platinum_maxed;
  result->revision=tx.revision;
  result->wexp=static_cast<std::uint64_t>(tx.wexp);
  result->verified_exchange_ticket_count=tx.tickets; // SHADOW, NOT real CABAL inventory
  result->free_points=tx.points;
  result->active_category_mask=tx.active_categories;
  result->server_open_mastery_ids=tx.open_slots.empty()?nullptr:tx.open_slots.data();
  result->server_open_count=tx.open_slots.size();
  result->server_levels=tx.levels.empty()?nullptr:tx.levels.data();
  result->server_level_count=tx.levels.size();
  return 0;
 }catch(...){return -1;}
}
int commit(void*,void* ptr,const cabal_diamond_request* req,
           const cabal_diamond_evaluation* result){
 if(!ptr||!req||!result)return -1;
 try{
  auto* tx=static_cast<Transaction*>(ptr);
  tx->guarded_commit(*req,*result);
  delete tx; // WorldBridge contract: success consumes transaction token
  return 0;
 }catch(...) {return -1;} // WorldBridge aborts and rolls back on failure.
}
void abort_tx(void*,void* ptr){delete static_cast<Transaction*>(ptr);}
} // namespace
extern "C" cabal_diamond_world_callbacks cabal_diamond_mssql_shadow_callbacks(void){
 cabal_diamond_world_callbacks c{};
 c.version=CABAL_DIAMOND_WORLD_BRIDGE_VERSION;
 c.begin_authenticated_locked=begin;
 c.load_trusted_state=load;
 c.commit_durable=commit;
 c.abort_transaction=abort_tx;
 return c;
}
