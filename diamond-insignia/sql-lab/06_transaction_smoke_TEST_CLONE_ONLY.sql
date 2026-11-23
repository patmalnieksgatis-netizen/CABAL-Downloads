-- TEST LAB ONLY; test a synthetic Diamond user and ROLLBACK everything.
USE [Server01_DiamondLab];
GO
SET NOCOUNT ON;
SET XACT_ABORT ON;
IF DB_NAME() <> N'Server01_DiamondLab'
 THROW 51401,'STOP: only Server01_DiamondLab is allowed',1;
IF OBJECT_ID(N'dbo.cabal_diamond_lab_commit_v1',N'P') IS NULL
 THROW 51402,'STOP: LAB procedures missing',1;
DECLARE @SyntheticUserNum INT=2147483600;
IF EXISTS (SELECT 1 FROM dbo.cabal_merit_diamond_lab_v1 WHERE UserNum=@SyntheticUserNum)
 THROW 51403,'STOP: synthetic LAB user ID already taken',1;
BEGIN TRY
 BEGIN TRANSACTION;
 INSERT INTO dbo.cabal_merit_diamond_lab_v1
   (UserNum,DiamondUnlocked,DiamondScore,DiamondMasteryPoint,ActiveDiamondCategory,RowRevision)
 VALUES(@SyntheticUserNum,1,0,0,NULL,0);
 EXEC dbo.cabal_diamond_lab_commit_v1
   @UserNum=@SyntheticUserNum,
   @ExpectedRowRevision=0,
   @NewDiamondScore=125,
   @NewDiamondMasteryPoint=10,
   @ActiveDiamondCategory=11;
 IF NOT EXISTS(
  SELECT 1 FROM dbo.cabal_merit_diamond_lab_v1
  WHERE UserNum=@SyntheticUserNum AND BadgeGrade=2 AND DiamondUnlocked=1
    AND DiamondScore=125 AND DiamondMasteryPoint=10
    AND ActiveDiamondCategory=11 AND RowRevision=1)
   THROW 51404,'STOP: LAB commit verification failed',1;
 ROLLBACK TRANSACTION;
 IF EXISTS (SELECT 1 FROM dbo.cabal_merit_diamond_lab_v1 WHERE UserNum=@SyntheticUserNum)
   THROW 51405,'STOP: synthetic row remains after rollback',1;
 PRINT 'DIAMOND_LAB_TRANSACTION_SMOKE=PASS_ROLLED_BACK';
END TRY
BEGIN CATCH
 IF @@TRANCOUNT>0 ROLLBACK TRANSACTION;
 THROW;
END CATCH;
GO
