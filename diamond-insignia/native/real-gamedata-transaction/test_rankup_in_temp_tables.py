#!/usr/bin/env python3
"""Run the actual rank-up procedure body against connection-local SQL tables.

This is a database-engine test, not installation or a real character upgrade.
The wrapper supplies SOURCE_SQL before this module. Only #temporary tables
and a #temporary stored procedure are created; they vanish on disconnect.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import secrets
import subprocess

TABLES=('cabal_diamond_v291_clone_approval','cabal_diamond_v291_rank_receipt',
        'cabal_diamond_v291_rank_state','cabal_Inventory_table','cabal_WarExp_Table')


def build_sql(source, namespace):
    if not re.fullmatch(r'[0-9a-f]{16}',namespace):
        raise ValueError('TEST_NAMESPACE')
    marker='CREATE OR ALTER PROCEDURE dbo.cabal_sp_diamond_v291_atomic_rankup'
    if source.count(marker)!=1:
        raise ValueError('EXPECTED_ONE_RANKUP_PROCEDURE')
    procedure='CREATE PROCEDURE #diamond_rankup'+source.split(marker,1)[1]
    procedure=re.split(r'(?im)^GO[ \t]*\r?$',procedure,maxsplit=1)[0]
    for table in TABLES:
        procedure=procedure.replace('dbo.'+table,'#'+table)
    if procedure.count("N'DiamondV291:User:'")!=1:
        raise ValueError('EXPECTED_ORIGINAL_APPLOCK_NAMESPACE')
    procedure=procedure.replace("N'DiamondV291:User:'", "N'DiamondTempTest:"+namespace+":User:'")
    code=re.sub(r'--[^\r\n]*','',procedure)
    if re.search(r'(?i)\bdbo\s*\.',code):
        raise ValueError('NON_TEMP_SCHEMA_REFERENCE')
    for match in re.finditer(r'(?i)\b(?:FROM|UPDATE|INTO)\s+([^\s(]+)',code):
        if match[1] not in {'#'+t for t in TABLES}:
            raise ValueError('NON_TEMP_TABLE_REFERENCE')
    before=(33554961).to_bytes(8,'little')+(901).to_bytes(8,'little')+(999).to_bytes(8,'little')+(47).to_bytes(2,'little')+bytes(4)
    after=before[:16]+(899).to_bytes(8,'little')+before[24:]
    prelude='''USE [Server01];
SET NOCOUNT ON;
IF DB_NAME()<>N'Server01' THROW 51100,N'WRONG_TEST_DATABASE',1;
CREATE TABLE #cabal_diamond_v291_clone_approval(ApprovalId int,CloneVerified bit,ChangesAllowed bit);
INSERT #cabal_diamond_v291_clone_approval VALUES(1,1,1);
CREATE TABLE #cabal_Inventory_table(CharacterIdx int PRIMARY KEY,Data varbinary(max));
CREATE TABLE #cabal_WarExp_Table(CharacterIdx int PRIMARY KEY,WarExp bigint NOT NULL,WarExpEarn bigint NOT NULL,WarExpUsed bigint NOT NULL);
CREATE TABLE #cabal_diamond_v291_rank_state(UserNum int PRIMARY KEY,CharacterIdx int UNIQUE,BadgeGrade tinyint,Revision int,ModifiedAt datetime2(3));
CREATE TABLE #cabal_diamond_v291_rank_receipt(
 UserNum int NOT NULL,CharacterIdx int NOT NULL,IntentId bigint NOT NULL,ExpectedRevision int NOT NULL,AppliedRevision int NOT NULL,
 BeforeWarExp bigint,AfterWarExp bigint,BeforeTicketUnits int,AfterTicketUnits int,
 AfterInventoryHash binary(32),CommittedAt datetime2(3) DEFAULT SYSUTCDATETIME(),
 PRIMARY KEY(UserNum,ExpectedRevision),UNIQUE(UserNum,IntentId),
 CHECK(IntentId<>998878));
GO
'''
    seed='''DELETE FROM #cabal_diamond_v291_rank_receipt;
DELETE FROM #cabal_diamond_v291_rank_state;
DELETE FROM #cabal_Inventory_table;
DELETE FROM #cabal_WarExp_Table;
INSERT #cabal_Inventory_table VALUES(24055,@before);
INSERT #cabal_WarExp_Table VALUES(24055,35000,100000,7);
INSERT #cabal_diamond_v291_rank_state VALUES(5005,24055,1,5,SYSUTCDATETIME());
'''
    call='''EXEC #diamond_rankup @UserNum=5005,@CharacterIdx=24055,@IntentId={intent},
 @ExpectedRevision=5,@InventoryBefore=@before,@InventoryAfter=@after,
 @WarExpBefore=35000,@WarExpAfter=5000,@WarExpEarnBefore=100000,
 @WarExpUsedBefore={used},@VerifiedTicketUnitsBefore=999,
 @VerifiedTicketUnitsAfter=899,@Outcome=@result OUTPUT;
'''
    unchanged='''IF NOT EXISTS(SELECT 1 FROM #cabal_Inventory_table WHERE Data=@before)
 OR NOT EXISTS(SELECT 1 FROM #cabal_WarExp_Table WHERE WarExp=35000 AND WarExpEarn=100000 AND WarExpUsed=7)
 OR NOT EXISTS(SELECT 1 FROM #cabal_diamond_v291_rank_state WHERE BadgeGrade=1 AND Revision=5)
 OR EXISTS(SELECT 1 FROM #cabal_diamond_v291_rank_receipt)
 THROW 51101,N'ROLLBACK_DID_NOT_RESTORE_ALL_TEMP_ROWS',1;
'''
    checks=(f'DECLARE @before varbinary(max)=0x{before.hex()},@after varbinary(max)=0x{after.hex()},@result int,@error int;\n'+seed+
      call.format(intent=998877,used=7)+'''IF @result<>1
 OR NOT EXISTS(SELECT 1 FROM #cabal_Inventory_table WHERE Data=@after)
 OR NOT EXISTS(SELECT 1 FROM #cabal_WarExp_Table WHERE WarExp=5000 AND WarExpEarn=100000 AND WarExpUsed=30007)
 OR NOT EXISTS(SELECT 1 FROM #cabal_diamond_v291_rank_state WHERE BadgeGrade=2 AND Revision=6)
 OR (SELECT COUNT(*) FROM #cabal_diamond_v291_rank_receipt)<>1
 THROW 51102,N'RANKUP_RESULT_OR_COUNTERS_DIFFER',1;
PRINT 'DIAMOND_TEMP_SQL_COMMIT=PASS';
'''+call.format(intent=998877,used=7)+'''IF @result<>2
 OR NOT EXISTS(SELECT 1 FROM #cabal_WarExp_Table WHERE WarExp=5000 AND WarExpUsed=30007)
 OR (SELECT COUNT(*) FROM #cabal_diamond_v291_rank_receipt)<>1
 THROW 51103,N'REPLAY_CHANGED_COUNTERS_OR_RECEIPT',1;
PRINT 'DIAMOND_TEMP_SQL_REPLAY=PASS';
'''+seed+'''SET @error=0;
BEGIN TRY
'''+call.format(intent=998878,used=7)+'''END TRY
BEGIN CATCH SET @error=ERROR_NUMBER(); END CATCH;
IF @error<>547 THROW 51104,N'EXPECTED_FINAL_RECEIPT_FAILURE',1;
'''+unchanged+'''PRINT 'DIAMOND_TEMP_SQL_ATOMIC_ROLLBACK=PASS';
SET @error=0;
BEGIN TRY
'''+call.format(intent=998877,used=9223372036854745808)+'''END TRY
BEGIN CATCH SET @error=ERROR_NUMBER(); END CATCH;
IF @error<>51008 THROW 51105,N'EXPECTED_SPENT_COUNTER_OVERFLOW_REJECTION',1;
'''+unchanged+'''PRINT 'DIAMOND_TEMP_SQL_OVERFLOW=PASS';
SET @error=0;
BEGIN TRY
'''+call.format(intent=998877,used=8)+'''END TRY
BEGIN CATCH SET @error=ERROR_NUMBER(); END CATCH;
IF @error<>51013 THROW 51106,N'EXPECTED_STALE_LEDGER_REJECTION',1;
'''+unchanged+'''PRINT 'DIAMOND_TEMP_SQL_STALE_COUNTERS=PASS';
IF @@TRANCOUNT<>0 THROW 51107,N'OPEN_TRANSACTION_AFTER_TEST',1;
PRINT 'DIAMOND_TEMP_SQL_TEST=PASS';
''')
    return prelude+procedure+'\nGO\n'+checks


def run_local_engine(source):
    # The password never leaves sql_main; reuse its existing environment.
    result=subprocess.run(['docker','inspect','sql_main','--format','{{.State.Running}}'],
                          capture_output=True,text=True,timeout=15)
    if result.returncode or result.stdout.strip()!='true':
        raise RuntimeError('SQL_CONTAINER_NOT_RUNNING')
    sql=build_sql(source,secrets.token_hex(8))
    shell=r'''
set -eu
diamond_sqlcmd=''
for diamond_candidate in /opt/mssql-tools18/bin/sqlcmd /opt/mssql-tools/bin/sqlcmd /usr/bin/sqlcmd; do
 if [ -x "$diamond_candidate" ]; then diamond_sqlcmd="$diamond_candidate"; break; fi
done
if [ -z "$diamond_sqlcmd" ]; then exit 23; fi
export SQLCMDPASSWORD="${MSSQL_SA_PASSWORD:-${SA_PASSWORD:-}}"
if [ -z "$SQLCMDPASSWORD" ]; then exit 24; fi
exec "$diamond_sqlcmd" -S localhost -U sa -d Server01 -C -b -V 16 -r 1 -h -1 -W -l 8 -t 30 -i /dev/stdin
'''
    result=subprocess.run(['docker','exec','-i','sql_main','sh','-c',shell],
                          input=sql,capture_output=True,text=True,timeout=90)
    if result.returncode==23:raise RuntimeError('SQLCMD_NOT_AVAILABLE')
    if result.returncode==24:raise RuntimeError('SQL_CONTAINER_CREDENTIAL_BINDING_UNAVAILABLE')
    text=result.stdout+'\n'+result.stderr
    expected=('DIAMOND_TEMP_SQL_COMMIT=PASS','DIAMOND_TEMP_SQL_REPLAY=PASS',
              'DIAMOND_TEMP_SQL_ATOMIC_ROLLBACK=PASS','DIAMOND_TEMP_SQL_OVERFLOW=PASS',
              'DIAMOND_TEMP_SQL_STALE_COUNTERS=PASS','DIAMOND_TEMP_SQL_TEST=PASS')
    for marker in expected:
        if marker in text:print(marker)
    if result.returncode or any(marker not in text for marker in expected):
        # SQL diagnostics refer only to synthetic temporary rows. Never expose
        # driver connection arguments or docker inspect output on failure.
        print(text[-3000:])
        raise RuntimeError('TEMP_SQL_ENGINE_TEST_FAILED')
    print(json.dumps({'status':'TEMP_SQL_ENGINE_TEST_PASS','cases':5,
          'procedure_source_sha256':hashlib.sha256(source.encode()).hexdigest(),
          'game_rows_read_or_written':False,'persistent_schema_changed':False,
          'server_restarted':False,'worldsvr_integration_tested':False}))


if __name__=='__main__':
    try:
        if 'SOURCE_SQL' in globals():
            run_local_engine(SOURCE_SQL.decode('utf-8-sig'))
        else:
            p=argparse.ArgumentParser(description=__doc__)
            p.add_argument('--emit-sql',required=True,type=Path)
            a=p.parse_args()
            print(build_sql(a.emit_sql.read_text(encoding='utf-8-sig'),'0123456789abcdef'))
    except (RuntimeError,ValueError,subprocess.TimeoutExpired,KeyError) as error:
        reason=str(error) if isinstance(error,(RuntimeError,ValueError)) else type(error).__name__
        print('DIAMOND_TEMP_SQL_STOPPED='+reason)
        raise SystemExit(2)
