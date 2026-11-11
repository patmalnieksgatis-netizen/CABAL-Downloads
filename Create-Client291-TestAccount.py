"""Create one explicitly requested fresh account on the pinned test VM.

Uses the existing native registration/authentication procedures. Password comes
from a task-specific environment variable; it is never written to disk/logs.
No existing account, character, inventory, pet or service is changed.
"""
import argparse
import hashlib
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys

VM_UUID = '7632fb78-37a0-f645-97c0-dc322c50b002'
REGISTER_SHA = 'BDE8C714D3ACC2DF4E14CCB5830B405E5085A9226BA2F18DFCACEA9CD736088C'
AUTH_SHA = 'AAD33D532020160549376448B6CA1A97C521787F8294D60549B6614273A83B9A'

def query(username, password, userkey):
    if not re.fullmatch(r'[A-Za-z0-9]{4,16}', username) or not re.fullmatch(r'[A-Za-z0-9]{8,16}', password):
        raise ValueError('TEST_ACCOUNT_FORMAT')
    if not re.fullmatch(r'[0-9a-f]{32}', userkey):
        raise ValueError('TEST_ACCOUNT_KEY_FORMAT')
    return f"""SET NOCOUNT ON;
SET XACT_ABORT ON;
SET LOCK_TIMEOUT 5000;
IF DB_NAME()<>N'Account' THROW 51000,'WRONG_ACCOUNT_DATABASE',1;
IF NOT EXISTS(SELECT 1 FROM sys.sql_modules
 WHERE object_id=OBJECT_ID(N'dbo.cabal_tool_registerAccount')
 AND HASHBYTES('SHA2_256',CONVERT(varbinary(max),definition))=0x{REGISTER_SHA})
 THROW 51000,'REGISTER_PROCEDURE_CHANGED_NO_ACCOUNT_CREATED',1;
IF NOT EXISTS(SELECT 1 FROM sys.sql_modules
 WHERE object_id=OBJECT_ID(N'dbo.cabal_sp_auth_netcafe_check')
 AND HASHBYTES('SHA2_256',CONVERT(varbinary(max),definition))=0x{AUTH_SHA})
 THROW 51000,'AUTH_PROCEDURE_CHANGED_NO_ACCOUNT_CREATED',1;
IF OBJECT_ID(N'Server01.dbo.cabal_character_table',N'U') IS NULL
 THROW 51000,'CHARACTER_TABLE_NOT_FOUND_NO_ACCOUNT_CREATED',1;
BEGIN TRY
 BEGIN TRAN;
 IF EXISTS(SELECT 1 FROM dbo.cabal_auth_table WITH(UPDLOCK,HOLDLOCK)
  WHERE ID COLLATE Latin1_General_100_CI_AS=N'{username}')
  THROW 51000,'ACCOUNT_ALREADY_EXISTS_NOT_CHANGED',1;
 EXEC dbo.cabal_tool_registerAccount @id='{username}',@password='{password}',
  @email='{username}@local-test.invalid',@name='{username}',
  @userkey='{userkey}',@refercode='';
 DECLARE @number int,@matches int,@verified int,@result int;
 SELECT @number=MIN(UserNum),@matches=COUNT(*) FROM dbo.cabal_auth_table
 WHERE ID COLLATE Latin1_General_100_CI_AS=N'{username}';
 IF @matches<>1 OR @number IS NULL THROW 51000,'NEW_ACCOUNT_INSERT_FAILED',1;
 UPDATE dbo.cabal_auth_table SET AuthType=1 WHERE UserNum=@number AND [Login]=0;
 IF @@ROWCOUNT<>1 THROW 51000,'NEW_ACCOUNT_ACTIVATION_FAILED',1;
 EXEC dbo.cabal_sp_auth_netcafe_check @ID='{username}',@Password='{password}',
  @IP='127.0.0.1',@Extra=NULL,@UserNum=@verified OUTPUT,@AuthResult=@result OUTPUT;
 IF @result IS NULL OR @result<>32 OR @verified IS NULL OR @verified<>@number
  THROW 51000,'NATIVE_PASSWORD_CHECK_FAILED',1;
 -- Password verification must not leave the newly created account logged in.
 UPDATE dbo.cabal_auth_table SET [Login]=0 WHERE UserNum=@number;
 IF @@ROWCOUNT<>1 THROW 51000,'NEW_ACCOUNT_LOGIN_STATE_FAILED',1;
 IF NOT EXISTS(SELECT 1 FROM dbo.cabal_charge_auth WHERE usernum=@number AND expiredate>GETDATE())
  THROW 51000,'NEW_ACCOUNT_ACCESS_MISSING',1;
 IF EXISTS(SELECT 1 FROM Server01.dbo.cabal_character_table WHERE CharacterIdx/16=@number)
  THROW 51000,'NEW_ACCOUNT_HAS_CHARACTERS_NOT_CLEAN',1;
 IF @@TRANCOUNT<>1 THROW 51000,'REGISTRATION_TRANSACTION_STATE_CHANGED',1;
 COMMIT;
 PRINT 'FRESH_TEST_ACCOUNT_COMMITTED_PASSWORD_CHECK_OK_CHARACTERS_0';
END TRY
BEGIN CATCH
 IF XACT_STATE()<>0 ROLLBACK;
 THROW;
END CATCH;
"""

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username',required=True)
    args=parser.parse_args()
    password=os.environ.pop('CABAL_TEST_ACCOUNT_PASSWORD','')
    # Validate before any remote/container or SQL action.
    key=secrets.token_hex(16)
    sql=query(args.username,password,key)
    if os.geteuid()!=0 or Path('/sys/class/dmi/id/product_uuid').read_text().strip().lower()!=VM_UUID:
        raise SystemExit('WRONG_TEST_VM_OR_ROOT_REQUIRED_NO_SQL_ACTION')
    shell='''set +x
export SQLCMDPASSWORD="${MSSQL_SA_PASSWORD:-${SA_PASSWORD:-}}"
[ -n "$SQLCMDPASSWORD" ] || { echo SQL_PASSWORD_ENV_MISSING; exit 2; }
tool=/opt/mssql-tools18/bin/sqlcmd
[ -x "$tool" ] || tool=/opt/mssql-tools/bin/sqlcmd
exec "$tool" -S localhost -U sa -N -C -d Account -b -l 5 -t 30 -h -1 -W -i /dev/stdin'''
    result=subprocess.run(['docker','exec','-i','sql_main','sh','-ec',shell],
        input=sql.encode('ascii'),capture_output=True,timeout=45)
    marker=b'FRESH_TEST_ACCOUNT_COMMITTED_PASSWORD_CHECK_OK_CHARACTERS_0'
    if result.returncode or marker not in result.stdout:
        text='\n'.join(b.decode('utf-16' if b[:2] in (b'\xff\xfe',b'\xfe\xff') else 'utf-8',errors='replace') for b in (result.stdout,result.stderr) if b)
        for private in (password,key):
            if private:text=text.replace(private,'[REDACTED]')
        print(text[-3000:],flush=True)
        raise SystemExit('ACCOUNT_CREATE_NOT_CONFIRMED')
    print('ACCOUNT_CREATED='+args.username+'; PASSWORD_CHECK=OK; CHARACTERS=0; TEST_VM_ONLY',flush=True)

if __name__=='__main__':
    main()
