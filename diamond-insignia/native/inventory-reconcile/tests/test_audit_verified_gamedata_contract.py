#!/usr/bin/env python3
"""Offline exact GameData contract read-only tests. No network, no SQL."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import re
import unittest

SCRIPT=Path(__file__).resolve().parent.parent / "audit_verified_gamedata_contract.py"
spec=importlib.util.spec_from_file_location("contract",SCRIPT)
contract=importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)

class GameContractTests(unittest.TestCase):
    def test_no_game_rows_no_writes(self):
        sql=contract.SQL
        self.assertIn("sys.tables",sql)
        self.assertIn("sys.sql_modules",sql)
        self.assertIn("sys.index_columns",sql)
        self.assertIn("sys.parameters",sql)
        # Only SQL Server system catalog sources may appear in FROM / JOIN.
        for name in re.findall(r"\b(?:FROM|JOIN)\s+([\w.]+)",sql,re.I):
            self.assertTrue(name.lower().startswith("sys."),name)
        self.assertIsNone(re.search(
            r"\b(?:UPDATE|DELETE|INSERT|ALTER|DROP|EXEC|EXECUTE|MERGE|TRUNCATE)\s",
            sql,re.I))
        self.assertNotIn("select *",sql.lower())
        self.assertNotIn("Server01_DiamondLab",sql)
        self.assertNotIn("sys.sp_executesql",sql)
    def test_selection_aligned_with_real_schema_observation(self):
        self.assertIn("cabal_Inventory_table",contract.TABLES)
        self.assertIn("cabal_WarExp_Table",contract.TABLES)
        self.assertIn("cabal_merit_platinum_table",contract.TABLES)
        self.assertIn("cabal_tool_inventory_set",contract.PROCEDURES)
        self.assertIn("Cabal_Sp_InstantWar_SetWarExp",contract.PROCEDURES)
    def test_valid_contract_parser(self):
        sample="\n".join((
            "DATABASE|Server01",
            "TABLE|dbo|cabal_Inventory_table",
            "COLUMN|dbo|cabal_Inventory_table|CharacterIdx|int|4|0",
            "COLUMN|dbo|cabal_Inventory_table|Data|varbinary|-1|1",
            "TABLE|dbo|cabal_WarExp_Table",
            "COLUMN|dbo|cabal_WarExp_Table|WarExp|bigint|8|0",
            "INDEX|dbo|cabal_Inventory_table|PK_Inventory|1|1|1|CharacterIdx",
            "PROCEDURE|dbo|cabal_tool_inventory_set",
            "PARAMETER|dbo|cabal_tool_inventory_set|@Data|varbinary|-1|0",
            "MODULE|dbo|cabal_tool_inventory_set|100|1|1|0|1|0|0"
        ))
        result=contract.parse(sample)
        self.assertEqual(result["COLUMN"][1][2:4],["Data","varbinary"])
        self.assertEqual(result["MODULE"][0][-3:],["1","0","0"])
        self.assertEqual(result["INDEX"][0][4],"1")
    def test_fail_closed_bad_database_procedure_and_shape(self):
        with self.assertRaisesRegex(ValueError,"WRONG_DATABASE"):
            contract.parse("DATABASE|master\nTABLE|dbo|cabal_Inventory_table")
        with self.assertRaisesRegex(ValueError,"UNEXPECTED_CATALOG_ITEM"):
            contract.parse("DATABASE|Server01\nTABLE|dbo|anything_else")
        with self.assertRaisesRegex(ValueError,"UNEXPECTED_SQL_OUTPUT"):
            contract.parse("DATABASE|Server01\nPLAYER_ROW|123|user")
        with self.assertRaisesRegex(ValueError,"WRONG_FIELD_COUNT"):
            contract.parse("DATABASE|Server01\nINDEX|dbo|cabal_Inventory_table|PK")
        with self.assertRaisesRegex(ValueError,"UNEXPECTED_SCHEMA"):
            contract.parse("DATABASE|Server01\nTABLE|Account|cabal_Inventory_table")
    def test_secrets_not_in_logs_or_args(self):
        self.assertIn("SQLCMDPASSWORD",contract.SQLCMD_SH)
        self.assertIn("MSSQL_SA_PASSWORD",contract.SQLCMD_SH)
        self.assertNotIn("-P ",contract.SQLCMD_SH)
        self.assertIn("-i /dev/stdin",contract.SQLCMD_SH)
        self.assertEqual(contract.SUSPECT_DEFAULTS["sql_mutations"],False)

if __name__=="__main__":
    unittest.main()
