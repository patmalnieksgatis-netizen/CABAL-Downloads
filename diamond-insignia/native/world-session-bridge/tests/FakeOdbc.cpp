// Fake ODBC driver. CI ONLY; never connected to a SQL Server.
// Source restored from the owner's local ODBC test artifact.
#include <sql.h>
#include <sqlext.h>
#include <algorithm>
#include <cstring>
#include <map>
#include <memory>
#include <mutex>
#include <set>
#include <string>
#include <vector>
#include <cstdint>
namespace fakeodbc {
struct Receipt {
 int command, mastery, applied, badge;
 std::int64_t wexp;
 int tickets, points, changed, level;
};
struct Data {
 int user=900001, badge=1, platinum=1, maxed=1, tickets=120, points=100, mask=1, rev=10;
 std::int64_t nonce=123456789, wexp=40000;
 std::set<int> slots{159};
 std::map<int,int> mastery;
 std::map<int,Receipt> receipts;
};
std::mutex mutex;
Data database;
int commits=0, rollbacks=0;
bool failReceiptOnce=false;
void reset(){ std::lock_guard<std::mutex> lock(mutex); database=Data{};commits=rollbacks=0;failReceiptOnce=false; }
}
namespace {
struct Env {int ok=1;};
struct Conn {
 bool connected=false, autocommitOff=false;
 std::string databaseName="Server01_DiamondLab";
 std::unique_lock<std::mutex> lock;
 fakeodbc::Data local;
};
struct Cell {std::int64_t i=0; std::string s; bool text=false;};
struct Stmt {
 Conn* db=nullptr;
 std::string sql;
 std::map<int,SQLPOINTER> params;
 std::map<int,SQLSMALLINT> types;
 std::vector<std::vector<Cell>> rows;
 std::size_t next=0;
 std::size_t current=0;
 SQLLEN changed=0;
};
std::int64_t p(Stmt& st,int n){
 auto it=st.params.find(n);
 if(it==st.params.end() || !it->second)return -1;
 const SQLSMALLINT type=st.types[n];
 if(type==SQL_C_SLONG)return *reinterpret_cast<SQLINTEGER*>(it->second);
 if(type==SQL_C_SBIGINT)return *reinterpret_cast<SQLBIGINT*>(it->second);
 return -1;
}
Cell n(std::int64_t i){return Cell{i,"",false};}
Cell s(std::string txt){return Cell{0,std::move(txt),true};}
bool has(const std::string& text,const char* fragment){return text.find(fragment)!=std::string::npos;}
SQLRETURN run(Stmt& st){
 st.rows.clear();st.next=0;st.changed=0;
 auto& db=st.db->local;
 if(has(st.sql,"SELECT DB_NAME()")){
  st.rows.push_back({s(st.db->databaseName)});return SQL_SUCCESS;
 }
 if(has(st.sql,"FROM dbo.cabal_diamond_bridge_wallet_v2")){
  if(!st.db->lock.owns_lock()){
   st.db->lock=std::unique_lock<std::mutex>(fakeodbc::mutex);
   db=fakeodbc::database;
  }
  if(p(st,1)==db.user && p(st,2)==db.nonce){
   st.rows.push_back({n(db.platinum),n(db.maxed),n(db.badge),n(db.wexp),n(db.tickets),
                       n(db.points),n(db.mask),n(db.rev)});
  }
  return SQL_SUCCESS;
 }
 if(has(st.sql,"FROM dbo.cabal_diamond_v291_receipt_v1")){
  if(p(st,1)!=db.user)return SQL_SUCCESS;
  const auto it=db.receipts.find(static_cast<int>(p(st,2)));
  if(it!=db.receipts.end()){
   const auto& r=it->second;
   st.rows.push_back({n(r.command),n(r.mastery),n(r.applied),n(r.badge),n(r.wexp),
                      n(r.tickets),n(r.points),n(r.changed),n(r.level)});
  }
  return SQL_SUCCESS;
 }
 if(has(st.sql,"FROM dbo.cabal_diamond_bridge_slot_v2")){
  if(p(st,1)==db.user)for(int id:db.slots)st.rows.push_back({n(id)});
  return SQL_SUCCESS;
 }
 if(has(st.sql,"FROM dbo.cabal_diamond_bridge_mastery_v2")){
  if(p(st,1)==db.user)for(auto [id,lv]:db.mastery)st.rows.push_back({n(id),n(lv)});
  return SQL_SUCCESS;
 }
 if(has(st.sql,"UPDATE dbo.cabal_diamond_bridge_wallet_v2")){
  if(p(st,6)==db.user && p(st,7)==db.nonce && p(st,8)==db.rev &&
     p(st,9)==db.badge && p(st,10)==db.wexp && p(st,11)==db.tickets && p(st,12)==db.points){
     db.badge=p(st,1);db.wexp=p(st,2);db.tickets=p(st,3);db.points=p(st,4);db.rev=p(st,5);
     st.changed=1;
  }
  return SQL_SUCCESS;
 }
 if(has(st.sql,"INSERT INTO dbo.cabal_diamond_bridge_mastery_v2")){
  if(p(st,1)==db.user && db.mastery.count(static_cast<int>(p(st,2)))==0){
   db.mastery[p(st,2)]=p(st,3);st.changed=1;
  }
  return SQL_SUCCESS;
 }
 if(has(st.sql,"UPDATE dbo.cabal_diamond_bridge_mastery_v2")){
  auto it=db.mastery.find(p(st,3));
  if(p(st,2)==db.user && it!=db.mastery.end() && it->second==p(st,4)){
   it->second=p(st,1);st.changed=1;
  }
  return SQL_SUCCESS;
 }
 if(has(st.sql,"INSERT INTO dbo.cabal_diamond_v291_receipt_v1")){
  if(fakeodbc::failReceiptOnce){fakeodbc::failReceiptOnce=false;return SQL_ERROR;}
  if(p(st,1)==db.user && !db.receipts.count(p(st,2))){
   db.receipts[p(st,2)]={static_cast<int>(p(st,3)),static_cast<int>(p(st,4)),static_cast<int>(p(st,5)),
      static_cast<int>(p(st,6)),p(st,7),static_cast<int>(p(st,8)),static_cast<int>(p(st,9)),
      static_cast<int>(p(st,10)),static_cast<int>(p(st,11))};
   st.changed=1;
  }
  return SQL_SUCCESS;
 }
 return SQL_ERROR;
}
}
extern "C" {
SQLRETURN SQL_API SQLAllocHandle(SQLSMALLINT type,SQLHANDLE parent,SQLHANDLE* out){
 if(!out)return SQL_ERROR;
 if(type==SQL_HANDLE_ENV){*out=new Env;return SQL_SUCCESS;}
 if(type==SQL_HANDLE_DBC){*out=new Conn;return SQL_SUCCESS;}
 if(type==SQL_HANDLE_STMT){auto* st=new Stmt;st->db=reinterpret_cast<Conn*>(parent);*out=st;return SQL_SUCCESS;}
 return SQL_ERROR;
}
SQLRETURN SQL_API SQLFreeHandle(SQLSMALLINT type,SQLHANDLE h){
 if(type==SQL_HANDLE_ENV)delete reinterpret_cast<Env*>(h);
 else if(type==SQL_HANDLE_DBC)delete reinterpret_cast<Conn*>(h);
 else if(type==SQL_HANDLE_STMT)delete reinterpret_cast<Stmt*>(h);
 else return SQL_ERROR;
 return SQL_SUCCESS;
}
SQLRETURN SQL_API SQLSetEnvAttr(SQLHENV,SQLINTEGER,SQLPOINTER,SQLINTEGER){return SQL_SUCCESS;}
SQLRETURN SQL_API SQLDriverConnectA(SQLHDBC h,SQLHWND,SQLCHAR* str,SQLSMALLINT,
                                    SQLCHAR*,SQLSMALLINT,SQLSMALLINT* olen,SQLUSMALLINT){
 auto* c=reinterpret_cast<Conn*>(h);
 if(!str)return SQL_ERROR;
 std::string connection(reinterpret_cast<char*>(str));
 if(has(connection,"Database=Server01_DiamondLab"))c->databaseName="Server01_DiamondLab";
 else c->databaseName="Server01";
 c->connected=true;if(olen)*olen=0;
 return SQL_SUCCESS;
}
SQLRETURN SQL_API SQLSetConnectAttr(SQLHDBC h,SQLINTEGER key,SQLPOINTER value,SQLINTEGER){
 auto* c=reinterpret_cast<Conn*>(h);
 if(key==SQL_ATTR_AUTOCOMMIT)c->autocommitOff=reinterpret_cast<std::uintptr_t>(value)==SQL_AUTOCOMMIT_OFF;
 return SQL_SUCCESS;
}
SQLRETURN SQL_API SQLDisconnect(SQLHDBC h){
 auto* c=reinterpret_cast<Conn*>(h);
 if(c->lock.owns_lock())c->lock.unlock();
 c->connected=false;return SQL_SUCCESS;
}
SQLRETURN SQL_API SQLPrepareA(SQLHSTMT h,SQLCHAR* query,SQLINTEGER){
 auto* st=reinterpret_cast<Stmt*>(h);
 st->sql=reinterpret_cast<char*>(query);return SQL_SUCCESS;
}
SQLRETURN SQL_API SQLExecDirectA(SQLHSTMT h,SQLCHAR* query,SQLINTEGER){
 auto* st=reinterpret_cast<Stmt*>(h);
 st->sql=reinterpret_cast<char*>(query);return run(*st);
}
SQLRETURN SQL_API SQLBindParameter(SQLHSTMT h,SQLUSMALLINT n,SQLSMALLINT,
   SQLSMALLINT type,SQLSMALLINT,SQLULEN,SQLSMALLINT,SQLPOINTER ptr,SQLLEN,SQLLEN*){
 auto* st=reinterpret_cast<Stmt*>(h);
 st->params[n]=ptr;st->types[n]=type;return SQL_SUCCESS;
}
SQLRETURN SQL_API SQLExecute(SQLHSTMT h){return run(*reinterpret_cast<Stmt*>(h));}
SQLRETURN SQL_API SQLFetch(SQLHSTMT h){
 auto* st=reinterpret_cast<Stmt*>(h);
 if(st->next>=st->rows.size())return SQL_NO_DATA;
 st->current=st->next++;return SQL_SUCCESS;
}
SQLRETURN SQL_API SQLGetData(SQLHSTMT h,SQLUSMALLINT col,SQLSMALLINT type,
                              SQLPOINTER out,SQLLEN cap,SQLLEN* length){
 auto* st=reinterpret_cast<Stmt*>(h);
 if(st->current>=st->rows.size() || col==0 || col>st->rows[st->current].size())return SQL_ERROR;
 auto& v=st->rows[st->current][col-1];
 if(type==SQL_C_SLONG && cap>=static_cast<SQLLEN>(sizeof(SQLINTEGER))){
  *reinterpret_cast<SQLINTEGER*>(out)=v.i;if(length)*length=sizeof(SQLINTEGER);return SQL_SUCCESS;
 }
 if(type==SQL_C_SBIGINT && cap>=static_cast<SQLLEN>(sizeof(SQLBIGINT))){
  *reinterpret_cast<SQLBIGINT*>(out)=v.i;if(length)*length=sizeof(SQLBIGINT);return SQL_SUCCESS;
 }
 if(type==SQL_C_CHAR && v.text && cap>static_cast<SQLLEN>(v.s.size())){
  std::memcpy(out,v.s.c_str(),v.s.size()+1);if(length)*length=v.s.size();return SQL_SUCCESS;
 }
 return SQL_ERROR;
}
SQLRETURN SQL_API SQLRowCount(SQLHSTMT h,SQLLEN* out){
 if(!out)return SQL_ERROR;
 *out=reinterpret_cast<Stmt*>(h)->changed;
 return SQL_SUCCESS;
}
SQLRETURN SQL_API SQLEndTran(SQLSMALLINT type,SQLHANDLE h,SQLSMALLINT decision){
 if(type!=SQL_HANDLE_DBC)return SQL_ERROR;
 auto* c=reinterpret_cast<Conn*>(h);
 if(decision==SQL_COMMIT){
  if(!c->lock.owns_lock())return SQL_ERROR;
  fakeodbc::database=c->local;fakeodbc::commits++;
 }else fakeodbc::rollbacks++;
 if(c->lock.owns_lock())c->lock.unlock();
 return SQL_SUCCESS;
}
} // extern "C"
