import csv
import tempfile
import unittest
from pathlib import Path
from audit_procmon_merit_paths import parse_csv

FIELDS = ["Time of Day", "Process Name", "PID", "Operation", "Path", "Result", "Detail"]
def csvfile(root, rows):
    p = Path(root) / "procmon.csv"
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for row in rows: w.writerow(row)
    return p

def item(name, operation, path, result="SUCCESS", pid="42"):
    return {"Time of Day": "10:20:30.0000000", "Process Name": name, "PID": pid,
            "Operation": operation, "Path": path, "Result": result, "Detail": ""}

class TestMeritRuntimePaths(unittest.TestCase):
    def test_successful_open_not_same_as_read(self):
        with tempfile.TemporaryDirectory() as d:
            p=csvfile(d,[
                item("CabalMain.exe", "CreateFile", r"F:\CABAL_291_TEST\Data\meritsystem.enc"),
                item("CabalMain.exe", "ReadFile", r"F:\CABAL_291_TEST\Data\meritsystem.enc"),
                item("CabalMain.exe", "CreateFile", r"F:\CABAL_291_TEST\Language\meritsystem.enc","NAME NOT FOUND"),
                item("explorer.exe", "ReadFile", r"F:\CABAL_291_TEST\Data\meritsystem_msg.enc"),
                item("CabalMain.exe", "CreateFile", r"F:\CABAL_291_TEST\Data\unrelated.enc"),
                item("CabalMain.exe", "CreateFile", r"F:\CABAL_291_TEST\Data\meritsystem_msg.enc"),
            ])
            r=parse_csv(p)
            self.assertEqual(r["opened_path_count"],2)
            self.assertEqual(r["read_path_count"],1)
            self.assertEqual(sum(x["open_failure"] for x in r["matched_paths"]),1)
            self.assertFalse(r["game_files_modified"])
            self.assertTrue(r["not_proven"])
    def test_denied_open_not_proof(self):
        with tempfile.TemporaryDirectory() as d:
            r=parse_csv(csvfile(d,[item("CabalMain.exe","CreateFile",r"C:\foo\meritsystem.enc","ACCESS DENIED")]))
            self.assertEqual(r["opened_path_count"],0)
            self.assertEqual(len(r["matched_paths"]),1)
    def test_invalid_headers(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"bad.csv";p.write_text("Path,Operation\na,b\n")
            with self.assertRaisesRegex(ValueError,"supported"):parse_csv(p)
    def test_utf8_bom_and_casefold(self):
        with tempfile.TemporaryDirectory() as d:
            p=csvfile(d,[item("CABALMAIN.EXE","ReadFile",r"C:\Other\MERITSYSTEM_MSG.ENC")])
            r=parse_csv(p)
            self.assertEqual(r["read_path_count"],1)
            self.assertEqual(r["opened_path_count"],0)
if __name__ == "__main__": unittest.main()
