/*
 CABAL v291 Diamond Insignia receipt ledger V1 — ISOLATED CLONE ONLY.
 This script intentionally refuses the live Server01 database.
 Deploy in Server01_DiamondLab AFTER prior shadow wallet V2 test schema.
 It is NOT a game inventory/WExp persistence adapter.
*/
USE [Server01_DiamondLab];
GO
SET NOCOUNT ON;
SET XACT_ABORT ON;
IF DB_NAME() <> N'Server01_DiamondLab'
    THROW 51670, 'STOP: receipt ledger SQL requires Server01_DiamondLab', 1;
IF OBJECT_ID(N'dbo.cabal_diamond_bridge_wallet_v2', N'U') IS NULL
    THROW 51671, 'STOP: isolated Diamond shadow wallet V2 missing', 1;
IF OBJECT_ID(N'dbo.cabal_diamond_v291_receipt_v1', N'U') IS NOT NULL
    THROW 51672, 'STOP: receipt ledger already exists; refusing overwrite', 1;
BEGIN TRY
    BEGIN TRANSACTION;
    CREATE TABLE dbo.cabal_diamond_v291_receipt_v1 (
        UserNum INT NOT NULL,
        ExpectedRevision INT NOT NULL,
        Command TINYINT NOT NULL,
        MasteryID INT NOT NULL,
        AppliedRevision INT NOT NULL,
        NewBadgeGrade TINYINT NOT NULL,
        NewWExp BIGINT NOT NULL,
        NewTicketCount INT NOT NULL,
        NewFreePoints INT NOT NULL,
        ChangedMasteryID INT NOT NULL,
        ChangedMasteryLevel INT NOT NULL,
        CommittedAt DATETIME2(3) NOT NULL
            CONSTRAINT DF_cabal_diamond_v291_receipt_time DEFAULT SYSUTCDATETIME(),
        CONSTRAINT PK_cabal_diamond_v291_receipt_v1
            PRIMARY KEY (UserNum, ExpectedRevision),
        CONSTRAINT FK_cabal_diamond_v291_receipt_owner_v1
            FOREIGN KEY (UserNum)
            REFERENCES dbo.cabal_diamond_bridge_wallet_v2(UserNum),
        CONSTRAINT CK_cabal_diamond_v291_receipt_req_v1 CHECK (
            ExpectedRevision >= 0 AND AppliedRevision = ExpectedRevision + 1
            AND ((Command = 1 AND MasteryID = 0 AND ChangedMasteryID = 0 AND ChangedMasteryLevel = 0)
               OR (Command = 2 AND MasteryID BETWEEN 159 AND 474
                   AND ChangedMasteryID = MasteryID AND ChangedMasteryLevel BETWEEN 1 AND 100))
        ),
        CONSTRAINT CK_cabal_diamond_v291_receipt_state_v1 CHECK (
            NewBadgeGrade IN (1, 2) AND NewWExp >= 0
            AND NewTicketCount >= 0 AND NewFreePoints >= 0
        )
    );
    COMMIT TRANSACTION;
    PRINT 'DIAMOND_V291_RECEIPT_LEDGER=CREATED;DB=Server01_DiamondLab';
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO
/*
 Read a committed receipt under the caller's existing account lock and DB
 transaction. A real adapter MUST authenticate UserNum independently of C2S.
 The caller MUST hold the account lock across lookup, evaluation and commit.
*/
CREATE OR ALTER PROCEDURE dbo.cabal_diamond_v291_receipt_lookup_v1
    @UserNum INT, @ExpectedRevision INT,
    @Command TINYINT, @MasteryID INT
AS
BEGIN
    SET NOCOUNT ON;
    IF DB_NAME() <> N'Server01_DiamondLab'
        THROW 51673, 'STOP: wrong DB for Diamond receipt', 1;
    IF @@TRANCOUNT < 1
        THROW 51674, 'STOP: receipt lookup requires active owner-locked transaction', 1;
    SELECT
        CAST(CASE WHEN Command = @Command AND MasteryID = @MasteryID THEN 1 ELSE -1 END AS INT) AS ReplayResult,
        UserNum, ExpectedRevision, Command, MasteryID, AppliedRevision,
        NewBadgeGrade, NewWExp, NewTicketCount, NewFreePoints,
        ChangedMasteryID, ChangedMasteryLevel, CommittedAt
    FROM dbo.cabal_diamond_v291_receipt_v1 WITH (UPDLOCK, HOLDLOCK)
    WHERE UserNum = @UserNum AND ExpectedRevision = @ExpectedRevision;
    -- No result row means Fresh. This procedure does not modify data.
END;
GO
