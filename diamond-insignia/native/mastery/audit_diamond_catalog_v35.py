#!/usr/bin/env python3
"""Validate the donor XML against staged TSVs; export offline rules fixtures.
No server connection, binary modification, or deployment.
"""
import argparse
import collections
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


def audit(path):
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read('decoded_ep45/EP45_meritsystem.xml'))
        def tsv(name):
            return [tuple(map(int, line.split('\t'))) for line in
                    z.read('delta/' + name + '_NEW_ONLY.tsv').decode().splitlines() if line.strip()]
        base = tsv('MeritMastery_Base')
        values = tsv('MeritMastery_Value')
        upgrade = tsv('UpGrade_Material')
    catalog = {}
    expected_base = []
    for category in root.findall('./meritmastery_base/mastery_category'):
        if int(category.attrib['Badge_Grade']) != 2:
            continue
        c = int(category.attrib['index'])
        for row in category.findall('mastery_base'):
            a = row.attrib
            i = int(a['mastery_index'])
            if i in catalog:
                raise ValueError('Duplicate mastery ID')
            m = dict(id=i, category=c, max_level=int(a['max_level']),
                     prerequisite_id=int(a['premastery_index']),
                     prerequisite_level=int(a['premastery_reqlevel']),
                     linked_id=int(a['linkedmastery_index']),
                     level_cost=[])
            catalog[i] = m
            expected_base.append((c, 2, int(a['mastery_type']), i, m['max_level'],
                                  m['prerequisite_id'], m['prerequisite_level'], m['linked_id']))
    if [r[1:] for r in base] != expected_base:
        raise ValueError('Base XML/TSV mismatch')
    if set(catalog) != set(range(159, 475)):
        raise ValueError('Unexpected mastery IDs')
    expected_values = []
    seen = set()
    for mastery in root.findall('./meritmastery_value/mastery'):
        i = int(mastery.attrib['index'])
        if i not in catalog:
            continue
        if i in seen:
            raise ValueError('Duplicate value group')
        seen.add(i)
        for index, value in enumerate(mastery.findall('value'), 1):
            a = value.attrib
            if int(a['mastery_level']) != index:
                raise ValueError('Non-contiguous mastery levels')
            cost = int(a['req_meritpoint'])
            if cost < 0:
                raise ValueError('Negative cost')
            catalog[i]['level_cost'].append(cost)
            expected_values.append((int(a['mastery_level']), i, cost))
    if [(r[3], r[2], r[4]) for r in values] != expected_values:
        raise ValueError('Level/cost XML/TSV mismatch')
    for i,m in catalog.items():
        if len(m['level_cost']) != m['max_level']:
            raise ValueError('Missing level costs')
        visited = set()
        cur = i
        while cur:
            if cur in visited or cur not in catalog:
                raise ValueError('Missing or cyclic prerequisite')
            visited.add(cur)
            entry = catalog[cur]
            p, level = entry['prerequisite_id'], entry['prerequisite_level']
            if (not p and level != 0) or (p and (p not in catalog or not 1 <= level <= catalog[p]['max_level'])):
                raise ValueError('Invalid prerequisite level')
            cur = p
        if m['linked_id'] and m['linked_id'] not in catalog:
            raise ValueError('Missing linked mastery')
    if upgrade != [(1, 2, 30000, 33554961, 100)]:
        raise ValueError('Unexpected rank-up row')
    return dict(status='OFFLINE_DONOR_CATALOG_VALIDATED',
                mastery_count=len(catalog), level_count=len(expected_values),
                linked_count=sum(bool(m['linked_id']) for m in catalog.values()),
                categories=dict(sorted(collections.Counter(m['category'] for m in catalog.values()).items())),
                rank_up=dict(wexp=30000, item_id=33554961, item_count=100),
                linked_semantics_verified=False, runtime_integration_verified=False,
                mastery=list(catalog.values()))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    result = audit(a.archive)
    a.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k != 'mastery'}, indent=2))
