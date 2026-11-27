#!/usr/bin/env python3
"""Offline, no SQL connection. Verify the REAL GameData SQL transaction DRAFT."""
import pathlib
import re
import unittest
PATH=pathlib.Path(__file__).resolve().parent/"00_server01_clone_atomic_rankup_v291.sql"
SQL=PATH.read_text(encoding="utf-8")

class SqlGates(unittest.TestCase):
    def test_clone_install_defaults_to_stop(self):
        self.assertRegex(SQL,r"@ExplicitVerifiedRestorableIsolatedClone bit=0")
        self.assertIn("cabal_diamond_v291_clone_approval",SQL)
        self.assertNotRegex(SQL,r"(?im)^\s*CREATE TABLE dbo\.cabal_diamond_v291_clone_approval")
        self.assertNotRegex(SQL,r"(?im)^\s*GRANT\s+(?:EXECUTE|CONTROL)\s+TO\s+PUBLIC")
    def test_stored_proc_one_serializable_transaction(self):
        proc=SQL.split("CREATE OR ALTER PROCEDURE dbo.cabal_sp_diamond_v291_atomic_rankup",1)[1]
        self.assertEqual(len(re.findall(r"\bBEGIN TRANSACTION\b",proc,re.I)),1)
        self.assertEqual(len(re.findall(r"\bSET TRANSACTION ISOLATION LEVEL SERIALIZABLE\b",proc,re.I)),1)
        self.assertIn("SET XACT_ABORT ON",proc)
        self.assertIn("sys.sp_getapplock",proc)
        self.assertIn("LockOwner='Transaction'",proc)
        self.assertIn("BEGIN CATCH",proc)
        self.assertIn("ROLLBACK TRANSACTION",proc)
        self.assertIn("THROW;",proc)
        self.assertIn("COMMIT TRANSACTION",proc)
    def test_actual_player_state_not_shadow_wallet(self):
        sql=SQL.split("CREATE OR ALTER PROCEDURE dbo.cabal_sp_diamond_v291_atomic_rankup",1)[1]
        for table in ("dbo.cabal_Inventory_table","dbo.cabal_WarExp_Table",
                      "dbo.cabal_diamond_v291_rank_state",
                      "dbo.cabal_diamond_v291_rank_receipt"):
            self.assertIn(table,sql)
        self.assertNotIn("Server01_DiamondLab",sql)
        self.assertNotIn("cabal_diamond_bridge_wallet",sql)
        self.assertIn("CharacterIdx=@CharacterIdx AND Data=@InventoryBefore",sql)
        self.assertIn("WarExp=@WarExpBefore",sql)
        self.assertIn("WarExpEarn=@WarExpEarnBefore",sql)
        self.assertIn("WarExpUsed=@WarExpUsedBefore",sql)
        self.assertIn("UserNum=@UserNum AND CharacterIdx=@CharacterIdx",sql)
        self.assertIn("BadgeGrade=1 AND Revision=@ExpectedRevision",sql)
        self.assertEqual(len(re.findall(r"IF @@ROWCOUNT<>1",sql)),3)
    def test_exact_100_and_30k_rules(self):
        proc=SQL.split("CREATE OR ALTER PROCEDURE dbo.cabal_sp_diamond_v291_atomic_rankup",1)[1]
        self.assertIn("@WarExpAfter<>@WarExpBefore-30000",proc)
        self.assertIn("@VerifiedTicketUnitsAfter<>@VerifiedTicketUnitsBefore-100",proc)
        self.assertIn("AfterInventoryHash",proc)
        self.assertIn("HASHBYTES('SHA2_256',@InventoryAfter)",proc)
        self.assertIn("@Outcome=2",proc) # replay
        self.assertIn("@Outcome=1",proc) # applied
        self.assertIn("@Outcome=0",proc) # failed
        self.assertIn("PRIMARY KEY (UserNum,ExpectedRevision)",SQL)
        self.assertIn("UNIQUE (UserNum,IntentId)",SQL)
        self.assertNotIn("InventoryData",proc) # schema must be exact Data
    def test_no_grant_or_auto_owner_account_creation(self):
        proc=SQL.split("CREATE OR ALTER PROCEDURE dbo.cabal_sp_diamond_v291_atomic_rankup",1)[1]
        self.assertNotIn("GRANT EXECUTE",proc)
        self.assertNotRegex(proc,r"(?i)\bINSERT\s+INTO\s+dbo\.cabal_diamond_v291_rank_state\b")
        self.assertNotRegex(proc,r"(?i)\bUPDATE\s+dbo\.cabal_merit_platinum_table\b")
        self.assertIn("WorldSvr",SQL)
    def test_native_spent_counter_updates_once_and_is_overflow_guarded(self):
        proc=SQL.split("CREATE OR ALTER PROCEDURE dbo.cabal_sp_diamond_v291_atomic_rankup",1)[1]
        self.assertIn("@WarExpUsedBefore>9223372036854745807",proc)
        self.assertIn("SET WarExp=@WarExpAfter,WarExpUsed=@WarExpUsedBefore+30000",proc)
        self.assertNotRegex(proc,r"SET\s+WarExpEarn\s*=")
        self.assertLess(proc.index("SET @Outcome=2"),proc.index("UPDATE dbo.cabal_WarExp_Table"))

if __name__=="__main__":unittest.main()
