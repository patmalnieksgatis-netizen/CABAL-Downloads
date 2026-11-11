"""Explicit one-time Kathleen level1/EXP0 reset on the pinned isolated VM.
Only LEV and EXP are updated. Original level/EXP are retained in a SQL journal.
"""
import os
from pathlib import Path
import subprocess
import sys
VM_UUID='7632fb78-37a0-f645-97c0-dc322c50b002'
SQL="SET NOCOUNT ON; SET XACT_ABORT ON; SET LOCK_TIMEOUT 5000;\nIF DB_NAME()<>N'Server01' THROW 51000,'WRONG_GAME_DATABASE',1;\nBEGIN TRY\n BEGIN TRAN;\n DECLARE @lock int,@user int,@character int,@count int;\n EXEC @lock=sys.sp_getapplock @Resource='Client291:Kathleen:Level1:20261111',\n  @LockMode='Exclusive',@LockOwner='Transaction',@LockTimeout=5000;\n IF @lock IS NULL OR @lock<0 THROW 51000,'KATHLEEN_RESET_LOCK_FAILED',1;\n SELECT @user=MIN(UserNum),@count=COUNT(*) FROM Account.dbo.cabal_auth_table WITH(UPDLOCK,HOLDLOCK)\n  WHERE ID COLLATE Latin1_General_100_BIN2='wolverine';\n IF @count<>1 OR @user IS NULL THROW 51001,'KATHLEEN_ACCOUNT_IDENTITY_MISMATCH',1;\n SELECT @character=MIN(CharacterIdx),@count=COUNT(*) FROM dbo.cabal_character_table WITH(UPDLOCK,HOLDLOCK)\n  WHERE CharacterIdx/16=@user AND Name COLLATE Latin1_General_100_BIN2='Kathleen';\n IF @count<>1 OR @character IS NULL THROW 51001,'KATHLEEN_CHARACTER_IDENTITY_MISMATCH',1;\n IF EXISTS(SELECT 1 FROM Account.dbo.cabal_auth_table WITH(UPDLOCK,HOLDLOCK)\n  WHERE UserNum=@user AND ([Login] IS NULL OR [Login]<>0))\n  OR EXISTS(SELECT 1 FROM dbo.cabal_character_table WITH(UPDLOCK,HOLDLOCK)\n  WHERE CharacterIdx/16=@user AND ([Login] IS NULL OR [Login]<>0))\n  THROW 51002,'CLOSE_GAME_LOG_OUT_WOLVERINE_FIRST; NOTHING_CHANGED',1;\n IF OBJECT_ID('dbo.Client291_KathleenLevel1_20261111','U') IS NULL\n  CREATE TABLE dbo.Client291_KathleenLevel1_20261111(\n   CharacterIdx int NOT NULL PRIMARY KEY,UserNum int NOT NULL,\n   BeforeLevel int NOT NULL,BeforeExp bigint NOT NULL,\n   AfterLevel int NOT NULL,AfterExp bigint NOT NULL,\n   CreatedUTC datetime2 NOT NULL DEFAULT SYSUTCDATETIME());\n IF EXISTS(SELECT 1 FROM dbo.Client291_KathleenLevel1_20261111 WITH(UPDLOCK,HOLDLOCK) WHERE CharacterIdx=@character)\n BEGIN\n  IF NOT EXISTS(SELECT 1 FROM dbo.Client291_KathleenLevel1_20261111\n   WHERE CharacterIdx=@character AND UserNum=@user AND AfterLevel=1 AND AfterExp=0)\n   THROW 51003,'KATHLEEN_RESET_RECEIPT_CONFLICT',1;\n  COMMIT;\n  PRINT 'KATHLEEN_LEVEL1_ALREADY_APPLIED; NOT_RESET_AGAIN';\n END\n ELSE\n BEGIN\n  DECLARE @beforeLevel int,@beforeExp bigint,@beforeAlz bigint,@beforeReserved bigint;\n  SELECT @beforeLevel=LEV,@beforeExp=EXP,@beforeAlz=Alz,@beforeReserved=Reserved1\n   FROM dbo.cabal_character_table WITH(UPDLOCK,HOLDLOCK) WHERE CharacterIdx=@character;\n  IF @beforeLevel IS NULL OR @beforeLevel<1 OR @beforeExp IS NULL OR @beforeExp<0\n   THROW 51004,'KATHLEEN_CURRENT_LEVEL_EXP_INVALID',1;\n  INSERT dbo.Client291_KathleenLevel1_20261111\n   (CharacterIdx,UserNum,BeforeLevel,BeforeExp,AfterLevel,AfterExp)\n   VALUES(@character,@user,@beforeLevel,@beforeExp,1,0);\n  UPDATE dbo.cabal_character_table SET LEV=1,EXP=0 WHERE CharacterIdx=@character;\n  IF @@ROWCOUNT<>1 THROW 51005,'KATHLEEN_RESET_ROW_COUNT_FAILED',1;\n  IF NOT EXISTS(SELECT 1 FROM dbo.cabal_character_table WHERE CharacterIdx=@character\n   AND LEV=1 AND EXP=0 AND (Alz=@beforeAlz OR (Alz IS NULL AND @beforeAlz IS NULL))\n   AND (Reserved1=@beforeReserved OR (Reserved1 IS NULL AND @beforeReserved IS NULL)))\n   THROW 51006,'KATHLEEN_RESET_READBACK_FAILED',1;\n  COMMIT;\n  PRINT 'KATHLEEN_LEVEL1_APPLIED; LEVEL=1; EXP=0';\n END;\n SELECT CONCAT('KATHLEEN_LEVEL=',LEV,'; EXP=',EXP,'; ALZ=',Alz)\n  FROM dbo.cabal_character_table WHERE CharacterIdx=@character;\nEND TRY\nBEGIN CATCH\n IF XACT_STATE()<>0 ROLLBACK;\n THROW;\nEND CATCH;\n"
def main():
    if sys.argv[1:]!=['--apply']:
        raise SystemExit('EXPLICIT_APPLY_REQUIRED; NOTHING_CHANGED')
    if os.geteuid()!=0 or Path('/sys/class/dmi/id/product_uuid').read_text().strip().lower()!=VM_UUID:
        raise SystemExit('WRONG_TEST_VM_OR_ROOT_REQUIRED; NOTHING_CHANGED')
    shell='''set +x
export SQLCMDPASSWORD="${MSSQL_SA_PASSWORD:-${SA_PASSWORD:-}}"
[ -n "$SQLCMDPASSWORD" ] || exit 2
tool=/opt/mssql-tools18/bin/sqlcmd
[ -x "$tool" ] || tool=/opt/mssql-tools/bin/sqlcmd
exec "$tool" -S localhost -U sa -N -C -d Server01 -b -l 5 -t 30 -h -1 -W -w 65535 -i /dev/stdin
'''
    p=subprocess.run(['docker','exec','-i','sql_main','sh','-ec',shell],input=SQL.encode('ascii'),capture_output=True,timeout=50)
    raw=p.stdout+p.stderr
    output=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig',errors='replace')
    for line in output.splitlines():
        if line.startswith(('KATHLEEN_','Msg ')) or any(m in line for m in ('NOTHING_CHANGED','FIRST','Invalid column','Invalid object')):
            print(line[:500],flush=True)
    if p.returncode or not any(m in output for m in ('KATHLEEN_LEVEL1_APPLIED;','KATHLEEN_LEVEL1_ALREADY_APPLIED;')):
        raise SystemExit('KATHLEEN_RESET_NOT_CONFIRMED; KEEP_OUTPUT')
if __name__=='__main__':main()
