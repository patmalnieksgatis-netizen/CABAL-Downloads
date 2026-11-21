"""Deliver one Golden Relic Lv.1 by native mail to Storm on the test VM."""
import os
from pathlib import Path
import subprocess

SQL = r"""SET NOCOUNT ON;
SET XACT_ABORT ON;
SET LOCK_TIMEOUT 5000;
IF DB_NAME()<>N'Server01' THROW 51000,'WRONG_GAME_DATABASE; NOTHING_SENT',1;
DECLARE @items TABLE(N int PRIMARY KEY,Kind bigint,Opt bigint,Label varchar(40));
INSERT @items VALUES (1,67109013,0,'Golden Relic Lv.1');
BEGIN TRY
 BEGIN TRANSACTION;
 DECLARE @lock int;
 EXEC @lock=sys.sp_getapplock @Resource='Client291_StormMandaratLv1_20261121:Storm',
  @LockMode='Exclusive',@LockOwner='Transaction',@LockTimeout=5000;
 IF @lock IS NULL OR @lock<0 THROW 51000,'STORM_MAIL_LOCK_FAILED',1;
 DECLARE @character int,@matches int;
 SELECT @character=MIN(CharacterIdx),@matches=COUNT(*) FROM dbo.cabal_character_table WITH(UPDLOCK,HOLDLOCK)
  WHERE Name COLLATE Latin1_General_100_BIN2='Storm';
 IF @matches<>1 OR @character IS NULL THROW 51001,'STORM_CHARACTER_IDENTITY_MISMATCH; NOTHING_SENT',1;
 IF HASHBYTES('SHA2_256',CONVERT(varbinary(max),OBJECT_DEFINITION(OBJECT_ID('dbo.cabal_tool_mail_send')))) IS NULL
  OR HASHBYTES('SHA2_256',CONVERT(varbinary(max),OBJECT_DEFINITION(OBJECT_ID('dbo.cabal_tool_mail_send'))))<>
  0xE1ACA240CF50C55C6847A38C202A79712DFC5E3EC31480FD67B479A99111E029
  OR HASHBYTES('SHA2_256',CONVERT(varbinary(max),OBJECT_DEFINITION(OBJECT_ID('dbo.Mail_GetGMType')))) IS NULL
  OR HASHBYTES('SHA2_256',CONVERT(varbinary(max),OBJECT_DEFINITION(OBJECT_ID('dbo.Mail_GetGMType'))))<>
  0xF11A7EF873E57ACC6FC9D5DDDBB7093E2E53745F35DA511659015837D0DCC4E1
  THROW 51002,'NATIVE_MAIL_HELPER_CHANGED; NOTHING_SENT',1;
 IF OBJECT_ID('dbo.Client291_StormMandaratLv1_20261121','U') IS NULL
  CREATE TABLE dbo.Client291_StormMandaratLv1_20261121(
   CharacterIdx int NOT NULL,N int NOT NULL,Kind bigint NOT NULL,Opt bigint NOT NULL,
   MailID int NOT NULL,SentAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
   PRIMARY KEY(CharacterIdx,N));
 IF EXISTS(SELECT 1 FROM dbo.Client291_StormMandaratLv1_20261121 WITH(UPDLOCK,HOLDLOCK) WHERE CharacterIdx=@character)
 BEGIN
  IF (SELECT COUNT(*) FROM dbo.Client291_StormMandaratLv1_20261121 WHERE CharacterIdx=@character)<>1
   OR EXISTS(SELECT N,Kind,Opt FROM @items EXCEPT
   SELECT N,Kind,Opt FROM dbo.Client291_StormMandaratLv1_20261121 WHERE CharacterIdx=@character)
   THROW 51003,'MAIL_GRANT_JOURNAL_DIFFERS; NOTHING_SENT',1;
  COMMIT;
  PRINT 'STORM_TICKET_ALREADY_SENT; NO_DUPLICATES';
  RETURN;
 END;
 DECLARE @n int=1,@kind bigint,@opt bigint,@label varchar(40),@body varchar(512),@id int;
 DECLARE @result TABLE(ID int);
 WHILE @n<=1
 BEGIN
  SELECT @kind=Kind,@opt=Opt,@label=Label FROM @items WHERE N=@n;
  SET @body='Storm Mandarat Lv.1 ticket: '+@label;
  DELETE @result;
  INSERT @result EXEC dbo.cabal_tool_mail_send
   @SenderName='GM',@ReceiverCharIdx=@character,@Title=@label,@Content=@body,
   @Alz=0,@ItemKindIdx=@kind,@ItemOption=@opt,@ItemDurationIdx=0,@ExpirationTime=NULL;
  IF (SELECT COUNT(*) FROM @result)<>1 THROW 51004,'MAIL_RECEIPT_FAILED',1;
  SELECT @id=ID FROM @result;
  IF @id IS NULL OR @id<=0 OR NOT EXISTS(SELECT 1 FROM dbo.cabal_mail_received_table
   WHERE ReceiverCharIdx=@character AND ReceivedMailID=@id AND IsCommitted=1 AND Type=4
   AND ItemKindIdx=@kind AND ItemOption=@opt AND ItemDurationIdx=0
   AND ExpirationTime IS NULL AND SenderName='GM' AND Alz=0 AND IsReceivedItem=0)
   THROW 51005,'MAIL_ATTACHMENT_POSTCHECK_FAILED',1;
  INSERT dbo.Client291_StormMandaratLv1_20261121(CharacterIdx,N,Kind,Opt,MailID)
   VALUES(@character,@n,@kind,@opt,@id);
  SET @n+=1;
 END;
 COMMIT;
 PRINT 'STORM_TICKET_SENT; MAILS1; QUANTITY1; OPEN_MAIL_AND_CLAIM_ATTACHMENTS';
 SELECT CONCAT('STORM_ITEM=',j.N,'; ',i.Label,'; MAIL_ID=',j.MailID) FROM dbo.Client291_StormMandaratLv1_20261121 j
 JOIN @items i ON i.N=j.N WHERE j.CharacterIdx=@character ORDER BY j.N;
END TRY
BEGIN CATCH
 IF @@TRANCOUNT>0 ROLLBACK;
 THROW;
END CATCH;
""".encode("ascii")


def main():
    if os.geteuid() != 0 or Path("/sys/class/dmi/id/product_uuid").read_text().strip().lower() != "7632fb78-37a0-f645-97c0-dc322c50b002":
        raise SystemExit("WRONG_TEST_VM")
    shell='''set +x
export SQLCMDPASSWORD="${MSSQL_SA_PASSWORD:-${SA_PASSWORD:-}}"
[ -n "$SQLCMDPASSWORD" ] || exit 2
tool=/opt/mssql-tools18/bin/sqlcmd
[ -x "$tool" ] || tool=/opt/mssql-tools/bin/sqlcmd
exec "$tool" -S localhost -U sa -N -C -d Server01 -b -l 5 -t 30 -h -1 -W -w 65535 -i /dev/stdin
'''
    p=subprocess.run(['docker','exec','-i','sql_main','sh','-ec',shell],input=SQL,capture_output=True,timeout=50)
    raw = p.stdout + p.stderr
    output = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig", errors="replace")
    print(output.strip())
    if p.returncode or not any(marker in output for marker in ("STORM_TICKET_SENT;", "STORM_TICKET_ALREADY_SENT;")):
        raise SystemExit("MAIL_NOT_CONFIRMED")


if __name__ == "__main__":
    main()
