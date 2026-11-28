#include "DiamondRealGameDataOdbc.h"
#include "DiamondWarExpAccounting.h"
#include <sql.h>
#include <sqlext.h>
#include <climits>
#include <cstring>
#include <limits>
#include <memory>
#include <string>
#include <utility>

namespace diamond_v291::real_gamedata {
namespace {
using diamond_v291::gradeup0bda::AtomicCommitState;
using diamond_v291::gradeup0bda::AtomicCommitOutcome;
using diamond_v291::gradeup0bda::AtomicGradeUpRequest;
bool Ok(SQLRETURN code) noexcept {return SQL_SUCCEEDED(code);}

struct Connection {
    SQLHENV env=SQL_NULL_HENV;
    SQLHDBC dbc=SQL_NULL_HDBC;
    ~Connection(){
        if(dbc!=SQL_NULL_HDBC){
            SQLDisconnect(dbc);
            SQLFreeHandle(SQL_HANDLE_DBC,dbc);
        }
        if(env!=SQL_NULL_HENV)SQLFreeHandle(SQL_HANDLE_ENV,env);
    }
    bool Open(const std::string& text) noexcept {
        if(text.empty() || text.size()>2048)return false;
        if(!Ok(SQLAllocHandle(SQL_HANDLE_ENV,SQL_NULL_HANDLE,&env)))return false;
        if(!Ok(SQLSetEnvAttr(env,SQL_ATTR_ODBC_VERSION,
                            reinterpret_cast<SQLPOINTER>(SQL_OV_ODBC3),0)))
            return false;
        if(!Ok(SQLAllocHandle(SQL_HANDLE_DBC,env,&dbc)))return false;
        if(!Ok(SQLSetConnectAttr(dbc,SQL_ATTR_LOGIN_TIMEOUT,
                                reinterpret_cast<SQLPOINTER>(static_cast<std::uintptr_t>(8)),0)))
            return false;
        SQLCHAR driverOutput[4096]{};
        SQLSMALLINT outputLen=0;
        return Ok(SQLDriverConnectA(dbc,nullptr,
            reinterpret_cast<SQLCHAR*>(const_cast<char*>(text.data())),
            SQL_NTS,driverOutput,sizeof(driverOutput),&outputLen,
            SQL_DRIVER_NOPROMPT));
    }
};
struct Statement {
    SQLHSTMT h=SQL_NULL_HSTMT;
    explicit Statement(SQLHDBC dbc) noexcept {
        if(!Ok(SQLAllocHandle(SQL_HANDLE_STMT,dbc,&h)))return;
        if(!Ok(SQLSetStmtAttr(h,SQL_ATTR_QUERY_TIMEOUT,
              reinterpret_cast<SQLPOINTER>(static_cast<std::uintptr_t>(30)),0))){
            SQLFreeHandle(SQL_HANDLE_STMT,h);h=SQL_NULL_HSTMT;
        }
    }
    ~Statement(){if(h!=SQL_NULL_HSTMT)SQLFreeHandle(SQL_HANDLE_STMT,h);}
    bool Ready() const noexcept{return h!=SQL_NULL_HSTMT;}
    bool Prepare(const char* sql) noexcept {
        return Ready() && Ok(SQLPrepareA(h,
            reinterpret_cast<SQLCHAR*>(const_cast<char*>(sql)),SQL_NTS));
    }
    bool Direct(const char* sql) noexcept {
        return Ready() && Ok(SQLExecDirectA(h,
            reinterpret_cast<SQLCHAR*>(const_cast<char*>(sql)),SQL_NTS));
    }
    bool I32(SQLUSMALLINT index,SQLINTEGER& value) noexcept {
        return Ok(SQLBindParameter(h,index,SQL_PARAM_INPUT,SQL_C_SLONG,
            SQL_INTEGER,0,0,&value,0,nullptr));
    }
    bool I64(SQLUSMALLINT index,SQLBIGINT& value) noexcept {
        return Ok(SQLBindParameter(h,index,SQL_PARAM_INPUT,SQL_C_SBIGINT,
            SQL_BIGINT,0,0,&value,0,nullptr));
    }
    bool Binary(SQLUSMALLINT index,std::vector<std::uint8_t>& data,
                SQLLEN& size) noexcept {
        size=static_cast<SQLLEN>(data.size());
        // Handles both 30B and 15K GameData; no streaming parameter.
        return Ok(SQLBindParameter(h,index,SQL_PARAM_INPUT,SQL_C_BINARY,
            SQL_LONGVARBINARY,data.size(),0,data.data(),
            static_cast<SQLLEN>(data.size()),&size));
    }
    bool Run() noexcept {return Ready() && Ok(SQLExecute(h));}
    bool FetchI32(SQLINTEGER& value) noexcept {
        if(!Ready() || !Ok(SQLFetch(h)))return false;
        SQLLEN ind=0;
        if(!Ok(SQLGetData(h,1,SQL_C_SLONG,&value,sizeof(value),&ind)) ||
           ind==SQL_NULL_DATA)return false;
        return SQLFetch(h)==SQL_NO_DATA;
    }
};
bool VerifiedServer01Database(SQLHDBC db) noexcept {
    Statement q(db);
    if(!q.Direct("SELECT DB_NAME()"))return false;
    if(!Ok(SQLFetch(q.h)))return false;
    char name[64]{};
    SQLLEN indicator=0;
    const auto rc=SQLGetData(q.h,1,SQL_C_CHAR,name,sizeof(name),&indicator);
    if(!Ok(rc) || indicator==SQL_NULL_DATA ||
       indicator<0 || indicator>=static_cast<SQLLEN>(sizeof(name)))
        return false;
    if(std::strcmp(name,"Server01")!=0)return false;
    return SQLFetch(q.h)==SQL_NO_DATA;
}
bool VerifyCommittedReceipt(SQLHDBC db,const Operation& operation,
                            std::vector<std::uint8_t>& after,
                            const WarExpLedger& afterLedger,
                            std::uint32_t afterTickets) noexcept {
    Statement q(db);
    if(!q.Prepare(
      "SELECT 1 FROM dbo.cabal_diamond_v291_rank_receipt AS r WITH (HOLDLOCK) "
      "WHERE r.UserNum=? AND r.ExpectedRevision=? AND r.CharacterIdx=? "
      "AND r.IntentId=? AND r.AppliedRevision=? AND r.AfterWarExp=? "
      "AND r.AfterTicketUnits=? "
      "AND r.AfterInventoryHash=HASHBYTES('SHA2_256',?) "
      "AND EXISTS (SELECT 1 FROM dbo.cabal_WarExp_Table AS w WITH (HOLDLOCK) "
      "WHERE w.CharacterIdx=r.CharacterIdx AND w.WarExp=? "
      "AND w.WarExpEarn=? AND w.WarExpUsed=?) "
      "AND EXISTS (SELECT 1 FROM dbo.cabal_Inventory_table AS i WITH (HOLDLOCK) "
      "WHERE i.CharacterIdx=r.CharacterIdx AND i.Data=?) "
      "AND EXISTS (SELECT 1 FROM dbo.cabal_diamond_v291_rank_state AS s WITH (HOLDLOCK) "
      "WHERE s.UserNum=r.UserNum AND s.CharacterIdx=r.CharacterIdx "
      "AND s.BadgeGrade=2 AND s.Revision=r.AppliedRevision)"))return false;
    SQLINTEGER user=static_cast<SQLINTEGER>(operation.userNum);
    SQLINTEGER rev=static_cast<SQLINTEGER>(operation.expectedRevision);
    SQLINTEGER chr=static_cast<SQLINTEGER>(operation.characterIdx);
    SQLBIGINT intent=static_cast<SQLBIGINT>(operation.durableIntent);
    SQLINTEGER nextRev=static_cast<SQLINTEGER>(operation.appliedRevision);
    SQLBIGINT wexp=static_cast<SQLBIGINT>(afterLedger.current);
    SQLBIGINT earned=static_cast<SQLBIGINT>(afterLedger.earned);
    SQLBIGINT used=static_cast<SQLBIGINT>(afterLedger.used);
    SQLINTEGER count=static_cast<SQLINTEGER>(afterTickets);
    SQLLEN afterLen=0,inventoryLen=0;
    if(!q.I32(1,user)||!q.I32(2,rev)||!q.I32(3,chr)||
       !q.I64(4,intent)||!q.I32(5,nextRev)||!q.I64(6,wexp)||
       !q.I32(7,count)||!q.Binary(8,after,afterLen)||
       !q.I64(9,wexp)||!q.I64(10,earned)||!q.I64(11,used)||
       !q.Binary(12,after,inventoryLen)||!q.Run())
        return false;
    SQLINTEGER found=0;
    return q.FetchI32(found) && found==1;
}
// DO NOT log credentials, serials, GameData or DB diagnostics.
}
AtomicCommitOutcome CommitRealGameDataServer01(
    void* trustedContext,const void* userCtx,
    const AtomicGradeUpRequest& request) noexcept {
    AtomicCommitOutcome rejected{};
    if(!trustedContext || !userCtx)return rejected;
    auto& ctx=*static_cast<RealServer01OdbcContext*>(trustedContext);
    if(!ctx.verifiedRestorableTestClone ||
       !ctx.driverConfiguredForExactServer01 ||
       !ctx.ownerLockStillHeld ||
       !ctx.independentWarExpAccountingVerified ||
       !ctx.actualDbOwnerRankRowProvisioned || ctx.committedRankUp || ctx.recoveryRankUp ||
       ctx.attestedWorldUserCtx!=userCtx ||
       ctx.attestedUserNum!=request.userNum ||
       ctx.attestedCharacterIdx!=request.characterIdx ||
       ctx.attestedSessionGeneration!=request.sessionGeneration ||
       ctx.proof.userNum!=request.userNum ||
       ctx.proof.characterIdx!=request.characterIdx ||
       request.durableIntentId==0 ||
       request.durableIntentId>static_cast<std::uint64_t>(LLONG_MAX) ||
       request.expectedBefore.revision>static_cast<std::uint32_t>(INT_MAX-2) ||
       request.intendedAfter.revision!=request.expectedBefore.revision+1 ||
       request.expectedBefore.wexp<30000 ||
       request.expectedBefore.wexp>static_cast<std::uint64_t>(LLONG_MAX) ||
       request.intendedAfter.wexp!=request.expectedBefore.wexp-30000 ||
       request.expectedBefore.tickets>static_cast<std::uint32_t>(INT_MAX) ||
       request.intendedAfter.tickets>static_cast<std::uint32_t>(INT_MAX) ||
       ctx.warExpEarnBefore<0 || ctx.warExpUsedBefore<0 ||
       ctx.inventoryBefore.empty() ||
       ctx.inventoryBefore.size()>15360)
        return rejected;

    const auto ledger=PlanWarExpDebit(
        {static_cast<std::int64_t>(request.expectedBefore.wexp),
         ctx.warExpEarnBefore,ctx.warExpUsedBefore},30000);
    if(!ledger.valid || ledger.after.current!=
       static_cast<std::int64_t>(request.intendedAfter.wexp))return rejected;

    if(request.selectedTicketDebit.status!=
       diamond_v291::gradeup0bda::SelectionVerdict::ExactDebitPlan ||
       request.selectedTicketDebit.exactPlannedDebit!=100 ||
       ctx.selectedSlots.size()!=request.selectedTicketDebit.selectedCount)
        return rejected;

    const auto staged=diamond_v291::inventory::StageVerifiedB0SelectedDebit100(
        ctx.inventoryBefore.data(),ctx.inventoryBefore.size(),
        request.selectedTicketDebit,ctx.selectedSlots.data(),
        ctx.selectedSlots.size(),ctx.proof);
    if(staged.verdict!=diamond_v291::inventory::B0SelectedDebitVerdict::PreparedClone ||
       staged.allTicketUnitsBefore!=request.expectedBefore.tickets ||
       staged.allTicketUnitsAfter!=request.intendedAfter.tickets ||
       staged.proposedGameData.size()>15360)
        return rejected;

    // Allocate/copy completion storage BEFORE attempting SQL. Once SQL may
    // have committed, an allocation failure must never destroy the evidence.
    std::unique_ptr<RankUpCommitRecord> record;
    try {
        record=std::make_unique<RankUpCommitRecord>();
        auto& op=record->operation;
        op.durableIntent=request.durableIntentId;
        op.userNum=request.userNum;op.characterIdx=request.characterIdx;
        op.expectedRevision=request.expectedBefore.revision;
        op.appliedRevision=request.intendedAfter.revision;
        op.command=1;op.newBadgeGrade=2;
        op.beforeWexp={static_cast<std::int64_t>(request.expectedBefore.wexp),
                      ctx.warExpEarnBefore,ctx.warExpUsedBefore};
        op.afterWexp=ledger.after;
        op.newTickets=request.intendedAfter.tickets;
        record->sessionGeneration=request.sessionGeneration;
        record->inventoryBefore=ctx.inventoryBefore;
        record->inventoryAfter=staged.proposedGameData;
        record->selectedSlots=ctx.selectedSlots;
        record->ticketDebit=request.selectedTicketDebit;
    }catch(...){return rejected;}

    // Only the existing Server01 clone procedure may perform any mutation.
    // It must include CAS checks on actual Inventory/WarExp rows and
    // uniquely commit the grade and receipt in one serializable transaction.
    Connection conn;
    if(!conn.Open(ctx.odbcConnectionString) ||
       !VerifiedServer01Database(conn.dbc))return rejected;

    Statement proc(conn.dbc);
    if(!proc.Prepare(
      "DECLARE @Outcome int; "
      "EXEC dbo.cabal_sp_diamond_v291_atomic_rankup "
      "@UserNum=?,@CharacterIdx=?,@IntentId=?,@ExpectedRevision=?,"
      "@InventoryBefore=?,@InventoryAfter=?,@WarExpBefore=?,"
      "@WarExpAfter=?,@WarExpEarnBefore=?,@WarExpUsedBefore=?,"
      "@VerifiedTicketUnitsBefore=?,@VerifiedTicketUnitsAfter=?,"
      "@Outcome=@Outcome OUTPUT; SELECT @Outcome;"))
        return rejected;
    SQLINTEGER user=static_cast<SQLINTEGER>(request.userNum);
    SQLINTEGER chr=static_cast<SQLINTEGER>(request.characterIdx);
    SQLBIGINT intent=static_cast<SQLBIGINT>(request.durableIntentId);
    SQLINTEGER revision=static_cast<SQLINTEGER>(request.expectedBefore.revision);
    // The owned images remain alive in recoveryRankUp through execute and readback.
    auto& before=record->inventoryBefore;
    auto& after=record->inventoryAfter;
    SQLLEN beforeLen=0,afterLen=0;
    SQLBIGINT oldWexp=static_cast<SQLBIGINT>(request.expectedBefore.wexp);
    SQLBIGINT newWexp=static_cast<SQLBIGINT>(request.intendedAfter.wexp);
    SQLBIGINT earned=static_cast<SQLBIGINT>(ctx.warExpEarnBefore);
    SQLBIGINT used=static_cast<SQLBIGINT>(ctx.warExpUsedBefore);
    SQLINTEGER beforeTicket=static_cast<SQLINTEGER>(staged.allTicketUnitsBefore);
    SQLINTEGER afterTicket=static_cast<SQLINTEGER>(staged.allTicketUnitsAfter);
    if(!proc.I32(1,user)||!proc.I32(2,chr)||!proc.I64(3,intent)||
       !proc.I32(4,revision)||!proc.Binary(5,before,beforeLen)||
       !proc.Binary(6,after,afterLen)||!proc.I64(7,oldWexp)||
       !proc.I64(8,newWexp)||!proc.I64(9,earned)||!proc.I64(10,used)||
       !proc.I32(11,beforeTicket)||!proc.I32(12,afterTicket))
        return rejected;

    // Any error AFTER this mutation attempt is ambiguous: SQL Server
    // could have committed before the ODBC reply was lost. Never retry.
    ctx.recoveryRankUp=std::move(record);
    if(!proc.Run())return {AtomicCommitState::InDoubtRecoveryRequired,0,0};
    SQLINTEGER outcome=0;
    bool gotResult=false;
    for(unsigned i=0;i<8 && !gotResult;++i) {
        const SQLRETURN fetch=SQLFetch(proc.h);
        if(Ok(fetch)) {
            SQLLEN length=0;
            if(!Ok(SQLGetData(proc.h,1,SQL_C_SLONG,&outcome,
                              sizeof(outcome),&length)) ||
               length==SQL_NULL_DATA)
                return {AtomicCommitState::InDoubtRecoveryRequired,0,0};
            gotResult=true;
            break;
        }
        if(fetch!=SQL_NO_DATA)return {AtomicCommitState::InDoubtRecoveryRequired,0,0};
        const SQLRETURN more=SQLMoreResults(proc.h);
        if(more==SQL_NO_DATA)break;
        if(!Ok(more))return {AtomicCommitState::InDoubtRecoveryRequired,0,0};
    }
    if(!gotResult || (outcome!=1 && outcome!=2))
        return {AtomicCommitState::InDoubtRecoveryRequired,0,0};
    // Free the executing procedure's statement before querying committed
    // receipt (some SQL drivers reject concurrent active statements).
    if(!Ok(SQLCloseCursor(proc.h)))
        return {AtomicCommitState::InDoubtRecoveryRequired,0,0};

    if(!VerifyCommittedReceipt(conn.dbc,ctx.recoveryRankUp->operation,after,ledger.after,
                               static_cast<std::uint32_t>(afterTicket)))
        return {AtomicCommitState::InDoubtRecoveryRequired,0,0};
    ctx.committedRankUp=std::move(ctx.recoveryRankUp);
    return {AtomicCommitState::CommittedNeedsIndependentSaveVerification,
            request.durableIntentId,request.intendedAfter.revision};
}
bool VerifySavedRankUpServer01(const std::string& connectionString,
                              const RankUpCommitRecord& committed) noexcept {
    // The barrier validates the complete operation, including bigint bounds.
    DiamondWorldSaveBarrier shape;
    if(!committed.sessionGeneration ||
       committed.operation.command!=1 ||
       shape.Begin(committed.operation,true,true)!=Verdict::Ok ||
       committed.operation.userNum>static_cast<std::uint32_t>(INT_MAX) ||
       committed.operation.characterIdx>static_cast<std::uint32_t>(INT_MAX) ||
       committed.operation.durableIntent>static_cast<std::uint64_t>(LLONG_MAX) ||
       committed.operation.appliedRevision>static_cast<std::uint32_t>(INT_MAX) ||
       committed.operation.newTickets>static_cast<std::uint32_t>(INT_MAX) ||
       committed.inventoryAfter.empty() || committed.inventoryAfter.size()>15360 ||
       committed.inventoryAfter.size()%30!=0)return false;
    try {
        auto after=committed.inventoryAfter;
        Connection connection;
        return connection.Open(connectionString) &&
               VerifiedServer01Database(connection.dbc) &&
               VerifyCommittedReceipt(connection.dbc,committed.operation,after,
                   committed.operation.afterWexp,committed.operation.newTickets);
    }catch(...){return false;}
}
} // namespace diamond_v291::real_gamedata
