-- TEST CLONE ONLY. Remove only three uniquely named LAB procedures.
USE [Server01_DiamondLab];
GO
SET NOCOUNT ON;
IF DB_NAME() <> N'Server01_DiamondLab'
 THROW 51501,'STOP: only Server01_DiamondLab is allowed',1;
IF OBJECT_ID(N'dbo.cabal_merit_diamond_lab_v1',N'U') IS NULL
 THROW 51502,'STOP: LAB table missing',1;
-- Run before 03_rollback_TEST_CLONE_ONLY.sql.
IF OBJECT_ID(N'dbo.cabal_diamond_lab_commit_v1',N'P') IS NOT NULL
 DROP PROCEDURE dbo.cabal_diamond_lab_commit_v1;
IF OBJECT_ID(N'dbo.cabal_diamond_lab_get_v1',N'P') IS NOT NULL
 DROP PROCEDURE dbo.cabal_diamond_lab_get_v1;
IF OBJECT_ID(N'dbo.cabal_diamond_lab_init_v1',N'P') IS NOT NULL
 DROP PROCEDURE dbo.cabal_diamond_lab_init_v1;
PRINT 'DIAMOND_LAB_PROCEDURES_REMOVED=YES';
GO
