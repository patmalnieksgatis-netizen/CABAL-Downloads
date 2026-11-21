#!/usr/bin/env python3
"""Pure offline Diamond purchase policy derived from verified EP45 Merit XML.

NOT a WorldSvr handler. State must come from an authoritative server; client
input is untrusted. Unknown LinkedMastery, slot and category activation
semantics fail closed. No SQL, item deduction, bonus grants or category unlock.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping, FrozenSet
import hashlib
import xml.etree.ElementTree as ET

XML_SHA='297078e4cff0918280c824252c4b46e5b17e15a4c57b941b75e8d9f3081c1b9e'

@dataclass(frozen=True)
class MasterySpec:
    index: int
    category: int
    max_level: int
    pre_index: int
    pre_level: int
    linked_index: int
    level_costs: tuple[int, ...]

@dataclass(frozen=True)
class TrustedDiamondState:
    # Caller MUST supply these from verified WorldSvr session/storage.
    badge_grade: int
    unlocked_categories: FrozenSet[int]
    verified_open_mastery_ids: FrozenSet[int]
    levels: Mapping[int,int]
    free_points: int
    row_revision: int
    authoritative: bool=False

@dataclass(frozen=True)
class PurchaseResult:
    allowed: bool
    reason: str
    mastery_id: int
    next_level: int | None=None
    point_cost: int | None=None
    new_state: TrustedDiamondState | None=None
    potential_category_activation: int | None=None

def load_specs(verified_xml:Path)->tuple[dict[int,MasterySpec],dict[int,int]]:
    raw=verified_xml.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=XML_SHA:
        raise ValueError('EP45_DONOR_XML_SHA_MISMATCH')
    root=ET.fromstring(raw)
    assert root.tag=='cabal_merit_system'
    costs_by_id={}
    for mastery in root.find('meritmastery_value'):
        idx=int(mastery.attrib['index'])
        costs_by_id[idx]=tuple(int(v.attrib['req_meritpoint']) for v in mastery)
    specs={}
    for category in root.find('meritmastery_base'):
        if int(category.attrib['Badge_Grade'])!=2:
            continue
        cid=int(category.attrib['index'])
        for mastery in category:
            idx=int(mastery.attrib['mastery_index'])
            assert idx not in specs
            specs[idx]=MasterySpec(
                index=idx,category=cid,max_level=int(mastery.attrib['max_level']),
                pre_index=int(mastery.attrib['premastery_index']),
                pre_level=int(mastery.attrib['premastery_reqlevel']),
                linked_index=int(mastery.attrib['linkedmastery_index']),
                level_costs=costs_by_id[idx])
    assert len(specs)==316 and set(specs)==set(range(159,475))
    activation={int(a.attrib['Mastery_Index']):int(a.attrib['Active_Category'])
                 for a in root.find('SpecialCategory_Active')}
    assert len(activation)==12 and all(mid in specs for mid in activation)
    return specs,activation

def validate_purchase(specs:Mapping[int,MasterySpec],activation:Mapping[int,int],
                      state:TrustedDiamondState,mastery_id:int,*,
                      expected_revision:int)->PurchaseResult:
    def fail(reason:str)->PurchaseResult:
        return PurchaseResult(allowed=False,reason=reason,mastery_id=mastery_id)
    if not state.authoritative:
        return fail('STATE_NOT_SERVER_VERIFIED')
    if state.badge_grade!=2:
        return fail('DIAMOND_BADGE_NOT_UNLOCKED')
    if state.row_revision!=expected_revision or not 0<=expected_revision<2147483647:
        return fail('STALE_OR_INVALID_REVISION')
    for mid,level in state.levels.items():
        node=specs.get(mid)
        if node is None or not isinstance(level,int) or not 0<=level<=node.max_level:
            return fail('INVALID_SERVER_MASTERY_LEVEL_STATE')
    spec=specs.get(mastery_id)
    if spec is None:
        return fail('UNKNOWN_DIAMOND_MASTERY')
    if spec.category not in state.unlocked_categories:
        return fail('DIAMOND_CATEGORY_LOCKED')
    if mastery_id not in state.verified_open_mastery_ids:
        return fail('SLOT_ACCESS_NOT_VERIFIED')
    if spec.linked_index:
        return fail('LINKED_MASTERY_SEMANTICS_NOT_VERIFIED')
    if state.free_points<0:
        return fail('INVALID_POINTS')
    current=state.levels.get(mastery_id,0)
    if not isinstance(current,int) or current<0 or current>=spec.max_level:
        return fail('MAX_LEVEL_OR_INVALID_CURRENT_LEVEL')
    if spec.pre_index and state.levels.get(spec.pre_index,0)<spec.pre_level:
        return fail('PREREQUISITE_NOT_MET')
    cost=spec.level_costs[current]
    if cost<0 or state.free_points<cost:
        return fail('INSUFFICIENT_POINTS')
    # Proposed state ONLY; future native code must commit atomically.
    new_levels=dict(state.levels)
    new_levels[mastery_id]=current+1
    updated=replace(state,levels=new_levels,free_points=state.free_points-cost,
                    row_revision=state.row_revision+1)
    return PurchaseResult(allowed=True,reason='KNOWN_PREREQUISITES_PASS',
                          mastery_id=mastery_id,next_level=current+1,
                          point_cost=cost,new_state=updated,
                          potential_category_activation=activation.get(mastery_id))
