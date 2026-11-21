-- READ-ONLY catalog inspection. No user or character records read.
USE [Server01_DiamondLab];
GO
SET NOCOUNT ON;
IF DB_NAME() <> N'Server01_DiamondLab'
    THROW 51101, 'STOP: expected isolated Server01_DiamondLab', 1;
IF OBJECT_ID(N'dbo.cabal_merit_diamond_lab_v1', N'U') IS NULL
    THROW 51102, 'STOP: Diamond lab table missing', 1;
SELECT N'DIAMOND_LAB_METADATA' AS Audit,
       SCHEMA_NAME(t.schema_id) AS SchemaName,
       t.name AS TableName,
       c.column_id AS ColumnOrdinal,
       c.name AS ColumnName,
       ty.name AS SqlType,
       c.max_length AS MaxLength,
       c.is_nullable AS Nullable
FROM sys.tables t
JOIN sys.columns c ON c.object_id=t.object_id
JOIN sys.types ty ON ty.user_type_id=c.user_type_id
WHERE t.object_id=OBJECT_ID(N'dbo.cabal_merit_diamond_lab_v1')
ORDER BY c.column_id;
SELECT N'DIAMOND_LAB_CHECKS' AS Audit, cc.name AS CheckName, cc.is_disabled AS Disabled
FROM sys.check_constraints cc
WHERE cc.parent_object_id=OBJECT_ID(N'dbo.cabal_merit_diamond_lab_v1')
ORDER BY cc.name;
GO
