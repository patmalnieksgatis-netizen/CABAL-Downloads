#!/usr/bin/env python3
"""Read-only SQL metadata auditor test; NO Docker or MSSQL connections."""
import importlib.util
import pathlib
import re
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "audit_live_inventory_schema.py"
spec = importlib.util.spec_from_file_location("schema_audit",SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

class CatalogTests(unittest.TestCase):
    def test_queries_select_only_sys_metadata(self):
        self.assertEqual(audit.TARGET_DB,"Server01")
        sql=audit.SQL
        self.assertIn("DB_NAME()",sql)
        self.assertEqual(len(re.findall(r"\bSELECT\b",sql,re.I)),5)
        self.assertFalse(re.search(
            r"\b(?:UPDATE|DELETE|INSERT|MERGE|TRUNCATE|DROP|ALTER|CREATE|EXEC|EXECUTE)\b",
            sql,re.I))
        targets=re.findall(r"\b(?:FROM|JOIN)\s+([\w.]+)",sql,re.I)
        self.assertGreaterEqual(len(targets),4)
        for name in targets:
            self.assertTrue(name.lower().startswith("sys."),name)
        # This test must NOT shell out to any real SQL server.
        self.assertNotIn("SELECT *",sql.upper())
    def test_known_metadata_rows(self):
        sample="\n".join((
            "DATABASE|Server01",
            "TABLE|dbo|cabal_character_table",
            "COLUMN|dbo|cabal_character_table|WarExp|bigint|8|0",
            "PROCEDURE|dbo|cabal_sp_eventpass_inventory_snapshot_v282",
            "PARAMETER|dbo|cabal_sp_eventpass_inventory_snapshot_v282|@CharacterIdx|int|4|0"
        ))
        result=audit.decode_sys_catalog(sample)
        self.assertEqual(result["DATABASE"],[["Server01"]])
        self.assertEqual(result["TABLE"],[["dbo","cabal_character_table"]])
        self.assertEqual(result["COLUMN"][0][-3:],["bigint","8","0"])
    def test_reject_player_data_and_wrong_database(self):
        with self.assertRaisesRegex(ValueError,"NOT_EXPECTED"):
            audit.decode_sys_catalog("DATABASE|Account\n")
        with self.assertRaisesRegex(ValueError,"UNEXPECTED"):
            audit.decode_sys_catalog("DATABASE|Server01\nUSER_NUM|900001")
        with self.assertRaisesRegex(ValueError,"INVALID_FIELD_COUNT"):
            audit.decode_sys_catalog("DATABASE|Server01\nCOLUMN|dbo|something")
        with self.assertRaisesRegex(ValueError,"INVALID_SQL_METADATA_FIELD"):
            audit.decode_sys_catalog("DATABASE|Server01\nTABLE|dbo|")
    def test_password_not_in_stdout_or_cli_args(self):
        self.assertIn("SQLCMDPASSWORD",audit.SH)
        self.assertIn("MSSQL_SA_PASSWORD",audit.SH)
        self.assertNotIn("-P ",audit.SH)
        self.assertNotIn("cat /",audit.SH)
        self.assertIn("-d Server01",audit.SH)
        self.assertIn("-i /dev/stdin",audit.SH)

if __name__=="__main__":
    unittest.main()
