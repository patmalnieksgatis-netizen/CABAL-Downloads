#!/usr/bin/env python3
"""Read-only bounded deidentified 0xB0/999 Merit Ticket option sampling.

This is a TARGETED GAME INVENTORY QUERY, NOT metadata-only. It reads
cabal_Inventory_table.Data but returns only item 33554961's raw 8-byte
ItemOption values (capped at 48), and 3 anonymous blob lengths.
Never returns CharacterIdx, UserNum, name, serial, full inventory
blob, IP, credential, or non-ticket data. No DB modifications.
Run only on the owner's EP36_291_TEST VM.
"""
from __future__ import annotations
import json
import subprocess
import sys

ITEM_ID=33554961  # 0x02000211
MAX_RECORDS=48
SQL=r"""
SET NOCOUNT ON;
SET LOCK_TIMEOUT 3000;
SET DEADLOCK_PRIORITY LOW;
-- Summarize only lengths, not character identifiers or inventory blobs.
SELECT TOP (3) N'BLOB_LENGTH|' + CONVERT(nvarchar(12),DATALENGTH(Data))
  + N'|' + CONVERT(nvarchar(12),DATALENGTH(Data) % 30)
FROM dbo.cabal_Inventory_table
WHERE Data IS NOT NULL
ORDER BY CharacterIdx;
-- v14 independently identified 30-byte GameData rows:
-- itemId +0 (8 bytes), itemSerial +8 (8), itemOption +16 (8),
-- physicalSlot +24 (2), duration +26 (4).
-- Restrict projection to ItemOption of exact 33554961 matches.
-- 0x02000211 as little-endian QWORD = 0x1102000200000000.
WITH Slots AS (
 SELECT TOP (522)
   CONVERT(int,ROW_NUMBER() OVER(ORDER BY (SELECT NULL)))-1 AS n
 FROM sys.all_objects AS a CROSS JOIN sys.all_objects AS b
)
SELECT TOP (48)
       N'TICKET_OPTION|' +
       CONVERT(varchar(16),SUBSTRING(inv.Data,Slots.n*30+17,8),2)
FROM dbo.cabal_Inventory_table AS inv
CROSS JOIN Slots
WHERE inv.Data IS NOT NULL
  AND DATALENGTH(inv.Data) % 30=0
  AND DATALENGTH(inv.Data)>=Slots.n*30+30
  AND SUBSTRING(inv.Data,Slots.n*30+1,8)=0x1102000200000000
OPTION (MAXDOP 1);
"""
# Only local sql_main; credential never appears in CLI or stdout.
SH=r"""set -eu
exe=''
for p in /opt/mssql-tools18/bin/sqlcmd /opt/mssql-tools/bin/sqlcmd; do
  if [ -x "$p" ]; then exe="$p"; break; fi
done
if [ -z "$exe" ]; then exit 23; fi
password="$(printenv MSSQL_SA_PASSWORD || printenv SA_PASSWORD || true)"
if [ -z "$password" ]; then exit 24; fi
export SQLCMDPASSWORD="$password"
"$exe" -S localhost -U sa -d Server01 -C -b -W -h -1 -w 1024 -i /dev/stdin
"""
def parse(output):
    lengths=[]
    options=[]
    for line in output.splitlines():
        v=line.strip()
        if not v or v.startswith("("): continue
        parts=v.split("|")
        if parts[0]=="BLOB_LENGTH" and len(parts)==3:
            length,remainder=parts[1:]
            if not length.isdigit() or not remainder.isdigit():
                raise ValueError("BAD_LENGTH_RECORD")
            if len(lengths)>=3:
                raise ValueError("TOO_MANY_LENGTHS")
            lengths.append({"bytes":int(length),"mod30":int(remainder)})
        elif parts[0]=="TICKET_OPTION" and len(parts)==2:
            token=parts[1]
            if len(token)!=16 or any(x not in "0123456789abcdefABCDEF" for x in token):
                raise ValueError("BAD_ITEM_OPTION")
            if len(options)>=MAX_RECORDS:
                raise ValueError("TOO_MANY_OPTIONS")
            raw=int.from_bytes(bytes.fromhex(token),"little")
            options.append({
                "raw_option_le_hex":"0x"+token.lower(),
                "option_low32":raw & 0xffffffff,
                "candidate_low16":raw & 0xffff,
                "candidate_low10":raw & 0x3ff,
                "candidate_upper10_of_low32":(raw>>22)&0x3ff,
                "candidate_low7":raw & 0x7f,
                "candidate_high32":(raw>>32)&0xffffffff
            })
        else:
            raise ValueError("UNEXPECTED_OUTPUT_TYPE")
    return {"anonymous_blob_length_samples":lengths,
            "matching_ticket_option_sample":options,
            "matching_ticket_record_count_in_sample":len(options),
            "sampling_limit":MAX_RECORDS,
            "sample_may_be_truncated":len(options)>=MAX_RECORDS,
            "quantity_codec_verified":False,
            "note":"Raw real ticket options only. Candidate values are hypotheses, NOT proven counts."}
def run():
    safety={"mode":"CABAL_291_B0_TICKET_RAW_OPTIONS",
            "read_only":True,"target_item_id":ITEM_ID,
            "player_identifiers_exported":False,
            "item_serials_exported":False,"sql_mutations":False,
            "status":"STOP"}
    try:
        host=subprocess.run(["hostname"],capture_output=True,text=True,timeout=5)
        if host.returncode or host.stdout.strip()!="cabalep33":
            raise ValueError("WRONG_VM")
        check=subprocess.run(
            ["docker","inspect","sql_main","--format","{{.State.Running}}"],
            capture_output=True,text=True,timeout=8)
        if check.returncode or check.stdout.strip()!="true":
            raise ValueError("SQL_NOT_RUNNING")
        result=subprocess.run(["docker","exec","-i","sql_main","sh","-lc",SH],
                              input=SQL,capture_output=True,text=True,timeout=90)
        if result.returncode:
            raise ValueError("SQLCMD_FAILED_"+str(result.returncode))
        safety.update(parse(result.stdout))
        safety["status"]="PASS"
    except (ValueError,OSError,subprocess.TimeoutExpired) as exc:
        safety["reason"]=str(exc)[:100]
    return safety
if __name__=="__main__":
    out=run()
    print(json.dumps(out,sort_keys=True,separators=(",",":")))
    raise SystemExit(0 if out["status"]=="PASS" else 2)
