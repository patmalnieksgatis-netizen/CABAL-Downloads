-- TEST CLONE ONLY: rollback of the Diamond lab artifact.
-- Refuses to drop any table with test rows or unknown column layout.
USE [Server01_DiamondLab];
GO
SET NOCOUNT ON;
SET XACT_ABORT ON;
SET LOCK_TIMEOUT 5000;
IF DB_NAME() <> N'Server01_DiamondLab'
    THROW 51201, 'STOP: rollback only in Server01_DiamondLab', 1;
IF OBJECT_ID(N'dbo.cabal_merit_diamond_lab_v1', N'U') IS NULL
    THROW 51202, 'STOP: Diamond lab table missing; nothing to remove', 1;
IF (SELECT COUNT(*) FROM sys.columns WHERE object_id=OBJECT_ID(N'dbo.cabal_merit_diamond_lab_v1')) <> 11
    THROW 51203, 'STOP: Diamond lab schema changed; manual review needed', 1;
IF EXISTS (SELECT TOP (1) 1 FROM dbo.cabal_merit_diamond_lab_v1)
    THROW 51204, 'STOP: Diamond lab has rows; preserve or export test data before dropping', 1;
BEGIN TRY
    BEGIN TRANSACTION;
    DROP TABLE dbo.cabal_merit_diamond_lab_v1;
    COMMIT TRANSACTION;
    PRINT 'DIAMOND_LAB_SCHEMA_V1_REMOVED=YES';
END TRY
BEGIN CATCH
    IF @@TRANCOUNT>0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO
