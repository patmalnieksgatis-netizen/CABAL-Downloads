-- Only on isolated clone Server01_DiamondLab, against synthetic UserNum 900001.
-- This is NOT a production data migration or gameplay command.
USE [Server01_DiamondLab];
GO
SET NOCOUNT ON;
SET XACT_ABORT ON;
SET LOCK_TIMEOUT 5000;
IF DB_NAME()<>N'Server01_DiamondLab'
 THROW 51701,'STOP: Lab DB required',1;
IF OBJECT_ID(N'dbo.cabal_diamond_bridge_wallet_v2',N'U') IS NULL OR
   OBJECT_ID(N'dbo.cabal_diamond_bridge_slot_v2',N'U') IS NULL OR
   OBJECT_ID(N'dbo.cabal_diamond_bridge_mastery_v2',N'U') IS NULL
 THROW 51702,'STOP: Install 08 first',1;
IF EXISTS(SELECT 1 FROM dbo.cabal_diamond_bridge_wallet_v2 WHERE UserNum=900001)
 THROW 51703,'STOP: Synthetic test user already exists: never reset balances',1;
BEGIN TRY
 BEGIN TRANSACTION;
 INSERT dbo.cabal_diamond_bridge_wallet_v2
  (UserNum,SessionNonce,PlatinumBadge,PlatinumMaxed,BadgeGrade,WExp,
   MedalItemCount,FreePoints,ActiveCategoryMask,RowRevision)
 VALUES(900001,123456789,1,1,1,40000,120,100,1,10);
 INSERT dbo.cabal_diamond_bridge_slot_v2(UserNum,MasteryID) VALUES(900001,159);
 COMMIT TRANSACTION;
 SELECT UserNum,BadgeGrade,WExp,MedalItemCount,FreePoints,RowRevision
 FROM dbo.cabal_diamond_bridge_wallet_v2 WHERE UserNum=900001;
END TRY
BEGIN CATCH
 IF @@TRANCOUNT>0 ROLLBACK TRANSACTION;
 THROW;
END CATCH;
GO
-- Rows are separate synthetic shadow state, NEVER real inventory or Account.
