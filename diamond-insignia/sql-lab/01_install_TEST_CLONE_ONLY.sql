-- CABAL DIAMOND INSIGNIA / LAB V1. NOT A PRODUCTION INSTALLER.
-- Only a named clone database, Server01_DiamondLab, may be modified.
-- A standalone shadow persistence adapter: WorldSvr does not call it yet.
-- NO changes to legacy Platinum, Gold, Account or existing procedures.
USE [Server01_DiamondLab];
GO
SET NOCOUNT ON;
SET XACT_ABORT ON;
SET LOCK_TIMEOUT 5000;

IF DB_NAME() <> N'Server01_DiamondLab'
    THROW 51001, 'STOP: Diamond LAB requires Server01_DiamondLab clone only', 1;
IF OBJECT_ID(N'dbo.cabal_merit_platinum_table', N'U') IS NULL
   OR OBJECT_ID(N'dbo.cabal_merit_platinum_mastery_table', N'U') IS NULL
   OR OBJECT_ID(N'dbo.cabal_merit_table', N'U') IS NULL
    THROW 51002, 'STOP: Source Merit/Platinum tables missing in clone', 1;
IF NOT EXISTS (
 SELECT 1 FROM sys.indexes i
 JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
 JOIN sys.columns c ON c.object_id=i.object_id AND c.column_id=ic.column_id
 WHERE i.object_id=OBJECT_ID(N'dbo.cabal_merit_platinum_table')
   AND i.is_primary_key=1 AND ic.key_ordinal=1 AND c.name=N'UserNum'
)
    THROW 51003, 'STOP: Platinum UserNum primary key not verified', 1;
IF OBJECT_ID(N'dbo.cabal_merit_diamond_lab_v1', N'U') IS NOT NULL
    THROW 51004, 'STOP: Diamond lab table already exists; do not overwrite', 1;
IF EXISTS (SELECT 1 FROM sys.objects WHERE name=N'cabal_merit_diamond_lab_v1')
    THROW 51005, 'STOP: Diamond lab object name already taken', 1;
BEGIN TRY
    BEGIN TRANSACTION;
    CREATE TABLE dbo.cabal_merit_diamond_lab_v1
    (
       UserNum INT NOT NULL,
       BadgeGrade TINYINT NOT NULL CONSTRAINT DF_cabal_merit_diamond_lab_v1_BadgeGrade DEFAULT (2),
       DiamondUnlocked BIT NOT NULL CONSTRAINT DF_cabal_merit_diamond_lab_v1_Unlocked DEFAULT (0),
       DiamondScore INT NOT NULL CONSTRAINT DF_cabal_merit_diamond_lab_v1_Score DEFAULT (0),
       DiamondMasteryPoint INT NOT NULL CONSTRAINT DF_cabal_merit_diamond_lab_v1_Point DEFAULT (0),
       ActiveDiamondCategory TINYINT NULL,
       -- The client/server payload encoding is not known: do not populate any blob yet.
       MasteryPayload VARBINARY(MAX) NULL,
       OpenSlotPayload VARBINARY(MAX) NULL,
       SpecialMasteryPayload VARBINARY(MAX) NULL,
       RowRevision INT NOT NULL CONSTRAINT DF_cabal_merit_diamond_lab_v1_Revision DEFAULT (0),
       UpdatedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_cabal_merit_diamond_lab_v1_Updated DEFAULT (SYSUTCDATETIME()),
       CONSTRAINT PK_cabal_merit_diamond_lab_v1 PRIMARY KEY CLUSTERED (UserNum),
       CONSTRAINT CK_cabal_merit_diamond_lab_v1_Grade CHECK (BadgeGrade=2),
       CONSTRAINT CK_cabal_merit_diamond_lab_v1_Score CHECK (DiamondScore>=0),
       CONSTRAINT CK_cabal_merit_diamond_lab_v1_Point CHECK (DiamondMasteryPoint>=0),
       CONSTRAINT CK_cabal_merit_diamond_lab_v1_Category CHECK (ActiveDiamondCategory IS NULL OR ActiveDiamondCategory BETWEEN 11 AND 26),
       CONSTRAINT CK_cabal_merit_diamond_lab_v1_Revision CHECK (RowRevision>=0)
    );
    COMMIT TRANSACTION;
    PRINT 'DIAMOND_LAB_SCHEMA_V1_CREATED=YES';
END TRY
BEGIN CATCH
    IF @@TRANCOUNT>0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO
