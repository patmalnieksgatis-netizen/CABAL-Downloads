import csv
import tempfile
import unittest
from pathlib import Path

from correlate_procmon_merit_assets import correlate
from test_audit_merit_candidates import fixture, make_enc

FIELDS = ["Time of Day", "Process Name", "PID", "Operation", "Path", "Result"]
ROOT = r"F:\CABAL_291_TEST"

def setup(d, events):
    directory=Path(d)
    archive=directory/"collected.zip"
    archive.write_bytes(fixture(make_enc(b"MeritFixture"*200),
                                path="Data/meritsystem.enc").getvalue())
    procmon=directory/"file-events.csv"
    with procmon.open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS)
        writer.writeheader()
        for operation,path,result in events:
            writer.writerow({"Time of Day":"10:00:00.000","Process Name":"CabalMain.exe",
                             "PID":"321","Operation":operation,"Path":path,"Result":result})
    return procmon,archive

class TestCorrelateProcmon(unittest.TestCase):
    def test_actual_open_correlates_inventory_but_not_decoding(self):
        with tempfile.TemporaryDirectory() as d:
            path=ROOT+r"\Data\meritsystem.enc"
            proc,assets=setup(d,[("QueryOpen",path,"SUCCESS"),
                                 ("CreateFile",path,"SUCCESS"),
                                 ("ReadFile",path,"SUCCESS")])
            r=correlate(proc,assets,ROOT)
            self.assertEqual(r["confirmed_open_matching_collected_path_count"],1)
            self.assertEqual(r["observations"][0]["classification"],"opened_and_read")
            self.assertTrue(r["observations"][0]["matches_collected_asset"])
            self.assertFalse(r["actual_runtime_byte_identity_proven"])
            self.assertFalse(r["actual_decode_success_proven"])
    def test_query_only_never_proves_open(self):
        with tempfile.TemporaryDirectory() as d:
            proc,assets=setup(d,[("QueryOpen",ROOT+r"\Data\meritsystem.enc","SUCCESS")])
            r=correlate(proc,assets,ROOT)
            self.assertEqual(r["confirmed_open_matching_collected_path_count"],0)
            self.assertEqual(r["observations"][0]["classification"],"query_only")
    def test_uncollected_path_is_not_sha_matched(self):
        with tempfile.TemporaryDirectory() as d:
            proc,assets=setup(d,[("CreateFile",r"G:\OTHER\meritsystem.enc","SUCCESS")])
            r=correlate(proc,assets,ROOT)
            self.assertFalse(r["observations"][0]["matches_collected_asset"])
            self.assertIsNone(r["observations"][0]["asset_sha256"])
    def test_casefolded_windows_path_matches(self):
        with tempfile.TemporaryDirectory() as d:
            proc,assets=setup(d,[("CreateFile",r"f:\cabal_291_test\DATA\MERITSYSTEM.ENC","SUCCESS")])
            r=correlate(proc,assets,ROOT)
            self.assertEqual(r["confirmed_open_matching_collected_path_count"],1)
    def test_relative_root_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            proc,assets=setup(d,[])
            with self.assertRaisesRegex(ValueError,"absolute"):
                correlate(proc,assets,"test/client")
if __name__=="__main__":
    unittest.main()
