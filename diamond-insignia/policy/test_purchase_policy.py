#!/usr/bin/env python3
"""No donor game files needed: synthetic, immutable Diamond policy tests."""
import sys,unittest
from dataclasses import replace
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from diamond_purchase_policy import MasterySpec,TrustedDiamondState,validate_purchase

def sample():
    specs={
      159:MasterySpec(159,11,5,0,0,0,(1,2,3,4,5)),
      160:MasterySpec(160,11,5,159,3,0,(1,1,1,1,1)),
      161:MasterySpec(161,12,5,159,4,162,(1,1,1,1,1))}
    s=TrustedDiamondState(2,frozenset({11,12}),frozenset({159,160,161}),{},
                           100,5,authoritative=True)
    return specs,s

class TestPolicy(unittest.TestCase):
    def check(self,i=159,st=None,rev=5):
        specs,s=sample()
        return validate_purchase(specs,{},s if st is None else st,i,
                                 expected_revision=rev)
    def test_purchase_first_level(self):
        result=self.check()
        self.assertTrue(result.allowed)
        self.assertEqual(result.new_state.levels[159],1)
        self.assertEqual(result.new_state.free_points,99)
        self.assertEqual(result.new_state.row_revision,6)
    def test_unverified_source_rejected(self):
        _,s=sample()
        self.assertEqual(self.check(st=replace(s,authoritative=False)).reason,'STATE_NOT_SERVER_VERIFIED')
    def test_platinum_only_rejected(self):
        _,s=sample()
        self.assertEqual(self.check(st=replace(s,badge_grade=1)).reason,'DIAMOND_BADGE_NOT_UNLOCKED')
    def test_stale_rejected(self):
        self.assertEqual(self.check(rev=4).reason,'STALE_OR_INVALID_REVISION')
    def test_no_slot(self):
        _,s=sample()
        self.assertEqual(self.check(st=replace(s,verified_open_mastery_ids=frozenset())).reason,'SLOT_ACCESS_NOT_VERIFIED')
    def test_no_category(self):
        _,s=sample()
        self.assertEqual(self.check(st=replace(s,unlocked_categories=frozenset())).reason,'DIAMOND_CATEGORY_LOCKED')
    def test_linked_unknown_is_blocked(self):
        self.assertEqual(self.check(i=161).reason,'LINKED_MASTERY_SEMANTICS_NOT_VERIFIED')
    def test_requires_parent_level(self):
        self.assertEqual(self.check(i=160).reason,'PREREQUISITE_NOT_MET')
        _,s=sample()
        self.assertTrue(self.check(i=160,st=replace(s,levels={159:3})).allowed)
    def test_no_points(self):
        _,s=sample()
        self.assertEqual(self.check(st=replace(s,free_points=0)).reason,'INSUFFICIENT_POINTS')
    def test_rejects_invalid_masters(self):
        _,s=sample()
        self.assertEqual(self.check(st=replace(s,levels={159:99})).reason,'INVALID_SERVER_MASTERY_LEVEL_STATE')
    def test_does_not_change_original(self):
        _,s=sample()
        result=self.check()
        self.assertEqual(s.levels,{})
        self.assertEqual(s.free_points,100)
        self.assertEqual(s.row_revision,5)
        self.assertTrue(result.allowed)

if __name__=='__main__':unittest.main(verbosity=2)
