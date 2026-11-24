#!/usr/bin/env python3
"""Offline preview of learned linked mastery scopes from donor definitions.
No game integration, stat mutation, network access or deployment."""
import argparse
import json
import zipfile
import xml.etree.ElementTree as ET

def load(archive):
    with zipfile.ZipFile(archive) as z:
        root = ET.fromstring(z.read('decoded_ep45/EP45_meritsystem.xml'))
        msgs = {e.attrib['id']: e.attrib['cont'] for e in
                ET.fromstring(z.read('decoded_ep45/EP45_meritsystem_msg.xml')).iter('msg')}
    nodes = {}
    for group in root.findall('./meritmastery_base/mastery_category'):
        if group.attrib['Badge_Grade'] != '2':
            continue
        for node in group.findall('mastery_base'):
            a = node.attrib
            i = int(a['mastery_index'])
            if i in nodes:
                raise ValueError('duplicate node')
            nodes[i] = (int(group.attrib['index']), int(a['max_level']),
                        int(a['linkedmastery_index']), msgs[a['mastery_desc']])
    links = {}
    for i, (cat, cap, target, desc) in nodes.items():
        if not target:
            continue
        if target not in nodes or cap != 1 or nodes[target][2] or 'dungeons and fields' not in desc.lower():
            raise ValueError('unsupported donor link')
        links[i] = target
    if len(links) != 108 or len(set(links.values())) != 60:
        raise ValueError('unexpected catalog')
    return nodes, links

def preview(nodes, links, levels, active_categories, area):
    """Return expanded base mastery IDs, not force IDs or stat deltas.
    Only known learned base effects can be expanded; never add link values.
    Area names here are semantic labels, NOT verified WorldSvr map IDs.
    This function is a donor-data preview, not authorization to learn skills."""
    if area not in ('dungeon', 'field', 'mission_war', 'unknown'):
        raise ValueError('unknown area label')
    for i, level in levels.items():
        if i not in nodes or type(level) is not int or not 0 <= level <= nodes[i][1]:
            raise ValueError('invalid mastery level')
    if any(type(c) is not int or not 11 <= c <= 26 for c in active_categories):
        raise ValueError('invalid category')
    for root in (11,15,19,23):
        if sum(c in active_categories for c in range(root+1,root+4)) > 1:
            raise ValueError('conflicting categories')
    if area not in ('dungeon', 'field'):
        return set()
    return {target for i,target in links.items()
            if levels.get(i,0)==1 and levels.get(target,0)>0
            and nodes[i][0] in active_categories and nodes[target][0] in active_categories}

def self_test(nodes, links):
    count=0
    for i,target in links.items():
        cats={nodes[i][0],nodes[target][0]}
        for level in range(1,nodes[target][1]+1):
            both={i:1,target:level}
            for area in ('dungeon','field'):
                assert preview(nodes,links,both,cats,area)=={target}
                assert not preview(nodes,links,{i:1},cats,area)
                assert not preview(nodes,links,{target:level},cats,area)
                assert not preview(nodes,links,both,set(),area)
                count+=4
            assert not preview(nodes,links,both,cats,'mission_war')
            assert not preview(nodes,links,both,cats,'unknown')
            count+=2
    return {'status':'OFFLINE_SCOPE_PREVIEW_PASS','links':len(links),
            'targets':len(set(links.values())), 'assertions':count,
            'runtime_verified':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive')
    a=p.parse_args()
    print(json.dumps(self_test(*load(a.archive)),indent=2))
