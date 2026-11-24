#!/usr/bin/env python3
"""Offline donor-data audit, not a runtime effect engine."""
import argparse
import collections
import hashlib
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


def audit(path):
    with zipfile.ZipFile(path) as z:
        defs = z.read('decoded_ep45/EP45_meritsystem.xml')
        descriptions = z.read('decoded_ep45/EP45_meritsystem_msg.xml')
    root = ET.fromstring(defs)
    messages = {e.attrib['id']: e.attrib['cont'] for e in ET.fromstring(descriptions).iter('msg')}
    mastery = {}
    for group in root.findall('./meritmastery_base/mastery_category'):
        if group.attrib['Badge_Grade'] != '2':
            continue
        category = int(group.attrib['index'])
        for entry in group.findall('mastery_base'):
            ident = int(entry.attrib['mastery_index'])
            if ident in mastery:
                raise ValueError(f'duplicate mastery {ident}')
            mastery[ident] = (category, entry.attrib)
    values = {}
    for entry in root.findall('./meritmastery_value/mastery'):
        ident = int(entry.attrib['index'])
        if ident in values:
            raise ValueError(f'duplicate value group {ident}')
        values[ident] = [e.attrib for e in entry.findall('value')]
    links = []
    for ident, (category, entry) in sorted(mastery.items()):
        target = int(entry['linkedmastery_index'])
        if not target:
            continue
        target_category, base = mastery[target]
        row, = values[ident]
        root_category = 11 + ((category - 11) // 4) * 4
        if not (11 <= category <= 26 and category != root_category and
                target_category in (category, root_category)):
            raise ValueError(f'Unexpected linked category {ident}')
        if (entry['mastery_type'], entry['max_level'], base['mastery_type'],
                base['linkedmastery_index'], row['mastery_level']) != ('2','1','1','0','1'):
            raise ValueError(f'Unexpected linked definition {ident}')
        if any(int(row[k]) for k in ('base_forcevalue','base_valuetype','bonus_forceid','bonus_forcevalue','bonus_valuetype')):
            raise ValueError(f'Unexpected additive modifier {ident}')
        if not values[target] or any(v['base_forceid'] != row['base_forceid'] for v in values[target]):
            raise ValueError(f'Effect mismatch {ident}')
        desc = messages[entry['mastery_desc']]
        if 'dungeons and fields' not in desc.lower():
            raise ValueError(f'Unrecognized expansion description {ident}')
        links.append(dict(id=ident, category=category, target=target,
                          target_category=target_category, cost=int(row['req_meritpoint']),
                          effect_id=int(row['base_forceid']),
                          prerequisite_id=int(entry['premastery_index']),
                          prerequisite_level=int(entry['premastery_reqlevel'])))
    costs = collections.Counter(x['cost'] for x in links)
    if (len(mastery), len(links), len({x['target'] for x in links}), costs) != (316,108,60,{15:72,30:36}):
        raise ValueError('Unexpected donor catalog totals')
    return dict(status='DONOR_LINK_METADATA_VALIDATED',
                source_xml_sha256=hashlib.sha256(defs).hexdigest(),
                source_messages_sha256=hashlib.sha256(descriptions).hexdigest(),
                mastery_count=len(mastery), linked_count=len(links),
                unique_targets=len({x['target'] for x in links}),
                same_category=sum(x['category']==x['target_category'] for x in links),
                costs=dict(sorted(costs.items())),
                donor_description_scope='dungeons_and_fields',
                runtime_effect_semantics_verified=False,
                runtime_integration_verified=False, links=links)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive',type=Path)
    p.add_argument('output',type=Path)
    a = p.parse_args()
    report = audit(a.archive)
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='links'},indent=2))
