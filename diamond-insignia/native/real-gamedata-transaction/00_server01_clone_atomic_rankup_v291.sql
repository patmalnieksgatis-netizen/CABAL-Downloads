-- CABAL v291 DIAMOND: first REAL GameData inventory+WarExp+grade-state
-- transaction contract. FOR AN ISOLATED, RESTORABLE Server01 TEST CLONE.
--
-- WARNING: This is NOT a verified game-compatible live handler.
-- - Actual WorldSvr 0BDA handler registration and S2C ABI are missing.
-- - Normal inventory Data row layout and B0 count still need SAME-STACK proof.
-- - WorldSvr in-memory inventory/WarExp must be made consistent with DB
--   under an exclusive owner lease; a later original cmd46/47 must NEVER
--   overwrite these SQL changes from stale in-memory state.
-- - The grade-state table below is a new durable ledger, NOT proof of
--   how the v291 client expects its Diamond rank in native GameData.
-- This script is deliberately DISABLED by default. DO NOT blindly run.
USE [Server01];
GO
DECLARE @ExplicitVerifiedRestorableIsolatedClone bit=0;
IF DB_NAME()<>N'Server01' OR @ExplicitVerifiedRestorableIsolatedClone<>1
    THROW 51001,N'STOP: only manually approved isolated/restorable Server01 test clone',1;
GO
-- CAUTION: GO splits batches. The installer MUST independently guard
-- EVERY batch. The above refusal is informational only. The DDL below
-- contains a permanent zero-default session gate and refuses until a
-- vetted operator creates an approval row in clone config.
IF OBJECT_ID(N'dbo.cabal_diamond_v291_clone_approval',N'U') IS NULL
    THROW 51002,N'STOP: no separately created clone approval table. NO DDL applied.',1;
IF NOT EXISTS (
    SELECT 1 FROM dbo.cabal_diamond_v291_clone_approval
    WHERE ApprovalId=1 AND CloneVerified=1 AND ChangesAllowed=1
)
    THROW 51003,N'STOP: clone approval missing or denied',1;
GO
-- Every subsequent DDL block additionally checks the clone approval.
-- The gate table is intentionally NOT created by this script.
IF NOT EXISTS (
 SELECT 1 FROM dbo.cabal_diamond_v291_clone_approval
 WHERE ApprovalId=1 AND CloneVerified=1 AND ChangesAllowed=1
) THROW 51004,N'STOP: no clone approval',1;
IF OBJECT_ID(N'dbo.cabal_diamond_v291_rank_state',N'U') IS NULL
BEGIN
    CREATE TABLE dbo.cabal_diamond_v291_rank_state(
        UserNum int NOT NULL PRIMARY KEY,
        CharacterIdx int NOT NULL UNIQUE,
        BadgeGrade tinyint NOT NULL CONSTRAINT CK_DiamondV291_Grade CHECK (BadgeGrade IN (1,2)),
        Revision int NOT NULL CONSTRAINT CK_DiamondV291_Revision CHECK (Revision>=0),
        ModifiedAt datetime2(3) NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO
IF NOT EXISTS (
 SELECT 1 FROM dbo.cabal_diamond_v291_clone_approval
 WHERE ApprovalId=1 AND CloneVerified=1 AND ChangesAllowed=1
) THROW 51005,N'STOP: no clone approval',1;
IF OBJECT_ID(N'dbo.cabal_diamond_v291_rank_receipt',N'U') IS NULL
BEGIN
    CREATE TABLE dbo.cabal_diamond_v291_rank_receipt(
        UserNum int NOT NULL,
        CharacterIdx int NOT NULL,
        IntentId bigint NOT NULL,
        ExpectedRevision int NOT NULL,
        AppliedRevision int NOT NULL,
        BeforeWarExp bigint NOT NULL,
        AfterWarExp bigint NOT NULL,
        BeforeTicketUnits int NOT NULL,
        AfterTicketUnits int NOT NULL,
        AfterInventoryHash binary(32) NOT NULL,
        CommittedAt datetime2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
        CONSTRAINT PK_DiamondV291_RankReceipt PRIMARY KEY (UserNum,ExpectedRevision),
        CONSTRAINT UQ_DiamondV291_RankIntent UNIQUE (UserNum,IntentId),
        CONSTRAINT CK_DiamondV291_ReceiptGrade CHECK (AppliedRevision=ExpectedRevision+1),
        CONSTRAINT CK_DiamondV291_ReceiptWexp CHECK (BeforeWarExp-AfterWarExp=30000),
        CONSTRAINT CK_DiamondV291_ReceiptTickets CHECK (BeforeTicketUnits-AfterTicketUnits=100)
    );
END;
GO
-- The stored procedure may ONLY be called by a specially authorized
-- host adapter while a genuine server-owned character lock is held.
-- There is deliberately NO GRANT EXECUTE TO PUBLIC or any player login.
IF NOT EXISTS (
 SELECT 1 FROM dbo.cabal_diamond_v291_clone_approval
 WHERE ApprovalId=1 AND CloneVerified=1 AND ChangesAllowed=1
) THROW 51006,N'STOP: no clone approval before creating procedure',1;
GO
CREATE OR ALTER PROCEDURE dbo.cabal_sp_diamond_v291_atomic_rankup
    @UserNum int,
    @CharacterIdx int,
    @IntentId bigint,
    @ExpectedRevision int,
    @InventoryBefore varbinary(max),
    @InventoryAfter varbinary(max),
    @WarExpBefore bigint,
    @WarExpAfter bigint,
    @WarExpEarnBefore bigint,
    @WarExpUsedBefore bigint,
    @VerifiedTicketUnitsBefore int,
    @VerifiedTicketUnitsAfter int,
    @Outcome int OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET @Outcome=0; -- zero means not applied; only 1 means new commit.

    IF NOT EXISTS (
      SELECT 1 FROM dbo.cabal_diamond_v291_clone_approval
      WHERE ApprovalId=1 AND CloneVerified=1 AND ChangesAllowed=1
    ) THROW 51007,N'STOP: clone approval revoked',1;
    IF @UserNum<=0 OR @CharacterIdx<=0 OR @IntentId<=0
       OR @ExpectedRevision<0 OR @ExpectedRevision>=2147483646
       OR @InventoryBefore IS NULL OR @InventoryAfter IS NULL
       OR DATALENGTH(@InventoryBefore)=0 OR
          DATALENGTH(@InventoryBefore)>15360 OR
       DATALENGTH(@InventoryAfter)>15360 OR
       DATALENGTH(@InventoryBefore)%30<>0 OR
       DATALENGTH(@InventoryAfter)%30<>0 OR
       @InventoryBefore=@InventoryAfter OR
       @WarExpBefore<30000 OR @WarExpAfter<>@WarExpBefore-30000
       OR @WarExpEarnBefore<0 OR @WarExpUsedBefore<0
       OR @VerifiedTicketUnitsBefore<100
       OR @VerifiedTicketUnitsAfter<>@VerifiedTicketUnitsBefore-100
        THROW 51008,N'STOP: malformed or inconsistent proposed rank-up',1;

    DECLARE @lockResult int;
    DECLARE @lockResource nvarchar(128)=
        N'DiamondV291:User:'+CONVERT(nvarchar(20),@UserNum);
    BEGIN TRY
      BEGIN TRANSACTION;

      EXEC @lockResult=sys.sp_getapplock @Resource=@lockResource,
          @LockMode='Exclusive', @LockOwner='Transaction',@LockTimeout=3000;
      IF @lockResult<0 THROW 51009,N'STOP: cannot acquire user serializable lock',1;

      -- Replay-safe and conflict-safe. A previously committed intent is
      -- authoritative. No inventory or WarExp is charged again.
      DECLARE @oldIntent bigint,@oldCharacter int,@oldWexp bigint;
      DECLARE @oldReceiptHash binary(32);
      SELECT @oldIntent=IntentId,@oldCharacter=CharacterIdx,
             @oldWexp=AfterWarExp,@oldReceiptHash=AfterInventoryHash
      FROM dbo.cabal_diamond_v291_rank_receipt WITH(UPDLOCK,HOLDLOCK)
      WHERE UserNum=@UserNum AND ExpectedRevision=@ExpectedRevision;
      IF @oldIntent IS NOT NULL
      BEGIN
        IF @oldIntent<>@IntentId OR @oldCharacter<>@CharacterIdx
           OR @oldWexp<>@WarExpAfter
           OR @oldReceiptHash<>HASHBYTES('SHA2_256',@InventoryAfter)
           THROW 51010,N'STOP: conflicting committed revision',1;
        SET @Outcome=2; -- replay, NOT a new write
        COMMIT TRANSACTION;
        RETURN;
      END;

      -- Existing UserNum<->CharacterIdx mapping MUST have been provisioned
      -- by a trusted WorldSvr-attested binding. Never auto-create from
      -- client input or infer it from an arithmetic CharacterIdx rule.
      IF NOT EXISTS(
         SELECT 1 FROM dbo.cabal_diamond_v291_rank_state WITH(UPDLOCK,HOLDLOCK)
         WHERE UserNum=@UserNum AND CharacterIdx=@CharacterIdx
           AND BadgeGrade=1 AND Revision=@ExpectedRevision
      ) THROW 51011,N'STOP: missing trusted rank owner/revision mapping',1;

      -- Lock and compare actual persisted GameData rows, not a wallet
      -- shadow table. Database compare-and-swap prevents a stale snapshot
      -- from overwriting an unrelated inventory save.
      IF NOT EXISTS (
         SELECT 1 FROM dbo.cabal_Inventory_table WITH(UPDLOCK,HOLDLOCK)
         WHERE CharacterIdx=@CharacterIdx AND Data=@InventoryBefore
      ) THROW 51012,N'STOP: inventory snapshot changed before commit',1;
      IF NOT EXISTS (
         SELECT 1 FROM dbo.cabal_WarExp_Table WITH(UPDLOCK,HOLDLOCK)
         WHERE CharacterIdx=@CharacterIdx
           AND WarExp=@WarExpBefore
           AND WarExpEarn=@WarExpEarnBefore
           AND WarExpUsed=@WarExpUsedBefore
      ) THROW 51013,N'STOP: WarExp snapshot changed before commit',1;

      UPDATE dbo.cabal_Inventory_table
        SET Data=@InventoryAfter
        WHERE CharacterIdx=@CharacterIdx AND Data=@InventoryBefore;
      IF @@ROWCOUNT<>1 THROW 51014,N'STOP: inventory CAS failed',1;
      -- WarExpEarn/WarExpUsed semantics are NOT assumed; these snapshots
      -- are checked and left intact until game-specific accounting verified.
      UPDATE dbo.cabal_WarExp_Table SET WarExp=@WarExpAfter
        WHERE CharacterIdx=@CharacterIdx AND WarExp=@WarExpBefore
          AND WarExpEarn=@WarExpEarnBefore
          AND WarExpUsed=@WarExpUsedBefore;
      IF @@ROWCOUNT<>1 THROW 51015,N'STOP: WarExp CAS failed',1;

      UPDATE dbo.cabal_diamond_v291_rank_state
        SET BadgeGrade=2,Revision=@ExpectedRevision+1,ModifiedAt=SYSUTCDATETIME()
        WHERE UserNum=@UserNum AND CharacterIdx=@CharacterIdx
          AND BadgeGrade=1 AND Revision=@ExpectedRevision;
      IF @@ROWCOUNT<>1 THROW 51016,N'STOP: rank CAS failed',1;

      INSERT INTO dbo.cabal_diamond_v291_rank_receipt(
        UserNum,CharacterIdx,IntentId,ExpectedRevision,AppliedRevision,
        BeforeWarExp,AfterWarExp,BeforeTicketUnits,AfterTicketUnits,AfterInventoryHash)
      VALUES(@UserNum,@CharacterIdx,@IntentId,@ExpectedRevision,
        @ExpectedRevision+1,@WarExpBefore,@WarExpAfter,
        @VerifiedTicketUnitsBefore,@VerifiedTicketUnitsAfter,
        HASHBYTES('SHA2_256',@InventoryAfter));

      COMMIT TRANSACTION;
      SET @Outcome=1;
    END TRY
    BEGIN CATCH
      IF @@TRANCOUNT>0 ROLLBACK TRANSACTION;
      SET @Outcome=0;
      THROW;  -- SQL error is NOT a successful rank-up.
    END CATCH
END;
GO
-- No automatic population of rank_state and NO permission grants.
-- Operator must separately verify the account->character mapping via
-- trusted WorldSvr registry and create a disposable character ONLY.
-- A successful SQL transaction alone still cannot send S2C 0BDA.
