#!/usr/bin/env python3
"""Offline tests of bounded read-only ticket sample. No SSH, SQL or player data."""
import importlib.util
import json
from pathlib import Path
import re
import unittest

p=Path(__file__).resolve().parents[1]/"probe_live_b0_ticket_options.py"
sp=importlib.util.spec_from_file_location("ticketprobe",p)
probe=importlib.util.module_from_spec(sp)
sp.loader.exec_module(probe)

class TestB0TicketOptionProbe(unittest.TestCase):
    def test_no_writes_or_user_columns_projected(self):
        sql=re.sub(r"--[^\n]*","",probe.SQL)
        self.assertEqual(probe.ITEM_ID,33554961)
        self.assertEqual(probe.MAX_RECORDS,48)
        self.assertIn("SUBSTRING(inv.Data,Slots.n*30+1,4)=0x11020002",sql)
        self.assertIn("SUBSTRING(inv.Data,Slots.n*30+17,8)",sql)
        self.assertIn("TOP (48)",sql)
        self.assertIn("TOP (3)",sql)
        self.assertIn("FROM dbo.cabal_Inventory_table",sql)
        self.assertIsNone(re.search(r"\b(?:UPDATE|DELETE|INSERT|EXEC|MERGE|ALTER|CREATE|DROP|TRUNCATE)\s",sql,re.I))
        self.assertNotIn("SELECT *",sql.upper())
        self.assertNotIn("UserNum",sql)
        self.assertNotIn("ItemSerial",sql)
        self.assertNotIn("Name",sql)
    def test_parser_for_one_ticket_without_inventing_stack_count(self):
        result=probe.parse("BLOB_LENGTH|2790|0\nTICKET_OPTION|2c01000000000000|01000000")
        self.assertEqual(result["anonymous_blob_length_samples"][0]["bytes"],2790)
        row=result["matching_ticket_option_sample"][0]
        self.assertEqual(row["option_low32"],300)
        self.assertEqual(row["item_kind_upper32_value"],1)
        self.assertEqual(row["candidate_low16"],300)
        self.assertEqual(row["candidate_low7"],44)
        self.assertEqual(row["candidate_upper10_of_low32"],0)
        self.assertFalse(result["quantity_codec_verified"])
        self.assertEqual(result["matching_ticket_record_count_in_sample"],1)
        self.assertFalse(result["sample_may_be_truncated"])
    def test_empty_and_limits(self):
        r=probe.parse("BLOB_LENGTH|0|0")
        self.assertFalse(r["matching_ticket_option_sample"])
        self.assertFalse(r["quantity_codec_verified"])
        options="\n".join(["TICKET_OPTION|0000000000000000|00000000"]*49)
        with self.assertRaisesRegex(ValueError,"TOO_MANY_OPTIONS"):
            probe.parse(options)
        with self.assertRaisesRegex(ValueError,"BAD_ITEM_OPTION"):
            probe.parse("TICKET_OPTION|1234|00000000")
        with self.assertRaisesRegex(ValueError,"BAD_ITEM_KIND_FLAGS"):
            probe.parse("TICKET_OPTION|2c01000000000000|1234")
        with self.assertRaisesRegex(ValueError,"UNEXPECTED_OUTPUT"):
            probe.parse("ACCOUNT|1234")
    def test_owner_real_b0_999_fixture_does_not_claim_low10_or_low16(self):
        path=Path(__file__).resolve().parents[1]/"fixtures"/"owner_ep36_291_b0_999_option_observation_20261123.json"
        report=json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(report["real_item_id"],33554961)
        self.assertEqual(report["actual_world_kind_field38"],"0xB0")
        self.assertEqual(report["actual_world_max_stack_field3c"],999)
        self.assertEqual(report["anonymous_inventory_blob_lengths"],[120,1830,210])
        self.assertEqual(report["observed_ticket_records"],2)
        self.assertEqual(report["distinct_character_count"],"unknown")
        self.assertFalse(report["independent_ui_quantity_comparison_done"])
        self.assertFalse(report["low10_or_low16_profile_verified"])
        for sample in report["observed_ticket_options"]:
            self.assertEqual(sample["low10"],999)
            self.assertEqual(sample["low16"],999)
            self.assertEqual(sample["raw_itemOption_64bit_le"],"e703000000000000")
            self.assertEqual(sample["item_kind_hi32_le"],"00000000")
    def test_no_credentials_in_arguments_or_output(self):
        self.assertIn("SQLCMDPASSWORD",probe.SH)
        self.assertIn("MSSQL_SA_PASSWORD",probe.SH)
        self.assertNotIn("-P ",probe.SH)
        self.assertIn("-i /dev/stdin",probe.SH)

if __name__=="__main__":
    unittest.main()
