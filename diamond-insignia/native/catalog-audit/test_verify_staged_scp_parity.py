"""Synthetic full-row parity tests. No private SCP is committed to GitHub."""
import importlib.util
import sys
from pathlib import Path
import unittest

root=Path(__file__).resolve().parent
sys.path.insert(0,str(root))
import verify_staged_scp_parity as proof

def fake_scp(staged=False,modify_existing=False):
    out=[]
    names=["MeritMastery_Base","MeritMastery_Value","UpGrade_Material",
           "SlotOpen_Material","SlotOpen_Time","SpecialMastery_Material",
           "SpecialMastery_Value","SpecialMastery_Active"]
    for name in names:
        if name=="MeritMastery_Base":
            out.append("[MeritMastery_Base]\tMastery_Category\tBadge_Grade\tMastery_Index")
            out.append("0 1 0 "+("2" if modify_existing else "1"))
            if staged:
                out.extend(f"{i+1} 11 2 {159+i}" for i in range(316))
        elif name=="UpGrade_Material":
            out.append("[UpGrade_Material]\tBadge_Grade\tWexp\tNeed_Item\tNeed_Count")
            out.append("0 1 20000 33554961 100")
            if staged:out.append("1 2 30000 33554961 100")
        else:
            out.append(f"[{name}]\tExample")
            out.append("0 10")
            if staged:
                out.extend(f"{i+1} 10" for i in range(proof.ADDED_EXPECTED[name]))
        out.append("")
    return ("\n".join(out)+"\n").encode()

class StagedTests(unittest.TestCase):
    def test_full_synthetic_staging_parity(self):
        result=proof.compare_scp(fake_scp(),fake_scp(staged=True),False)
        self.assertEqual(result["status"],"STATIC_STAGED_SCP_PARITY_PASS")
        self.assertEqual(result["added_rows_total"],2442)
        self.assertEqual(result["grade_2_mastery_rows"],316)
        self.assertFalse(result["confirmed_gameplay"])

    def test_original_mastery_row_cannot_change(self):
        with self.assertRaisesRegex(proof.CatalogError,"ACTIVE_ROWS_MODIFIED"):
            proof.compare_scp(fake_scp(),fake_scp(True,True),False)

    def test_missing_staged_rows_fails(self):
        data=fake_scp(True).replace(b"1 2 30000 33554961 100\n",b"")
        with self.assertRaisesRegex(proof.CatalogError,"UNEXPECTED_ADDED_ROWS"):
            proof.compare_scp(fake_scp(),data,False)

    def test_exact_source_hash_gate(self):
        with self.assertRaisesRegex(proof.CatalogError,"EXACT_ACTIVE_OR_STAGED_SHA_MISMATCH"):
            proof.compare_scp(fake_scp(),fake_scp(True),True)

if __name__=="__main__":
    unittest.main()
