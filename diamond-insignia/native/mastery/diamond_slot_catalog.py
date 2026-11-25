#!/usr/bin/env python3
"""Read-only Diamond slot and special mastery catalog. No server access."""
import argparse
import json
import xml.etree.ElementTree as ET
import zipfile


def load_catalog(path):
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read('decoded_ep45/EP45_meritsystem.xml'))
        def rows(name):
            return [tuple(map(int, line.split('\t')))[1:] for line in
                    archive.read('delta/' + name + '_NEW_ONLY.tsv').decode().splitlines() if line.strip()]
        material_rows = rows('SlotOpen_Material')
        time_rows = rows('SlotOpen_Time')
        active_rows = rows('SpecialMastery_Active')
    materials = {}
    observed = []
    for cat in root.findall('./SlotOpen_Material/Category'):
        category = int(cat.attrib['Num'])
        if not 11 <= category <= 26:
            continue
        for node in cat:
            slot, order, item, count = (int(node.attrib[k]) for k in ('Slot','Order','Need_Item','Need_Count'))
            key = (category, slot, order)
            if key in materials or item <= 0 or count <= 0:
                raise ValueError('Invalid material row')
            materials[key] = (item, count)
            observed.append(key + (item,count))
    if observed != material_rows:
        raise ValueError('Material delta mismatch')
    times = {}
    observed = []
    for node in root.findall('./SlotOpen_Time/SlotOpenTime'):
        category, slot, seconds = (int(node.attrib[k]) for k in ('Category_Num','Opened_Slot','Need_Time'))
        if not 11 <= category <= 26:
            continue
        key = (category,slot)
        if key in times or seconds <= 0:
            raise ValueError('Invalid timer row')
        times[key] = seconds
        observed.append(key + (seconds,))
    if observed != time_rows:
        raise ValueError('Timer delta mismatch')
    slots = []
    for category in range(11,27):
        cap = 17 if category in (11,15,19,23) else 20
        for slot in range(cap):
            key = (category,slot)
            req = [materials[key+(order,)] for order in (0,1)]
            if len({item for item,count in req}) != 2:
                raise ValueError('Duplicate resource')
            slots.append(dict(category=category,slot=slot,seconds=times[key],materials=[dict(item=i,count=n) for i,n in req]))
    if len(slots) != len(times) or len(materials) != 2*len(slots):
        raise ValueError('Unexpected slot keys')
    special = [(int(n.attrib['Mastery_Index']),int(n.attrib['Active_Category'])) for n in root.findall('./SpecialMastery_Active/SpecialMasteryActive') if int(n.attrib['Active_Category']) in (11,15,19,23)]
    if special != active_rows:
        raise ValueError('Special mastery activation delta mismatch')
    costs = [dict(wexp=int(n.attrib['wexp']),item=int(n.attrib['Need_Item']),count=int(n.attrib['Need_Count'])) for n in root.findall('./SpecialMastery_Material/Material') if n.attrib['Mastery_type']=='2']
    if len(costs) != 1:
        raise ValueError('Unexpected special mastery cost')
    return dict(status='DONOR_SLOT_CATALOG_VALIDATED',slots=slots,special_activation=special,special_cost=costs[0],runtime_verified=False)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive')
    p.add_argument('output')
    args=p.parse_args()
    result=load_catalog(args.archive)
    with open(args.output,'w',encoding='utf8') as f:
        json.dump(result,f,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k!='slots'}))
    print('SLOT_ROWS=%d MATERIAL_ROWS=%d' % (len(result['slots']),sum(len(s['materials']) for s in result['slots'])))
