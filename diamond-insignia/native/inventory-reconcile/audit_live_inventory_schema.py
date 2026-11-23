#!/usr/bin/env python3
"""Read-only SQL Server metadata audit for CABAL GameData inventory and WExp.

Runs on verified EP36_291_TEST VM HOST and queries sys.* catalog only.
NO player data, DDL, DML, stored-procedure execution, or game edits.
Reuses the previously working sql_main sqlcmd convention.
"""
from __future__ import annotations
import json
import subprocess
import sys

TARGET_DB = "Server01"
SQL = r"""
SET NOCOUNT ON;
SELECT N'DATABASE|' + DB_NAME();
SELECT TOP (120) N'TABLE|' + SCHEMA_NAME(t.schema_id) + N'|' + t.name
FROM sys.tables AS t
WHERE t.name LIKE '%inventor%' OR t.name LIKE '%char%' OR
      t.name LIKE '%item%' OR t.name LIKE '%merit%' OR
      t.name LIKE '%warehouse%' OR t.name LIKE '%war%exp%'
ORDER BY t.name;
SELECT TOP (600)
       N'COLUMN|' + SCHEMA_NAME(t.schema_id) + N'|' + t.name
       + N'|' + c.name + N'|' + ty.name
       + N'|' + CONVERT(nvarchar(10),c.max_length)
       + N'|' + CONVERT(nvarchar(10),c.is_nullable)
FROM sys.tables AS t
JOIN sys.columns AS c ON c.object_id=t.object_id
JOIN sys.types AS ty ON ty.user_type_id=c.user_type_id
WHERE t.name LIKE '%inventor%' OR t.name LIKE '%char%'
   OR t.name LIKE '%merit%' OR t.name LIKE '%warehouse%'
   OR c.name LIKE '%item%' OR c.name LIKE '%inventory%'
   OR c.name LIKE '%wexp%' OR c.name LIKE '%warexp%'
   OR c.name LIKE '%battle%exp%'
ORDER BY t.name,c.column_id;
SELECT TOP (180)
       N'PROCEDURE|' + SCHEMA_NAME(p.schema_id) + N'|' + p.name
FROM sys.procedures AS p
WHERE p.name LIKE '%inventor%' OR p.name LIKE '%item%'
   OR p.name LIKE '%char%' OR p.name LIKE '%merit%'
   OR p.name LIKE '%wexp%' OR p.name LIKE '%war%exp%'
ORDER BY p.name;
SELECT TOP (500)
       N'PARAMETER|' + SCHEMA_NAME(p.schema_id) + N'|' + p.name
       + N'|' + a.name + N'|' + ty.name
       + N'|' + CONVERT(nvarchar(10),a.max_length)
       + N'|' + CONVERT(nvarchar(10),a.is_output)
FROM sys.procedures AS p
JOIN sys.parameters AS a ON a.object_id=p.object_id
JOIN sys.types AS ty ON ty.user_type_id=a.user_type_id
WHERE p.name LIKE '%inventor%' OR p.name LIKE '%item%'
   OR p.name LIKE '%char%' OR p.name LIKE '%merit%'
   OR p.name LIKE '%wexp%' OR p.name LIKE '%war%exp%'
ORDER BY p.name,a.parameter_id;
"""
# Password is read INSIDE sql_main and never included in CLI args or stdout.
SH = r"""set -eu
exe=''
for p in /opt/mssql-tools18/bin/sqlcmd /opt/mssql-tools/bin/sqlcmd; do
  if [ -x "$p" ]; then exe="$p"; break; fi
done
if [ -z "$exe" ]; then exit 23; fi
password="$(printenv MSSQL_SA_PASSWORD || printenv SA_PASSWORD || true)"
if [ -z "$password" ]; then exit 24; fi
export SQLCMDPASSWORD="$password"
"$exe" -S localhost -U sa -d Server01 -C -b -W -h -1 -w 2048 -i /dev/stdin
"""
PREFIX_COUNTS = {
    "DATABASE":1, "TABLE":2, "COLUMN":6,
    "PROCEDURE":2, "PARAMETER":6,
}

def decode_sys_catalog(stdout: str):
    rows = {k: [] for k in PREFIX_COUNTS}
    for line in stdout.splitlines():
        value = line.strip()
        if not value or value.startswith("("):
            continue
        prefix = value.split("|",1)[0]
        if prefix not in rows:
            raise ValueError("UNEXPECTED_SQL_OUTPUT")
        cells = value.split("|")[1:]
        if len(cells) != PREFIX_COUNTS[prefix]:
            raise ValueError("INVALID_FIELD_COUNT_" + prefix)
        if any(not c or len(c)>256 for c in cells):
            raise ValueError("INVALID_SQL_METADATA_FIELD")
        rows[prefix].append(cells)
    if rows["DATABASE"] != [[TARGET_DB]]:
        raise ValueError("NOT_EXPECTED_SERVER01_DATABASE")
    return rows

def run():
    try:
        host = subprocess.run(["hostname"],capture_output=True,text=True,timeout=5)
        if host.returncode or host.stdout.strip()!="cabalep33":
            raise ValueError("WRONG_VM_HOSTNAME")
        check = subprocess.run(
            ["docker","inspect","sql_main","--format","{{.State.Running}}"],
            capture_output=True,text=True,timeout=10)
        if check.returncode or check.stdout.strip()!="true":
            raise ValueError("SQL_MAIN_NOT_RUNNING")
        p = subprocess.run(
            ["docker","exec","-i","sql_main","sh","-lc",SH],
            input=SQL,capture_output=True,text=True,timeout=65)
        if p.returncode:
            raise ValueError("SQLCMD_FAILED_EXIT_"+str(p.returncode))
        rows=decode_sys_catalog(p.stdout)
        return {
            "mode":"CABAL_DIAMOND_B0_METADATA_ONLY",
            "status":"PASS",
            "database":TARGET_DB,
            "metadata_only":True,"player_rows_read":False,
            "sql_mutations":False,"worldsvr_changed":False,
            "item_id_for_future_analysis":33554961,
            "actual_world_kind_field38":"0xB0",
            "actual_world_stack_field3c":999,
            "catalog":rows,
            "counts":{key:len(value) for key,value in rows.items()},
            "limit_by_type":{"TABLE":120,"COLUMN":600,
                             "PROCEDURE":180,"PARAMETER":500},
            "result_may_be_truncated": (
                len(rows["TABLE"])>=120 or len(rows["COLUMN"])>=600
                or len(rows["PROCEDURE"])>=180
                or len(rows["PARAMETER"])>=500
            )
        }
    except (ValueError,OSError,subprocess.TimeoutExpired) as ex:
        return {
            "mode":"CABAL_DIAMOND_B0_METADATA_ONLY",
            "status":"STOP","reason":str(ex)[:96],
            "player_rows_read":False,"sql_mutations":False,
            "worldsvr_changed":False
        }

if __name__=="__main__":
    result=run()
    print(json.dumps(result,sort_keys=True,separators=(",",":")))
    sys.exit(0 if result["status"]=="PASS" else 2)
