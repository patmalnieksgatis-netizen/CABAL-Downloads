#!/usr/bin/env python3
"""Recover verified EP45 definitions from the existing private sources ZIP.

Creates a private input bundle for the existing catalog readers. Does not
install files, contact a server, change a client or update a database.
"""
import argparse
import hashlib
import importlib.util
import json
import struct
import xml.etree.ElementTree as ET
import zipfile
import zlib
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
PINS = {
    'client/ep45/meritsystem.enc':
        '74391c4317adb1dcd375de6097812f6fa57f3f52864d4f96c83c4e862de46ec1',
    'client/ep45/Language/Korean/meritsystem_msg.enc':
        '8325002522e565b7d06cf82b9e64bbe0b00a564be38f5f2474dfa018a7078e76',
    'server/active-v291/MeritSystem.scp':
        '307fc981ec3efe66f6cc1b0606ed7d86cd9e5a6e46205769a9bb34b012464295',
}
XML_PINS = (
    '297078e4cff0918280c824252c4b46e5b17e15a4c57b941b75e8d9f3081c1b9e',
    'cd627645e7c4d7aa7d5fff66d8dbcf0faa4c8c95dc776fe152778fd8d004cb50',
)
EXPECTED_ROWS = {
    'MeritMastery_Base': 316, 'MeritMastery_Value': 1096,
    'UpGrade_Material': 1, 'SlotOpen_Material': 616,
    'SlotOpen_Time': 308, 'SpecialMastery_Material': 1,
    'SpecialMastery_Value': 100, 'SpecialMastery_Active': 4,
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def decode_ep45(raw, expected_root, limit=4*1024*1024):
    if not 8 <= len(raw) <= limit:
        raise ValueError('ENC_SIZE')
    count, = struct.unpack_from('<I', raw)
    if not 1 <= count <= limit:
        raise ValueError('DECODED_SIZE')
    compressed = bytearray(raw[4:])
    for i, key in enumerate(bytes.fromhex('92656757')):
        compressed[i] ^= key
    decoder = zlib.decompressobj(-15)
    decoded = decoder.decompress(compressed, count+1)
    if (len(decoded) != count or not decoder.eof or decoder.unused_data or
            decoder.unconsumed_tail):
        raise ValueError('DEFLATE_LENGTH_OR_TRAILING_DATA')
    if b'<!DOCTYPE' in decoded.upper() or b'<!ENTITY' in decoded.upper():
        raise ValueError('XML_EXTERNAL_DECLARATION')
    if ET.fromstring(decoded).tag != expected_root:
        raise ValueError('XML_ROOT')
    return decoded


def read_sources(path):
    files = {}
    with zipfile.ZipFile(path) as archive:
        if len(archive.infolist()) > 32:
            raise ValueError('ARCHIVE_MEMBER_LIMIT')
        for member in archive.infolist():
            name = member.filename.replace('\\', '/')
            p = PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or name in files:
                raise ValueError('ARCHIVE_PATH_OR_DUPLICATE')
            if member.file_size > 4*1024*1024:
                raise ValueError('ARCHIVE_FILE_LIMIT')
            if not member.is_dir():
                files[name] = archive.read(member)
    manifest = json.loads(files['MANIFEST.json'].decode('utf-8-sig'))
    declared = {}
    for row in manifest['files']:
        name = row['archive_path']
        if name in declared:
            raise ValueError('MANIFEST_DUPLICATE')
        declared[name] = row
        if len(files[name]) != row['bytes'] or sha(files[name]) != row['sha256']:
            raise ValueError('MANIFEST_FILE_DIFFERS')
    if set(files) != set(declared) | {'MANIFEST.json'}:
        raise ValueError('UNDECLARED_ARCHIVE_FILE')
    for name, expected in PINS.items():
        if sha(files[name]) != expected:
            raise ValueError('SOURCE_PROFILE_DIFFERS:'+name)
    return files


def donor_rows(root):
    rows = {name: [] for name in EXPECTED_ROWS}
    types = {}
    for category in root.findall('./meritmastery_base/mastery_category'):
        if category.attrib['Badge_Grade'] != '2':
            continue
        cat = int(category.attrib['index'])
        for mastery in category:
            a = mastery.attrib
            mid = int(a['mastery_index'])
            if mid in types:
                raise ValueError('DUPLICATE_MASTERY')
            types[mid] = int(a['mastery_type'])
            rows['MeritMastery_Base'].append((cat, 2, types[mid], mid, *(
                int(a[k]) for k in ('max_level', 'premastery_index',
                                    'premastery_reqlevel', 'linkedmastery_index'))))
    for mastery in root.findall('./meritmastery_value/mastery'):
        mid = int(mastery.attrib['index'])
        if mid not in types:
            continue
        for value in mastery:
            rows['MeritMastery_Value'].append((types[mid], mid, *(
                int(value.attrib[k]) for k in (
                    'mastery_level', 'req_meritpoint', 'base_forceid',
                    'base_forcevalue', 'base_valuetype', 'bonus_forceid',
                    'bonus_forcevalue', 'bonus_valuetype'))))
    specs = (
        ('UpGrade_Material', './UpGrade_Material/UpGrade', 'upgrade_badge',
         lambda n: n == 2, ('upgrade_badge', 'upgrade_wexp', 'upgrade_item', 'upgrade_count')),
        ('SlotOpen_Time', './SlotOpen_Time/SlotOpenTime', 'Category_Num',
         lambda n: 11 <= n <= 26, ('Category_Num', 'Opened_Slot', 'Need_Time')),
        ('SpecialMastery_Material', './SpecialMastery_Material/Material', 'Mastery_type',
         lambda n: n == 2, ('wexp', 'Need_Item', 'Need_Count')),
        ('SpecialMastery_Value', './SpecialMastery_Value/SpecialMasteryValue', 'Category_Num',
         lambda n: 11 <= n <= 26,
         ('SpecialMastery_Index', 'Grade', 'Force_ID', 'Force_Value', 'Force_ValueType')),
        ('SpecialMastery_Active', './SpecialMastery_Active/SpecialMasteryActive', 'Active_Category',
         lambda n: 11 <= n <= 26, ('Mastery_Index', 'Active_Category')),
    )
    for name, xpath, filter_key, include, keys in specs:
        for node in root.findall(xpath):
            if include(int(node.attrib[filter_key])):
                rows[name].append(tuple(int(node.attrib[k]) for k in keys))
    for category in root.findall('./SlotOpen_Material/Category'):
        cat = int(category.attrib['Num'])
        if 11 <= cat <= 26:
            for node in category:
                rows['SlotOpen_Material'].append((cat, *(
                    int(node.attrib[k]) for k in ('Slot', 'Order', 'Need_Item', 'Need_Count'))))
    if {k: len(v) for k, v in rows.items()} != EXPECTED_ROWS:
        raise ValueError('DONOR_ROW_COUNTS')
    if set(types) != set(range(159, 475)):
        raise ValueError('DONOR_MASTERY_ID_RANGE')
    return rows


def stage_catalog(active, rows):
    # Preserve every original line. Insert only the new grade-2 rows before
    # each section's final blank separator; retain all native old headers.
    sections = []
    for line in active.decode('utf-8').splitlines(keepends=True):
        if line.startswith('['):
            sections.append([line.split(']', 1)[0][1:], []])
        if not sections:
            raise ValueError('SCP_PREAMBLE_NOT_SUPPORTED')
        sections[-1][1].append(line)
    out, delta = [], {}
    for name, lines in sections:
        added = rows.get(name, [])
        if added:
            before = [line for line in lines[1:] if line.strip() and not line.startswith(('#', ';'))]
            index = int(before[-1].split('\t', 1)[0]) + 1
            generated = ['\t'.join(map(str, (index+i, *row)))+'\n'
                         for i, row in enumerate(added)]
            insert = len(lines)
            while insert > 1 and not lines[insert-1].strip():
                insert -= 1
            lines = lines[:insert] + generated + lines[insert:]
            delta[name] = ''.join(generated).encode()
        out.extend(lines)
    if set(delta) != set(EXPECTED_ROWS):
        raise ValueError('SCP_MISSING_SECTION')
    return ''.join(out).encode(), delta


def recover(source, output):
    files = read_sources(source)
    definitions = decode_ep45(files['client/ep45/meritsystem.enc'], 'cabal_merit_system')
    messages = decode_ep45(files['client/ep45/Language/Korean/meritsystem_msg.enc'],
                           'meritsystem_message')
    if (sha(definitions), sha(messages)) != XML_PINS:
        raise ValueError('DECODED_SOURCE_PROFILE_DIFFERS')
    staged, delta = stage_catalog(files['server/active-v291/MeritSystem.scp'],
                                  donor_rows(ET.fromstring(definitions)))
    spec = importlib.util.spec_from_file_location(
        'scp_parity', HERE.parent/'catalog-audit/verify_staged_scp_parity.py')
    # The existing parity gate imports its neighboring section reader.
    import sys
    sys.path.insert(0, str(HERE.parent/'catalog-audit'))
    parity = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parity)
    report = parity.compare_scp(files['server/active-v291/MeritSystem.scp'], staged,
                                check_sha=False)
    output.mkdir(parents=True, exist_ok=False)
    members = {
        'decoded_ep45/EP45_meritsystem.xml': definitions,
        'decoded_ep45/EP45_meritsystem_msg.xml': messages,
        'MeritSystem.DIAMOND_STAGED_DO_NOT_INSTALL.scp': staged,
        **{'delta/'+name+'_NEW_ONLY.tsv': data for name, data in delta.items()},
    }
    with zipfile.ZipFile(output/'recovered-donor-inputs.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, raw in members.items():
            archive.writestr(name, raw)
    (output/'MeritSystem.DIAMOND_STAGED_DO_NOT_INSTALL.scp').write_bytes(staged)
    report.update(source_zip_sha256=sha(Path(source).read_bytes()),
                  donor_xml_sha256=sha(definitions), messages_xml_sha256=sha(messages),
                  original_staged_sha_reproduced=sha(staged) == parity.STAGED_SHA,
                  game_install_performed=False)
    (output/'recovery-report.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('sources_zip', type=Path)
    p.add_argument('private_output_directory', type=Path)
    args = p.parse_args()
    print(json.dumps(recover(args.sources_zip, args.private_output_directory), indent=2))
