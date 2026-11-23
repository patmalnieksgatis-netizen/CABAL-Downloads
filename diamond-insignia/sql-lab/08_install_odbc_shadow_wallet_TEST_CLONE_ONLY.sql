-- CABAL v291 Diamond MSSQL ODBC bridge: strictly ISOLATED SHADOW WALLET.
-- NOT a production migration or inventory database schema.
-- Do not deploy to Server01: only Server01_DiamondLab is allowed.
USE [Server01_DiamondLab];
GO
SET NOCOUNT ON;
SET XACT_ABORT ON;
SET LOCK_TIMEOUT 5000;
IF DB_NAME() <> N'Server01_DiamondLab'
  THROW 51601, 'STOP: Requires isolated Server01_DiamondLab', 1;
IF OBJECT_ID(N'dbo.cabal_diamond_bridge_wallet_v2',N'U') IS NOT NULL OR
   OBJECT_ID(N'dbo.cabal_diamond_bridge_mastery_v2',N'U') IS NOT NULL OR
   OBJECT_ID(N'dbo.cabal_diamond_bridge_slot_v2',N'U') IS NOT NULL
  THROW 51602, 'STOP: Existing V2 shadow tables; do not overwrite', 1;
IF EXISTS(SELECT 1 FROM sys.objects WHERE name IN
  (N'cabal_diamond_bridge_wallet_v2',N'cabal_diamond_bridge_mastery_v2',N'cabal_diamond_bridge_slot_v2'))
  THROW 51603, 'STOP: Shadow object name is already in use', 1;
BEGIN TRY
 BEGIN TRANSACTION;
 CREATE TABLE dbo.cabal_diamond_bridge_wallet_v2(
  UserNum INT NOT NULL PRIMARY KEY,
  SessionNonce BIGINT NOT NULL,
  PlatinumBadge BIT NOT NULL,
  PlatinumMaxed BIT NOT NULL,
  BadgeGrade TINYINT NOT NULL,
  WExp BIGINT NOT NULL,
  MedalItemCount INT NOT NULL,
  FreePoints INT NOT NULL,
  ActiveCategoryMask INT NOT NULL,
  RowRevision INT NOT NULL,
  CONSTRAINT CK_cabal_diamond_bridge_wallet_v2_Grade CHECK(BadgeGrade IN (1,2)),
  CONSTRAINT CK_cabal_diamond_bridge_wallet_v2_Resources CHECK(
    WExp>=0 AND MedalItemCount>=0 AND FreePoints>=0 AND RowRevision>=0),
  CONSTRAINT CK_cabal_diamond_bridge_wallet_v2_Cat CHECK(
    ActiveCategoryMask BETWEEN 0 AND 65535)
 );
 CREATE TABLE dbo.cabal_diamond_bridge_slot_v2(
  UserNum INT NOT NULL,
  MasteryID INT NOT NULL CHECK(MasteryID BETWEEN 159 AND 474),
  CONSTRAINT PK_cabal_diamond_bridge_slot_v2 PRIMARY KEY(UserNum,MasteryID),
  CONSTRAINT FK_cabal_diamond_bridge_slot_v2_Wallet FOREIGN KEY(UserNum)
    REFERENCES dbo.cabal_diamond_bridge_wallet_v2(UserNum)
 );
 CREATE TABLE dbo.cabal_diamond_bridge_mastery_v2(
  UserNum INT NOT NULL,
  MasteryID INT NOT NULL CHECK(MasteryID BETWEEN 159 AND 474),
  MasteryLevel INT NOT NULL CHECK(MasteryLevel BETWEEN 1 AND 100),
  CONSTRAINT PK_cabal_diamond_bridge_mastery_v2 PRIMARY KEY(UserNum,MasteryID),
  CONSTRAINT FK_cabal_diamond_bridge_mastery_v2_Wallet FOREIGN KEY(UserNum)
    REFERENCES dbo.cabal_diamond_bridge_wallet_v2(UserNum)
 );
 COMMIT TRANSACTION;
 PRINT 'DIAMOND_MSSQL_SHADOW_V2_CREATED=YES;GAME_TABLES_MODIFIED=NO';
END TRY
BEGIN CATCH
 IF @@TRANCOUNT>0 ROLLBACK TRANSACTION;
 THROW;
END CATCH;
GO
-- No GRANTs, no seed users, no ALTER of existing Merit/Platinum tables.
-- SessionNonce, item count and WExp are mock shadow values, NOT real game inventory.
