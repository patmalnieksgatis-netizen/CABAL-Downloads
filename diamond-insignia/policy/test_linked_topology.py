#!/usr/bin/env python3
"""Synthetic topology mutation tests. No donor XML or game binaries committed."""
import hashlib
import importlib.util
import pathlib
import unittest
import xml.etree.ElementTree as ET

SRC=pathlib.Path(__file__).with_name("linked_mastery_topology.py")
SPEC=importlib.util.spec_from_file_location("diamond_linked_audit",SRC)
m=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)

def source_xml():
    root=ET.Element("cabal_merit_system")
    parent=ET.SubElement(root,"meritmastery_base")
    index=1000
    for main,subs in m.GROUPS.items():
        category=ET.SubElement(parent,"mastery_category",index=str(main),Badge_Grade="2")
        mainids=[]
        for _ in range(6):
            mainids.append(index)
            ET.SubElement(category,"mastery_base",mastery_index=str(index),
                          linkedmastery_index="0",max_level="1")
            index+=1
        for sub in subs:
            subcat=ET.SubElement(parent,"mastery_category",index=str(sub),Badge_Grade="2")
            local=[]
            for _ in range(3):
                local.append(index)
                ET.SubElement(subcat,"mastery_base",mastery_index=str(index),
                              linkedmastery_index="0",max_level="1")
                index+=1
            for target in mainids+local:
                ET.SubElement(subcat,"mastery_base",mastery_index=str(index),
                              linkedmastery_index=str(target),max_level="1")
                index+=1
    return root

def try_audit(root):
    data=ET.tostring(root)
    m.DONOR_SHA256=hashlib.sha256(data).hexdigest()
    return m.inspect(data)

def first_link(root):
    return next(n for n in root.iter("mastery_base") if n.attrib["linkedmastery_index"]!="0")

class LinkedTopologyTests(unittest.TestCase):
    def test_exact_108_and_distribution(self):
        r=try_audit(source_xml())
        self.assertEqual(r["diamond_linked_edges"],108)
        self.assertEqual(len(r["subcategories"]),12)
        self.assertTrue(all((n["linked"],n["links_to_main"],n["links_to_self"])==(9,6,3)
                            for n in r["subcategories"].values()))
        self.assertEqual(r["server_rule_mode"],"FAIL_CLOSED_LINKED_BONUSES")
    def test_missing_link_rejected(self):
        root=source_xml()
        first_link(root).set("linkedmastery_index","0")
        with self.assertRaises(ValueError):try_audit(root)
    def test_bogus_link_rejected(self):
        root=source_xml()
        first_link(root).set("linkedmastery_index","900000")
        with self.assertRaises(ValueError):try_audit(root)
    def test_forward_link_rejected(self):
        root=source_xml()
        n=first_link(root)
        n.set("linkedmastery_index",n.get("mastery_index"))
        with self.assertRaises(ValueError):try_audit(root)
    def test_wrong_subcategory_rejected(self):
        root=source_xml()
        first_link(root).set("linkedmastery_index","1006")
        with self.assertRaises(ValueError):try_audit(root)
    def test_sha_gate_rejects_modified_xml(self):
        root=source_xml()
        src=ET.tostring(root)
        m.DONOR_SHA256=hashlib.sha256(src).hexdigest()
        with self.assertRaisesRegex(ValueError,"CHECKSUM_MISMATCH"):
            m.inspect(src+b" ")
    def test_duplicate_mastery_rejected(self):
        root=source_xml()
        nodes=list(root.iter("mastery_base"))
        nodes[1].set("mastery_index",nodes[0].get("mastery_index"))
        with self.assertRaises(ValueError):try_audit(root)

if __name__=="__main__":
    unittest.main(verbosity=2)
