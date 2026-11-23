#!/usr/bin/env python3
"""Exact Server01 GameData storage/procedure SQL catalog evidence for Diamond.

Executes only SELECT against SQL Server sys.* (including sys.sql_modules).
Never SELECTs player rows, calls a game procedure or mutates game state.
Must run on EP36_291_TEST VM host, not inside the SQL container.
"""
from __future__ import annotations

import json
import subprocess
import sys

TABLES = (
    "cabal_Inventory_table",
    "cabal_inventory_ex_table",
    "cabal_WarExp_Table",
    "cabal_merit_table",
    "cabal_merit_platinum_table",
    "cabal_merit_platinum_mastery_table",
)
PROCEDURES = (
    "cabal_tool_inventory_get",
    "cabal_tool_inventory_set",
    "Cabal_Sp_InstantWar_GetWarExp",
    "Cabal_Sp_InstantWar_SetWarExp",
    "cabal_tool_merit_get",
    "cabal_tool_merit_set",
    "cabal_tool_merit_platinum_get",
    "cabal_tool_merit_platinum_set",
    "cabal_tool_merit_platinum_mastery_get",
    "cabal_tool_merit_platinum_mastery_set",
)
# Literal identifiers only. No dynamic interpolated SQL or user row queries.
SQL = r"""
SET NOCOUNT ON;
SELECT N'DATABASE|' + DB_NAME();

SELECT N'TABLE|' + s.name + N'|' + t.name
FROM sys.tables AS t JOIN sys.schemas AS s ON s.schema_id=t.schema_id
WHERE LOWER(t.name) IN
('cabal_inventory_table','cabal_inventory_ex_table','cabal_warexp_table',
 'cabal_merit_table','cabal_merit_platinum_table',
 'cabal_merit_platinum_mastery_table')
ORDER BY t.name;

SELECT N'COLUMN|' + s.name + N'|' + t.name + N'|' + c.name
  + N'|' + ty.name + N'|' + CONVERT(nvarchar(12),c.max_length)
  + N'|' + CONVERT(nvarchar(2),c.is_nullable)
FROM sys.tables AS t
JOIN sys.schemas AS s ON s.schema_id=t.schema_id
JOIN sys.columns AS c ON c.object_id=t.object_id
JOIN sys.types AS ty ON ty.user_type_id=c.user_type_id
WHERE LOWER(t.name) IN
('cabal_inventory_table','cabal_inventory_ex_table','cabal_warexp_table',
 'cabal_merit_table','cabal_merit_platinum_table',
 'cabal_merit_platinum_mastery_table')
ORDER BY t.name,c.column_id;

SELECT N'INDEX|' + s.name + N'|' + t.name + N'|' + i.name
  + N'|' + CONVERT(nvarchar(2),i.is_unique)
  + N'|' + CONVERT(nvarchar(2),i.is_primary_key)
  + N'|' + CONVERT(nvarchar(12),ic.key_ordinal)
  + N'|' + c.name
FROM sys.tables AS t
JOIN sys.schemas AS s ON s.schema_id=t.schema_id
JOIN sys.indexes AS i ON i.object_id=t.object_id
JOIN sys.index_columns AS ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
JOIN sys.columns AS c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
WHERE LOWER(t.name) IN
('cabal_inventory_table','cabal_inventory_ex_table','cabal_warexp_table',
 'cabal_merit_table','cabal_merit_platinum_table',
 'cabal_merit_platinum_mastery_table')
  AND ic.is_included_column=0
ORDER BY t.name,i.name,ic.key_ordinal;

SELECT N'TRIGGER|' + s.name + N'|' + t.name + N'|' + tr.name
  + N'|' + CONVERT(nvarchar(2),tr.is_disabled)
FROM sys.triggers AS tr
JOIN sys.tables AS t ON t.object_id=tr.parent_id
JOIN sys.schemas AS s ON s.schema_id=t.schema_id
WHERE LOWER(t.name) IN
('cabal_inventory_table','cabal_inventory_ex_table','cabal_warexp_table',
 'cabal_merit_table','cabal_merit_platinum_table',
 'cabal_merit_platinum_mastery_table')
ORDER BY t.name,tr.name;

SELECT N'PROCEDURE|' + s.name + N'|' + p.name
FROM sys.procedures AS p JOIN sys.schemas AS s ON s.schema_id=p.schema_id
WHERE LOWER(p.name) IN
('cabal_tool_inventory_get','cabal_tool_inventory_set',
 'cabal_sp_instantwar_getwarexp','cabal_sp_instantwar_setwarexp',
 'cabal_tool_merit_get','cabal_tool_merit_set',
 'cabal_tool_merit_platinum_get','cabal_tool_merit_platinum_set',
 'cabal_tool_merit_platinum_mastery_get',
 'cabal_tool_merit_platinum_mastery_set')
ORDER BY p.name;

SELECT N'PARAMETER|' + s.name + N'|' + p.name + N'|' + a.name
  + N'|' + ty.name + N'|' + CONVERT(nvarchar(12),a.max_length)
  + N'|' + CONVERT(nvarchar(2),a.is_output)
FROM sys.procedures AS p
JOIN sys.schemas AS s ON s.schema_id=p.schema_id
JOIN sys.parameters AS a ON a.object_id=p.object_id
JOIN sys.types AS ty ON ty.user_type_id=a.user_type_id
WHERE LOWER(p.name) IN
('cabal_tool_inventory_get','cabal_tool_inventory_set',
 'cabal_sp_instantwar_getwarexp','cabal_sp_instantwar_setwarexp',
 'cabal_tool_merit_get','cabal_tool_merit_set',
 'cabal_tool_merit_platinum_get','cabal_tool_merit_platinum_set',
 'cabal_tool_merit_platinum_mastery_get',
 'cabal_tool_merit_platinum_mastery_set')
ORDER BY p.name,a.parameter_id;

-- These are *hints* extracted from procedure definitions, not proof that a
-- stored procedure is an atomic and safe WorldSvr gameplay mutation.
-- Do NOT print or export complete procedure source or credentials.
SELECT N'MODULE|' + s.name + N'|' + p.name
  + N'|' + CONVERT(nvarchar(12),COALESCE(LEN(m.definition),-1))
  + N'|' + CONVERT(nvarchar(2),CASE WHEN CHARINDEX('BEGIN TRAN',UPPER(m.definition))>0 THEN 1 ELSE 0 END)
  + N'|' + CONVERT(nvarchar(2),CASE WHEN CHARINDEX('COMMIT',UPPER(m.definition))>0 THEN 1 ELSE 0 END)
  + N'|' + CONVERT(nvarchar(2),CASE WHEN CHARINDEX('ROLLBACK',UPPER(m.definition))>0 THEN 1 ELSE 0 END)
  + N'|' + CONVERT(nvarchar(2),CASE WHEN CHARINDEX('CABAL_INVENTORY_TABLE',UPPER(m.definition))>0 THEN 1 ELSE 0 END)
  + N'|' + CONVERT(nvarchar(2),CASE WHEN CHARINDEX('CABAL_WAREXP_TABLE',UPPER(m.definition))>0
                                   OR CHARINDEX('CABAL_WAREXP_TABLE',REPLACE(UPPER(m.definition),'_',''))>0
                                   THEN 1 ELSE 0 END)
  + N'|' + CONVERT(nvarchar(2),CASE WHEN CHARINDEX('CABAL_MERIT_PLATINUM_TABLE',UPPER(m.definition))>0 THEN 1 ELSE 0 END)
FROM sys.procedures AS p
JOIN sys.schemas AS s ON s.schema_id=p.schema_id
LEFT JOIN sys.sql_modules AS m ON m.object_id=p.object_id
WHERE LOWER(p.name) IN
('cabal_tool_inventory_get','cabal_tool_inventory_set',
 'cabal_sp_instantwar_getwarexp','cabal_sp_instantwar_setwarexp',
 'cabal_tool_merit_get','cabal_tool_merit_set',
 'cabal_tool_merit_platinum_get','cabal_tool_merit_platinum_set',
 'cabal_tool_merit_platinum_mastery_get',
 'cabal_tool_merit_platinum_mastery_set')
ORDER BY p.name;
"""
# Never print secrets. Uses validated existing sql_main 2022 transport.
SQLCMD_SH = r"""set -eu
exe=''
for p in /opt/mssql-tools18/bin/sqlcmd /opt/mssql-tools/bin/sqlcmd; do
  if [ -x "$p" ]; then exe="$p"; break; fi
done
if [ -z "$exe" ]; then exit 23; fi
password="$(printenv MSSQL_SA_PASSWORD || printenv SA_PASSWORD || true)"
if [ -z "$password" ]; then exit 24; fi
export SQLCMDPASSWORD="$password"
"$exe" -S localhost -U sa -d Server01 -C -b -W -h -1 -w 4096 -i /dev/stdin
"""
WIDTHS = {
    "DATABASE":1,"TABLE":2,"COLUMN":6,"INDEX":7,
    "TRIGGER":4,"PROCEDURE":2,"PARAMETER":6,"MODULE":9,
}
SUSPECT_DEFAULTS = {"status":"STOP","metadata_only":True,
    "sql_mutations":False,"game_player_rows_read":False,
    "worldsvr_changed":False}

def parse(stdout: str):
    rows={k:[] for k in WIDTHS}
    for line in stdout.splitlines():
        line=line.strip()
        if not line or line.startswith("("): continue
        tag,sep,*rest=line.split("|")
        if not sep: raise ValueError("MALFORMED_ROW")
        if tag not in WIDTHS: raise ValueError("UNEXPECTED_SQL_OUTPUT")
        cells=line.split("|")[1:]
        if len(cells)!=WIDTHS[tag]: raise ValueError("WRONG_FIELD_COUNT_"+tag)
        if not all(cell and len(cell)<300 for cell in cells):
            raise ValueError("INVALID_FIELD_VALUE_"+tag)
        rows[tag].append(cells)
    if rows["DATABASE"]!=[["Server01"]]:
        raise ValueError("WRONG_DATABASE")
    for schema,name in rows["TABLE"] + rows["PROCEDURE"]:
        if schema.lower()!="dbo": raise ValueError("UNEXPECTED_SCHEMA")
        expected=TABLES if [schema,name] in rows["TABLE"] else PROCEDURES
        if name.lower() not in {z.lower() for z in expected}:
            raise ValueError("UNEXPECTED_CATALOG_ITEM")
    return rows

def run():
    result=dict(SUSPECT_DEFAULTS)
    result.update({"mode":"CABAL_V291_REAL_GAMEDATA_CONTRACT","database":"Server01"})
    try:
        p=subprocess.run(["hostname"],capture_output=True,text=True,timeout=6)
        if p.returncode or p.stdout.strip()!="cabalep33":
            raise ValueError("WRONG_GUEST")
        p=subprocess.run(["docker","inspect","sql_main",
                          "--format","{{.State.Running}}"],
                         capture_output=True,text=True,timeout=10)
        if p.returncode or p.stdout.strip()!="true":
            raise ValueError("SQL_NOT_RUNNING")
        p=subprocess.run(["docker","exec","-i","sql_main",
                          "sh","-lc",SQLCMD_SH],
                         input=SQL,capture_output=True,text=True,timeout=65)
        if p.returncode: raise ValueError("SQLCMD_FAILED_"+str(p.returncode))
        rows=parse(p.stdout)
        result.update({"status":"PASS","catalog":rows,
            "counts":{k:len(v) for k,v in rows.items()},
            "candidate_warning":"Metadata only. No item stack codec or atomic write proven."})
    except (ValueError,OSError,subprocess.TimeoutExpired) as e:
        result["reason"]=str(e)[:100]
    return result

if __name__=="__main__":
    x=run()
    print(json.dumps(x,sort_keys=True,separators=(",",":")))
    sys.exit(0 if x["status"]=="PASS" else 2)
