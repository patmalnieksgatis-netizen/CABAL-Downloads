"""Regression: archived and v14 source patchers MUST NOT double-handle C2S.

An actual 0x09F3 packet still reaches the original WorldSvr dispatcher.
Even a trial-only Diamond shadow debit in that same path is unsafe: it
could debit both shadow and game state. Only the OFFLINE test export may
call the shadow-mutating WorldBridge before protocol/game integration.
"""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

def audit_v14_patcher(text):
    first=text.find("p=replace_one(p,'    UINT16 opcode = header->wMainCmd;")
    end=text.find("        p+='''",first)
    if first<0 or end<first:
        return False
    dispatcher=text[first:end]
    return all([
        "DiamondIngress::Inspect(" in dispatcher,
        "READ_ONLY 0x09F3 candidate" in dispatcher,
        "DiamondBoundIngress::Process(" not in dispatcher,
        "ShadowApplied" not in dispatcher,
        "return DiamondBoundIngress::" not in dispatcher,
        'cabal_diamond_proc_test_ingress_clone_v3' in text[end:],
        'DiamondBoundIngress::Process(' in text[end:],
        '#if defined(DIAMOND_ENABLE_SHADOW_TRIAL)' in text[end:],
    ])

def audit_archived_patcher(text):
    start=text.find('        data=one(data,b\'#include "DiamondIngress.h"')
    end=text.find("        data+=b'''",start)
    if start<0 or end<start:return False
    normal_dispatch=text[start:end]
    return all([
        "if b\"DiamondBoundIngress::Process(\" in data:" in normal_dispatch,
        'raise RuntimeError("STOP: game dispatcher unexpectedly writes Diamond")'
            in normal_dispatch,
        "const auto trial=DiamondBoundIngress::Process" not in normal_dispatch,
        "const auto decision=DiamondBoundIngress::Process" not in normal_dispatch,
        'cabal_diamond_proc_test_ingress_clone_v3' in text[end:],
        'DiamondBoundIngress::Process(' in text[end:],
        '#if defined(DIAMOND_ENABLE_SHADOW_TRIAL)' in text[end:],
    ])

class NoDoubleDebitSourceTests(unittest.TestCase):
    def test_v14_source_clone_observes_game_packets_only(self):
        source=(ROOT/"Apply-DiamondV14BoundClone.py").read_text()
        self.assertTrue(audit_v14_patcher(source))
        unsafe=source.replace(
            'READ_ONLY 0x09F3 candidate; no Diamond write or consume',
            'SYNTHETIC shadow commit; original dispatch untouched'
        ).replace(
            '        if(observation.candidate && DiamondIngress::ShouldLog()) {',
            '        if(observation.candidate) {'
            ' const auto decision=DiamondBoundIngress::Process('
            'pProcessDataCtx->pUserCtx,pProcessDataCtx->cpPacket,'
            'pProcessDataCtx->iLen);'
        )
        self.assertFalse(audit_v14_patcher(unsafe))

    def test_archived_source_clone_observes_game_packets_only(self):
        source=(ROOT/"Apply-DiamondBoundClone.py").read_text()
        self.assertTrue(audit_archived_patcher(source))
        unsafe=source.replace(
            "        data+=b'''",
            '        const auto trial=DiamondBoundIngress::Process('
            "pProcessDataCtx->pUserCtx, pProcessDataCtx->cpPacket, "
            "pProcessDataCtx->iLen);\n        data+=b'''",1)
        self.assertFalse(audit_archived_patcher(unsafe))

if __name__=="__main__":
    unittest.main()
