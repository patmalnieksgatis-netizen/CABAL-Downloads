// Source restored from the owner's 2026-11-22 isolated ODBC transaction
// artifact. SYNTHETIC DATABASE Server01_DiamondLab ONLY. NOT FOR LIVE SERVER.
#include "DiamondLabOdbcBackend.h"
#include <algorithm>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>

namespace diamond_v291 {
namespace {
inline bool ok(SQLRETURN x) {return SQL_SUCCEEDED(x);}
class Statement final {
    SQLHSTMT h_=SQL_NULL_HSTMT;
public:
    explicit Statement(SQLHDBC dbc) {
        if(!ok(SQLAllocHandle(SQL_HANDLE_STMT,dbc,&h_)))
            throw std::runtime_error("ODBC alloc stmt failed");
    }
    ~Statement(){ if(h_!=SQL_NULL_HSTMT)SQLFreeHandle(SQL_HANDLE_STMT,h_); }
    Statement(const Statement&)=delete;
    Statement& operator=(const Statement&)=delete;
    void prepare(const char* query) {
        if(!ok(SQLPrepareA(h_,(SQLCHAR*)query,SQL_NTS)))
            throw std::runtime_error("ODBC prepare failed");
    }
    void bindInt(SQLUSMALLINT n, SQLINTEGER& x) {
        if(!ok(SQLBindParameter(h_,n,SQL_PARAM_INPUT,SQL_C_SLONG,SQL_INTEGER,0,0,&x,0,nullptr)))
            throw std::runtime_error("ODBC bind integer failed");
    }
    void bindLong(SQLUSMALLINT n, SQLBIGINT& x) {
        if(!ok(SQLBindParameter(h_,n,SQL_PARAM_INPUT,SQL_C_SBIGINT,SQL_BIGINT,0,0,&x,0,nullptr)))
            throw std::runtime_error("ODBC bind big integer failed");
    }
    void run() {
        if(!ok(SQLExecute(h_)))throw std::runtime_error("ODBC execute failed");
    }
    void direct(const char* query) {
        if(!ok(SQLExecDirectA(h_,(SQLCHAR*)query,SQL_NTS)))
            throw std::runtime_error("ODBC direct execution failed");
    }
    bool fetch(){
        const SQLRETURN r=SQLFetch(h_);
        if(r==SQL_NO_DATA)return false;
        if(!ok(r))throw std::runtime_error("ODBC fetch failed");
        return true;
    }
    SQLINTEGER i32(SQLUSMALLINT col){
        SQLINTEGER v=0;SQLLEN ind=0;
        if(!ok(SQLGetData(h_,col,SQL_C_SLONG,&v,sizeof(v),&ind)) || ind==SQL_NULL_DATA)
            throw std::runtime_error("ODBC int read failed");
        return v;
    }
    SQLBIGINT i64(SQLUSMALLINT col){
        SQLBIGINT v=0;SQLLEN ind=0;
        if(!ok(SQLGetData(h_,col,SQL_C_SBIGINT,&v,sizeof(v),&ind)) || ind==SQL_NULL_DATA)
            throw std::runtime_error("ODBC long read failed");
        return v;
    }
    std::string str(SQLUSMALLINT col){
        char value[128]{}; SQLLEN ind=0;
        const SQLRETURN r=SQLGetData(h_,col,SQL_C_CHAR,value,sizeof(value),&ind);
        if(!ok(r) || ind==SQL_NULL_DATA || ind>=static_cast<SQLLEN>(sizeof(value)))
            throw std::runtime_error("ODBC string read failed");
        return std::string(value);
    }
    bool exactlyOne(){SQLLEN count=-1;return ok(SQLRowCount(h_,&count)) && count==1;}
};
constexpr std::uint32_t kOnlySyntheticUser=900001;
constexpr std::int64_t kOnlySyntheticNonce=123456789;
}

DiamondLabOdbcBackend::DiamondLabOdbcBackend(std::string conn,AttestSession attest,void* ctx) noexcept
    :connection_(std::move(conn)),attest_(attest),attestContext_(ctx){}
DiamondLabOdbcBackend::~DiamondLabOdbcBackend(){release(false);}

bool DiamondLabOdbcBackend::connectAndBegin(){
    if(!ok(SQLAllocHandle(SQL_HANDLE_ENV,SQL_NULL_HANDLE,&env_)))return false;
    if(!ok(SQLSetEnvAttr(env_,SQL_ATTR_ODBC_VERSION,(SQLPOINTER)SQL_OV_ODBC3,0)))return false;
    if(!ok(SQLAllocHandle(SQL_HANDLE_DBC,env_,&dbc_)))return false;
    SQLCHAR out[1024]; SQLSMALLINT n=0;
    if(!ok(SQLDriverConnectA(dbc_,nullptr,(SQLCHAR*)connection_.c_str(),SQL_NTS,
                             out,sizeof(out),&n,SQL_DRIVER_NOPROMPT)))return false;
    if(!ok(SQLSetConnectAttr(dbc_,SQL_ATTR_TXN_ISOLATION,(SQLPOINTER)SQL_TXN_SERIALIZABLE,0)))return false;
    if(!ok(SQLSetConnectAttr(dbc_,SQL_ATTR_AUTOCOMMIT,(SQLPOINTER)SQL_AUTOCOMMIT_OFF,0)))return false;
    transaction_=true;
    return true;
}
bool DiamondLabOdbcBackend::verifyDatabase(){
    Statement q(dbc_);
    q.direct("SELECT DB_NAME()");
    if(!q.fetch() || q.str(1)!="Server01_DiamondLab" || q.fetch())return false;
    return true;
}
bool DiamondLabOdbcBackend::lockWallet(){
    Statement q(dbc_);
    q.prepare("SELECT PlatinumBadge,PlatinumMaxed,BadgeGrade,WExp,MedalItemCount,"
              "FreePoints,ActiveCategoryMask,RowRevision FROM dbo.cabal_diamond_bridge_wallet_v2 "
              "WITH (UPDLOCK,HOLDLOCK) WHERE UserNum=? AND SessionNonce=?");
    SQLINTEGER user=static_cast<SQLINTEGER>(session_.userNum);
    SQLBIGINT nonce=static_cast<SQLBIGINT>(session_.shadowNonce);
    q.bindInt(1,user);q.bindLong(2,nonce);q.run();
    if(!q.fetch())return false;
    wallet_.platinumBadge=q.i32(1);wallet_.platinumMaxed=q.i32(2);
    wallet_.badgeGrade=q.i32(3);wallet_.wexp=q.i64(4);
    wallet_.tickets=q.i32(5);wallet_.freePoints=q.i32(6);
    wallet_.categories=q.i32(7);wallet_.revision=q.i32(8);
    if(q.fetch())return false;
    return wallet_.revision>=0 && wallet_.wexp>=0 && wallet_.tickets>=0 &&
           wallet_.freePoints>=0 && (wallet_.badgeGrade==1 || wallet_.badgeGrade==2) &&
           (wallet_.platinumBadge==0 || wallet_.platinumBadge==1) &&
           (wallet_.platinumMaxed==0 || wallet_.platinumMaxed==1) &&
           wallet_.categories>=0 && wallet_.categories<=65535;
}
bool DiamondLabOdbcBackend::begin(const void* session,Identity& owner){
    owner={};
    if(!session || !attest_ || ready_ || env_!=SQL_NULL_HENV || dbc_!=SQL_NULL_HDBC)return false;
    try {
        VerifiedSession out{};
        if(!attest_(session,out,attestContext_) || out.userNum!=kOnlySyntheticUser ||
           out.shadowNonce!=kOnlySyntheticNonce || !out.characterIdx || connection_.empty())return false;
        session_=out;
        if(!connectAndBegin() || !verifyDatabase() || !lockWallet()) {
            release(false);return false;
        }
        owner.userNum=session_.userNum;owner.characterIdx=session_.characterIdx;
        ready_=true;
        return true;
    } catch(...){release(false);return false;}
}
Lookup DiamondLabOdbcBackend::receipt(std::uint32_t expected,const Request& request,Receipt& out){
    out={};
    if(!ready_ || expected!=request.expectedRevision || expected>INT32_MAX)return Lookup::Failure;
    try{
        Statement q(dbc_);
        q.prepare("SELECT Command,MasteryID,AppliedRevision,NewBadgeGrade,NewWExp,"
                  "NewTicketCount,NewFreePoints,ChangedMasteryID,ChangedMasteryLevel "
                  "FROM dbo.cabal_diamond_v291_receipt_v1 WITH (UPDLOCK,HOLDLOCK) "
                  "WHERE UserNum=? AND ExpectedRevision=?");
        SQLINTEGER user=static_cast<SQLINTEGER>(session_.userNum), rev=static_cast<SQLINTEGER>(expected);
        q.bindInt(1,user);q.bindInt(2,rev);q.run();
        if(!q.fetch())return Lookup::Fresh;
        const auto cmd=q.i32(1), mastery=q.i32(2);
        const int revision=q.i32(3),badge=q.i32(4);
        const auto wexp=q.i64(5);
        const int tickets=q.i32(6),points=q.i32(7),changed=q.i32(8),level=q.i32(9);
        if(q.fetch() || revision!=static_cast<int>(expected+1) || wexp<0 || tickets<0 || points<0 ||
           (badge!=1 && badge!=2))return Lookup::Failure;
        if(cmd!=static_cast<int>(request.command) || mastery!=request.masteryId)
            return Lookup::ConflictingCommitted;
        out.request=request;
        out.applied.abi_version=CABAL_DIAMOND_ABI_VERSION;
        out.applied.permitted=1;
        out.applied.requires_atomic_commit=1;
        out.applied.new_revision=static_cast<std::uint32_t>(revision);
        out.applied.new_badge_grade=static_cast<std::uint32_t>(badge);
        out.applied.new_wexp=static_cast<std::uint64_t>(wexp);
        out.applied.new_ticket_count=static_cast<std::uint32_t>(tickets);
        out.applied.new_free_points=points;
        out.applied.changed_mastery_id=changed;
        out.applied.changed_mastery_level=level;
        return Lookup::SameCommitted;
    }catch(...){return Lookup::Failure;}
}
bool DiamondLabOdbcBackend::loadMasteryAndSlots(){
    slots_.clear();levels_.clear();
    SQLINTEGER user=static_cast<SQLINTEGER>(session_.userNum);
    {
        Statement q(dbc_);
        q.prepare("SELECT MasteryID FROM dbo.cabal_diamond_bridge_slot_v2 WITH (HOLDLOCK) "
                  "WHERE UserNum=? ORDER BY MasteryID");
        q.bindInt(1,user);q.run();
        while(q.fetch()){
            const int id=q.i32(1);
            if(id<159 || id>474 || slots_.size()>=316)return false;
            slots_.push_back(static_cast<std::uint32_t>(id));
        }
    }
    {
        Statement q(dbc_);
        q.prepare("SELECT MasteryID,MasteryLevel FROM dbo.cabal_diamond_bridge_mastery_v2 "
                  "WITH (HOLDLOCK) WHERE UserNum=? ORDER BY MasteryID");
        q.bindInt(1,user);q.run();
        while(q.fetch()){
            const int id=q.i32(1),level=q.i32(2);
            if(id<159 || id>474 || level<1 || level>100 || levels_.size()>=316)return false;
            levels_.push_back({id,level});
        }
    }
    return true;
}
bool DiamondLabOdbcBackend::trustedState(cabal_diamond_state& state){
    state={};
    if(!ready_)return false;
    try{
        if(!loadMasteryAndSlots())return false;
        state.abi_version=CABAL_DIAMOND_ABI_VERSION;
        state.server_authoritative=1;
        state.badge_grade=static_cast<std::uint32_t>(wallet_.badgeGrade);
        state.platinum_badge=static_cast<std::uint32_t>(wallet_.platinumBadge);
        state.platinum_maxed=static_cast<std::uint32_t>(wallet_.platinumMaxed);
        state.revision=static_cast<std::uint32_t>(wallet_.revision);
        state.wexp=static_cast<std::uint64_t>(wallet_.wexp);
        state.verified_exchange_ticket_count=static_cast<std::uint32_t>(wallet_.tickets);
        state.free_points=wallet_.freePoints;
        state.active_category_mask=static_cast<std::uint32_t>(wallet_.categories);
        state.server_open_mastery_ids=slots_.empty()?nullptr:slots_.data();
        state.server_open_count=slots_.size();
        state.server_levels=levels_.empty()?nullptr:levels_.data();
        state.server_level_count=levels_.size();
        stateLoaded_=true;
        return true;
    }catch(...){return false;}
}
bool DiamondLabOdbcBackend::updateWallet(const cabal_diamond_evaluation& e){
    Statement q(dbc_);
    q.prepare("UPDATE dbo.cabal_diamond_bridge_wallet_v2 SET BadgeGrade=?,WExp=?,"
              "MedalItemCount=?,FreePoints=?,RowRevision=? WHERE UserNum=? AND SessionNonce=? "
              "AND RowRevision=? AND BadgeGrade=? AND WExp=? AND MedalItemCount=? AND FreePoints=?");
    SQLINTEGER badge=e.new_badge_grade,tickets=e.new_ticket_count,points=e.new_free_points;
    SQLINTEGER newrev=e.new_revision,user=session_.userNum,oldrev=wallet_.revision,oldbadge=wallet_.badgeGrade;
    SQLINTEGER oldtickets=wallet_.tickets,oldpoints=wallet_.freePoints;
    SQLBIGINT newwexp=e.new_wexp,nonce=session_.shadowNonce,oldwexp=wallet_.wexp;
    q.bindInt(1,badge);q.bindLong(2,newwexp);q.bindInt(3,tickets);q.bindInt(4,points);
    q.bindInt(5,newrev);q.bindInt(6,user);q.bindLong(7,nonce);q.bindInt(8,oldrev);
    q.bindInt(9,oldbadge);q.bindLong(10,oldwexp);q.bindInt(11,oldtickets);q.bindInt(12,oldpoints);
    q.run();return q.exactlyOne();
}
bool DiamondLabOdbcBackend::updateMastery(const Request& r,const cabal_diamond_evaluation& e){
    if(r.command==CABAL_DIAMOND_RANK_UP)return e.changed_mastery_id==0 && e.changed_mastery_level==0;
    if(r.command!=CABAL_DIAMOND_MASTERY_LEVEL_UP || e.changed_mastery_id!=r.masteryId)return false;
    const auto slot=std::find(slots_.begin(),slots_.end(),static_cast<std::uint32_t>(r.masteryId));
    if(slot==slots_.end())return false;
    int prior=0;
    for(const auto& m:levels_)if(m.mastery_id==r.masteryId){prior=m.level;break;}
    if(e.changed_mastery_level!=prior+1 || e.changed_mastery_level>100)return false;
    SQLINTEGER user=session_.userNum,mastery=r.masteryId, newlevel=e.changed_mastery_level;
    if(prior==0){
        Statement ins(dbc_);
        ins.prepare("INSERT INTO dbo.cabal_diamond_bridge_mastery_v2(UserNum,MasteryID,MasteryLevel) VALUES(?,?,?)");
        ins.bindInt(1,user);ins.bindInt(2,mastery);ins.bindInt(3,newlevel);
        ins.run();return ins.exactlyOne();
    }
    Statement upd(dbc_);
    upd.prepare("UPDATE dbo.cabal_diamond_bridge_mastery_v2 SET MasteryLevel=? "
                "WHERE UserNum=? AND MasteryID=? AND MasteryLevel=?");
    SQLINTEGER oldlevel=prior;
    upd.bindInt(1,newlevel);upd.bindInt(2,user);upd.bindInt(3,mastery);upd.bindInt(4,oldlevel);
    upd.run();return upd.exactlyOne();
}
bool DiamondLabOdbcBackend::insertReceipt(const Request& r,const cabal_diamond_evaluation& e){
    Statement q(dbc_);
    q.prepare("INSERT INTO dbo.cabal_diamond_v291_receipt_v1 "
              "(UserNum,ExpectedRevision,Command,MasteryID,AppliedRevision,NewBadgeGrade,NewWExp,"
              "NewTicketCount,NewFreePoints,ChangedMasteryID,ChangedMasteryLevel) VALUES(?,?,?,?,?,?,?,?,?,?,?)");
    SQLINTEGER user=session_.userNum,rev=r.expectedRevision,cmd=r.command,mastery=r.masteryId;
    SQLINTEGER applied=e.new_revision,badge=e.new_badge_grade,tickets=e.new_ticket_count;
    SQLINTEGER points=e.new_free_points,changed=e.changed_mastery_id,level=e.changed_mastery_level;
    SQLBIGINT wexp=e.new_wexp;
    q.bindInt(1,user);q.bindInt(2,rev);q.bindInt(3,cmd);q.bindInt(4,mastery);
    q.bindInt(5,applied);q.bindInt(6,badge);q.bindLong(7,wexp);
    q.bindInt(8,tickets);q.bindInt(9,points);q.bindInt(10,changed);q.bindInt(11,level);
    q.run();return q.exactlyOne();
}
bool DiamondLabOdbcBackend::commitAll(const Identity& owner,const Request& r,
                                      const cabal_diamond_evaluation& e){
    if(!ready_ || !transaction_ || !stateLoaded_ || committed_ ||
       owner.userNum!=session_.userNum || owner.characterIdx!=session_.characterIdx ||
       r.expectedRevision!=static_cast<std::uint32_t>(wallet_.revision) ||
       wallet_.revision==INT32_MAX || e.new_revision!=r.expectedRevision+1 ||
       e.abi_version!=CABAL_DIAMOND_ABI_VERSION || e.permitted!=1 ||
       e.requires_atomic_commit!=1 || e.new_wexp>static_cast<std::uint64_t>(wallet_.wexp) ||
       e.new_wexp>INT64_MAX || e.new_ticket_count>static_cast<std::uint32_t>(wallet_.tickets) ||
       e.new_ticket_count>INT32_MAX || e.new_free_points<0 || e.new_badge_grade!=2 ||
       e.new_badge_grade<static_cast<std::uint32_t>(wallet_.badgeGrade))return false;
    try{
        if(!updateWallet(e) || !updateMastery(r,e) || !insertReceipt(r,e))return false;
        if(!ok(SQLEndTran(SQL_HANDLE_DBC,dbc_,SQL_COMMIT)))return false;
        transaction_=false;committed_=true;
        return true;
    }catch(...){return false;}
}
void DiamondLabOdbcBackend::closeHandles() noexcept{
    if(dbc_!=SQL_NULL_HDBC){
        SQLDisconnect(dbc_);SQLFreeHandle(SQL_HANDLE_DBC,dbc_);dbc_=SQL_NULL_HDBC;
    }
    if(env_!=SQL_NULL_HENV){SQLFreeHandle(SQL_HANDLE_ENV,env_);env_=SQL_NULL_HENV;}
    ready_=false;stateLoaded_=false;
    session_={};wallet_={};slots_.clear();levels_.clear();
}
void DiamondLabOdbcBackend::release(bool) noexcept{
    if(transaction_ && dbc_!=SQL_NULL_HDBC)SQLEndTran(SQL_HANDLE_DBC,dbc_,SQL_ROLLBACK);
    transaction_=false;closeHandles();
}
} // namespace diamond_v291
