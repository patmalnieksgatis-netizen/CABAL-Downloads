import importlib.util
from pathlib import Path
import re
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('temp_rankup',HERE/'test_rankup_in_temp_tables.py')
runner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
SOURCE=(HERE/'00_server01_clone_atomic_rankup_v291.sql').read_text()


class TemporarySqlTests(unittest.TestCase):
    def test_actual_procedure_body_is_used(self):
        generated=runner.build_sql(SOURCE,'0123456789abcdef')
        self.assertIn('CREATE PROCEDURE #diamond_rankup',generated)
        self.assertIn('SET WarExp=@WarExpAfter,WarExpUsed=@WarExpUsedBefore+30000',generated)
        self.assertIn("N'DiamondTempTest:0123456789abcdef:User:'",generated)
        self.assertNotIn("N'DiamondV291:User:'",generated)
        self.assertNotIn('CREATE TABLE dbo.',generated)
        self.assertNotIn('ALTER TABLE dbo.',generated)
        code=re.sub(r'--[^\r\n]*','',generated)
        self.assertNotRegex(code,r'(?i)\bdbo\s*\.')
        self.assertIn('DIAMOND_TEMP_SQL_ATOMIC_ROLLBACK=PASS',generated)
        self.assertIn('DIAMOND_TEMP_SQL_OVERFLOW=PASS',generated)
        self.assertIn('DIAMOND_TEMP_SQL_STALE_COUNTERS=PASS',generated)

    def test_non_temp_reference_rejected(self):
        bad=SOURCE.replace('    SET NOCOUNT ON;', '    SET NOCOUNT ON; SELECT * FROM dbo.cabal_auth_table;')
        with self.assertRaisesRegex(ValueError,'NON_TEMP_SCHEMA_REFERENCE'):
            runner.build_sql(bad,'0123456789abcdef')

    def test_invalid_namespace_or_source_rejected(self):
        with self.assertRaises(ValueError):
            runner.build_sql(SOURCE,"'; SELECT 1;--")
        with self.assertRaises(ValueError):
            runner.build_sql('', '0123456789abcdef')


if __name__=='__main__':
    unittest.main()
