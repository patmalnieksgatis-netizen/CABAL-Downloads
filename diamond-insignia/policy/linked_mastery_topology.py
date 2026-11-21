#!/usr/bin/env python3
"""Check source-verified EP45 Diamond LinkedMastery topology without trusting or implementing effects."""
import hashlib
import json
import pathlib
import xml.etree.ElementTree as ET

DONOR_SHA256="297078e4cff0918280c824252c4b46e5b17e15a4c57b941b75e8d9f3081c1b9e"
GROUPS={11:(12,13,14),15:(16,17,18),19:(20,21,22),23:(24,25,26)}

def inspect(xml_bytes):
    if hashlib.sha256(xml_bytes).hexdigest()!=DONOR_SHA256:
        raise ValueError("EP45_DONOR_XML_CHECKSUM_MISMATCH")
    root=ET.fromstring(xml_bytes)
    mastery={}
    for cat in root.find("meritmastery_base"):
        grade,catid=int(cat.attrib["Badge_Grade"]),int(cat.attrib["index"])
        for node in cat:
            i=int(node.attrib["mastery_index"])
            if i in mastery:
                raise ValueError("DUPLICATE_MASTERY_INDEX")
            mastery[i]={"grade":grade,"category":catid,
                        "max_level":int(node.attrib["max_level"]),
                        "linked":int(node.attrib["linkedmastery_index"])}
    result={}
    total_links=0
    for main,subs in GROUPS.items():
        for sub in subs:
            members=[(idx,entry) for idx,entry in mastery.items()
                     if entry["grade"]==2 and entry["category"]==sub]
            links=[(idx,entry["linked"]) for idx,entry in members if entry["linked"]]
            parent_count=0
            intra_count=0
            for idx,target_id in links:
                target=mastery.get(target_id)
                if not target or target["grade"]!=2:
                    raise ValueError("BROKEN_LINKED_MASTERY_REFERENCE")
                if target_id>=idx:
                    raise ValueError("UNEXPECTED_FORWARD_LINK")
                if target["category"]==main:parent_count+=1
                elif target["category"]==sub:intra_count+=1
                else:raise ValueError("UNEXPECTED_CROSS_CATEGORY_LINK")
            if (len(links),parent_count,intra_count)!=(9,6,3):
                raise ValueError("UNEXPECTED_DIAMOND_LINK_TOPOLOGY")
            total_links+=len(links)
            result[str(sub)]={"main_category":main,"linked":len(links),
                              "links_to_main":parent_count,"links_to_self":intra_count}
    if total_links!=108:
        raise ValueError("TOTAL_DIAMOND_LINK_COUNT_MISMATCH")
    return {"status":"DIAMOND_DONOR_LINK_GRAPH_VERIFIED",
            "source_sha256":DONOR_SHA256,
            "diamond_linked_edges":total_links,"diamond_subcategories":12,
            "subcategories":result,"runtime_effects":"NOT_INFERRED",
            "server_rule_mode":"FAIL_CLOSED_LINKED_BONUSES"}

if __name__=="__main__":
    import argparse
    a=argparse.ArgumentParser()
    a.add_argument("ep45_decoded_merit_xml",type=pathlib.Path)
    a.add_argument("--output",type=pathlib.Path)
    opts=a.parse_args()
    result=inspect(opts.ep45_decoded_merit_xml.read_bytes())
    output=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if opts.output:opts.output.write_text(output,encoding="utf-8")
    print(output)
