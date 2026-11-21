-- TEST LAB ONLY; not connected to current CABAL WorldSvr or client.
-- Does NOT grant Diamond, deduct WExp/items, or validate game packets.
USE [Server01_DiamondLab];
GO
SET NOCOUNT ON;
IF DB_NAME() <> N'Server01_DiamondLab' THROW 51301,'STOP: Diamond lab only',1;
IF OBJECT_ID(N'dbo.cabal_merit_diamond_lab_v1',N'U') IS NULL THROW 51302,'STOP: install LAB V1 first',1;
IF OBJECT_ID(N'dbo.cabal_merit_platinum_table',N'U') IS NULL THROW 51303,'STOP: Platinum table absent',1;
IF OBJECT_ID(N'dbo.cabal_diamond_lab_init_v1',N'P') IS NOT NULL OR
   OBJECT_ID(N'dbo.cabal_diamond_lab_get_v1',N'P') IS NOT NULL OR
   OBJECT_ID(N'dbo.cabal_diamond_lab_commit_v1',N'P') IS NOT NULL
 THROW 51304,'STOP: LAB procedure already exists',1;
GO

-- Test-only initialization. Requires an EXISTING Platinum badge.
-- Does not unlock Diamond: real server must validate rank-up resources.
CREATE PROCEDURE dbo.cabal_diamond_lab_init_v1 @UserNum INT
AS
BEGIN
 SET NOCOUNT ON; SET XACT_ABORT ON; SET LOCK_TIMEOUT 5000;
 IF DB_NAME() <> N'Server01_DiamondLab' THROW 51311,'STOP: Incorrect DB',1;
 IF @UserNum IS NULL OR @UserNum<=0 THROW 51312,'STOP: Invalid user',1;
 BEGIN TRY
  BEGIN TRANSACTION;
  IF NOT EXISTS (SELECT 1 FROM dbo.cabal_merit_platinum_table WITH (HOLDLOCK)
                 WHERE UserNum=@UserNum AND HaveMeritPlatinumBagde=1)
   THROW 51313,'STOP: Platinum prerequisite not met',1;
  IF EXISTS (SELECT 1 FROM dbo.cabal_merit_diamond_lab_v1 WITH (UPDLOCK,HOLDLOCK)
             WHERE UserNum=@UserNum)
   THROW 51314,'STOP: LAB row already exists',1;
  INSERT INTO dbo.cabal_merit_diamond_lab_v1(UserNum) VALUES(@UserNum);
  IF @@ROWCOUNT<>1 THROW 51315,'STOP: insert count not one',1;
  COMMIT TRANSACTION;
 END TRY
 BEGIN CATCH
  IF @@TRANCOUNT>0 ROLLBACK TRANSACTION;
  THROW;
 END CATCH;
END;
GO

CREATE PROCEDURE dbo.cabal_diamond_lab_get_v1 @UserNum INT
AS
BEGIN
 SET NOCOUNT ON;
 IF DB_NAME() <> N'Server01_DiamondLab' THROW 51321,'STOP: Incorrect DB',1;
 IF @UserNum IS NULL OR @UserNum<=0 THROW 51322,'STOP: Invalid user',1;
 SELECT UserNum,BadgeGrade,DiamondUnlocked,DiamondScore,DiamondMasteryPoint,
        ActiveDiamondCategory,MasteryPayload,OpenSlotPayload,
        SpecialMasteryPayload,RowRevision,UpdatedAtUtc
 FROM dbo.cabal_merit_diamond_lab_v1 WHERE UserNum=@UserNum;
END;
GO

-- This is a serialization primitive for a FUTURE verified server adapter.
-- Not a public/game-client API. Caller must validate purchases, costs,
-- prerequisites, score formula and server-authoritative packet contents.
CREATE PROCEDURE dbo.cabal_diamond_lab_commit_v1
 @UserNum INT, @ExpectedRowRevision INT,
 @NewDiamondScore INT, @NewDiamondMasteryPoint INT,
 @ActiveDiamondCategory TINYINT=NULL,
 @MasteryPayload VARBINARY(MAX)=NULL,
 @OpenSlotPayload VARBINARY(MAX)=NULL,
 @SpecialMasteryPayload VARBINARY(MAX)=NULL
AS
BEGIN
 SET NOCOUNT ON; SET XACT_ABORT ON; SET LOCK_TIMEOUT 5000;
 IF DB_NAME() <> N'Server01_DiamondLab' THROW 51331,'STOP: Incorrect DB',1;
 IF @UserNum IS NULL OR @UserNum<=0 THROW 51332,'STOP: Invalid user',1;
 IF @ExpectedRowRevision IS NULL OR @ExpectedRowRevision<0 OR
    @ExpectedRowRevision>=2147483647
    THROW 51333,'STOP: Revision invalid',1;
 IF @NewDiamondScore IS NULL OR @NewDiamondScore<0 OR
    @NewDiamondMasteryPoint IS NULL OR @NewDiamondMasteryPoint<0
    THROW 51334,'STOP: Numeric counters invalid',1;
 IF @ActiveDiamondCategory IS NOT NULL AND
    (@ActiveDiamondCategory<11 OR @ActiveDiamondCategory>26)
    THROW 51335,'STOP: Diamond category invalid',1;
 -- Conservative limits, NOT proof of actual game serializer layout.
 IF DATALENGTH(@MasteryPayload)>65536 OR
    DATALENGTH(@OpenSlotPayload)>16384 OR
    DATALENGTH(@SpecialMasteryPayload)>16384
    THROW 51336,'STOP: LAB payload too long',1;
 BEGIN TRY
  BEGIN TRANSACTION;
  UPDATE dbo.cabal_merit_diamond_lab_v1 WITH (UPDLOCK,HOLDLOCK)
  SET DiamondScore=@NewDiamondScore,
      DiamondMasteryPoint=@NewDiamondMasteryPoint,
      ActiveDiamondCategory=@ActiveDiamondCategory,
      MasteryPayload=@MasteryPayload,
      OpenSlotPayload=@OpenSlotPayload,
      SpecialMasteryPayload=@SpecialMasteryPayload,
      RowRevision=RowRevision+1,UpdatedAtUtc=SYSUTCDATETIME()
  WHERE UserNum=@UserNum AND RowRevision=@ExpectedRowRevision
    AND BadgeGrade=2 AND DiamondUnlocked=1;
  IF @@ROWCOUNT<>1 THROW 51337,'STOP: Missing/locked/stale Diamond row',1;
  COMMIT TRANSACTION;
  SELECT @ExpectedRowRevision+1 AS NewRowRevision;
 END TRY
 BEGIN CATCH
  IF @@TRANCOUNT>0 ROLLBACK TRANSACTION;
  THROW;
 END CATCH;
END;
GO
-- No GRANT to public or to game database user.
