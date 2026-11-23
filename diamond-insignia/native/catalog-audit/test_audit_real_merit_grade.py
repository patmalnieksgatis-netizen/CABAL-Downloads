"""Public CI uses only miniature synthetic SCP text; no private resources."""
import importlib.util
from pathlib import Path
import unittest

src=Path(__file__).with_name("audit_real_merit_grade.py")
spec=importlib.util.spec_from_file_location("audit_grade",src)
audit_grade=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_grade)

PLATINUM=(
    "[MeritMastery_Base]\tMastery_Category\tBadge_Grade\tMastery_Type\t"
    "Mastery_Index\tMax_Level\tPreMastery_Index\tPreMastery_Level\tLinkedMastery_Index\n"
    "0\t1\t0\t1\t1\t5\t0\t0\t0\n"
    "1\t5\t1\t1\t2\t5\t0\t0\t0\n"
    "\n[UpGrade_Material]\tBadge_Grade\tWexp\tNeed_Item\tNeed_Count\n"
    "0\t1\t20000\t33554961\t100\n"
)
DIAMOND_ROW="2\t11\t2\t1\t159\t10\t0\t0\t0\n"
DIAMOND_UPGRADE="1\t2\t30000\t33554961\t100\n"

class GradeAuditTests(unittest.TestCase):
    def test_current_scp_shape_not_installable(self):
        r=audit_grade.audit(PLATINUM.encode())
        self.assertEqual(r["mastery_grade_counts"],{"0":1,"1":1})
        self.assertFalse(r["diamond_config_candidate"])
        self.assertEqual(r["status"],"BLOCKED_BY_SCP")
        self.assertFalse(r["installable_product_confirmed"])

    def test_diamond_candidate_is_still_not_gameplay(self):
        raw=(PLATINUM.replace("\n[UpGrade_Material]",
                              DIAMOND_ROW+"\n[UpGrade_Material]")
                    +DIAMOND_UPGRADE)
        r=audit_grade.audit(raw.encode())
        self.assertEqual(r["diamond_mastery_rows"],1)
        self.assertEqual(r["status"],"CONFIG_CANDIDATE_ONLY")
        self.assertTrue(r["diamond_config_candidate"])
        self.assertFalse(r["installable_product_confirmed"])

    def test_missing_upgrade_does_not_pass(self):
        raw=PLATINUM.replace("\n[UpGrade_Material]",
                              DIAMOND_ROW+"\n[UpGrade_Material]")
        r=audit_grade.audit(raw.encode())
        self.assertEqual(r["status"],"BLOCKED_BY_SCP")

    def test_duplicate_index_and_mastery_rejected(self):
        raw=PLATINUM.replace("1\t5\t1\t1\t2", "0\t5\t1\t1\t2")
        with self.assertRaisesRegex(audit_grade.CatalogError,"DUPLICATE_RECORD_INDEX"):
            audit_grade.audit(raw.encode())
        raw=PLATINUM.replace("1\t5\t1\t1\t2", "1\t5\t1\t1\t1")
        with self.assertRaisesRegex(audit_grade.CatalogError,"DUPLICATE_MASTERY_ID"):
            audit_grade.audit(raw.encode())

    def test_missing_grade_column_and_bad_row_rejected(self):
        raw=PLATINUM.replace("Badge_Grade\t","Unknown_Grade\t",1)
        with self.assertRaisesRegex(audit_grade.CatalogError,"MISSING_HEADER_Badge_Grade"):
            audit_grade.audit(raw.encode())
        raw=PLATINUM.replace("1\t5\t1\t1\t2\t5\t0\t0\t0",
                              "1\t5\t1\t1\t2")
        with self.assertRaisesRegex(audit_grade.CatalogError,"ROW_FIELD_COUNT"):
            audit_grade.audit(raw.encode())

if __name__=="__main__":
    unittest.main()
