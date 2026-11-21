#!/usr/bin/env python3
"""Offline text invariants for GitHub Diamond SQL LAB only; NOT a SQL Server test."""
import pathlib,re,unittest
ROOT=pathlib.Path(__file__).resolve().parent
REQUIRED=['01_install_TEST_CLONE_ONLY.sql','02_verify_TEST_CLONE_ONLY.sql',
          '03_rollback_TEST_CLONE_ONLY.sql','04_get_set_contract_TEST_CLONE_ONLY.sql',
          '05_create_diamond_lab_procedures_TEST_CLONE_ONLY.sql',
          '06_transaction_smoke_TEST_CLONE_ONLY.sql',
          '07_remove_diamond_lab_procedures_TEST_CLONE_ONLY.sql']
PROCS=['cabal_diamond_lab_init_v1','cabal_diamond_lab_get_v1',
       'cabal_diamond_lab_commit_v1']
def scrub(s):
 s=re.sub(r'/\*.*?\*/','',s,flags=re.S)
 return '\n'.join(line.split('--')[0] for line in s.splitlines())
def compact(s):return re.sub(r'\s+','',scrub(s)).lower()
def validate(d):
 for fname in REQUIRED:
  assert fname in d,('MISSING',fname)
  if fname==REQUIRED[3]:continue
  s=compact(d[fname])
  assert 'use[server01_diamondlab];' in s
  assert "ifdb_name()<>n'server01_diamondlab'" in s
  assert 'use[server01];' not in s
  for verb in ('updatedbo.cabal_merit_platinum_table','updatedbo.cabal_merit_table',
               'deletefromdbo.cabal_merit_platinum_table',
               'insertintodbo.cabal_merit_platinum_table'):
   assert verb not in s,('LEGACY_SQL_WRITE',fname,verb)
 proc=compact(d[REQUIRED[4]])
 for name in PROCS:
  assert proc.count('createproceduredbo.'+name)==1,name
 assert 'androwrevision=@expectedrowrevision' in proc
 assert 'rowrevision=rowrevision+1' in proc
 assert 'anddiamondunlocked=1' in proc
 assert 'whereusernum=@usernum' in proc
 assert 'havemeritplatinumbagde=1' in proc
 assert 'if@@rowcount<>1' in proc
 assert 'with(updlock,holdlock)' in proc
 assert 'setxact_aborton' in proc
 assert 'rollbacktransaction' in proc
 assert not re.search(r'\bgrant\b',scrub(d[REQUIRED[4]]),re.I)
 assert 'createproceduredbo.cabal_tool_' not in proc
 assert '2147483600' in d[REQUIRED[5]] and 'ROLLBACK TRANSACTION' in d[REQUIRED[5]]
 for name in PROCS:assert 'dropproceduredbo.'+name in compact(d[REQUIRED[6]])
 assert 'droptable' not in compact(d[REQUIRED[6]])
 return True
class TestLabSafety(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.f={p.name:p.read_text(encoding='utf8') for p in ROOT.glob('*.sql')}
 def assertBad(self,filename,src,repl):
  d=dict(self.f);d[filename]=d[filename].replace(src,repl)
  with self.assertRaises(AssertionError):validate(d)
 def test_original(self):self.assertTrue(validate(self.f))
 def test_missing_file(self):
  d=dict(self.f);d.pop(REQUIRED[5])
  with self.assertRaises(AssertionError):validate(d)
 def test_wrong_database(self):self.assertBad(REQUIRED[4],'Server01_DiamondLab','Server01')
 def test_missing_revision_guard(self):self.assertBad(REQUIRED[4],'AND RowRevision=@ExpectedRowRevision','AND 1=1')
 def test_missing_badge_guard(self):self.assertBad(REQUIRED[4],'AND DiamondUnlocked=1','AND 1=1')
 def test_missing_platinum_prerequisite(self):self.assertBad(REQUIRED[4],'AND HaveMeritPlatinumBagde=1','AND 1=1')
 def test_tainted_legacy_write(self):
  d=dict(self.f);d[REQUIRED[4]]+='\nUPDATE dbo.cabal_merit_platinum_table SET MeritPlatinumPoint=0;'
  with self.assertRaises(AssertionError):validate(d)
 def test_unwanted_grant(self):
  d=dict(self.f);d[REQUIRED[4]]+='\nGRANT EXECUTE ON dbo.cabal_diamond_lab_commit_v1 TO public;'
  with self.assertRaises(AssertionError):validate(d)
 def test_bad_rollback(self):self.assertBad(REQUIRED[5],'ROLLBACK TRANSACTION','COMMIT TRANSACTION')
 def test_missing_proc_drop(self):self.assertBad(REQUIRED[6],
   'DROP PROCEDURE dbo.cabal_diamond_lab_get_v1','PRINT 1')
if __name__=='__main__':unittest.main(verbosity=2)
