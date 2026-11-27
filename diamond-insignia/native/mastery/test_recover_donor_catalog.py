import importlib.util
import struct
import unittest
import zlib
from pathlib import Path

spec = importlib.util.spec_from_file_location('recover', Path(__file__).with_name('recover_donor_catalog.py'))
recover = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recover)


def encoded(xml):
    c = zlib.compressobj(wbits=-15)
    payload = bytearray(c.compress(xml)+c.flush())
    for i, key in enumerate(bytes.fromhex('92656757')):
        payload[i] ^= key
    return struct.pack('<I', len(xml))+payload


class RecoveryTests(unittest.TestCase):
    def test_bounded_exact_decode(self):
        xml = b'<cabal_merit_system><test>1234567890</test></cabal_merit_system>'
        self.assertEqual(recover.decode_ep45(encoded(xml), 'cabal_merit_system'), xml)

    def test_size_trailing_and_xml_rejections(self):
        raw = encoded(b'<cabal_merit_system><value>testing</value></cabal_merit_system>')
        for bad in (raw+b'junk', struct.pack('<I', 8)+raw[4:],
                    struct.pack('<I', 0x7fffffff)+raw[4:], raw[:-2]):
            with self.assertRaises((ValueError, zlib.error)):
                recover.decode_ep45(bad, 'cabal_merit_system')
        with self.assertRaisesRegex(ValueError, 'XML_ROOT'):
            recover.decode_ep45(raw, 'other_root')

    def test_entities_rejected(self):
        raw = encoded(b'<!DOCTYPE x [<!ENTITY a "content">]><x>&a;</x>')
        with self.assertRaisesRegex(ValueError, 'XML_EXTERNAL_DECLARATION'):
            recover.decode_ep45(raw, 'x')

    def test_original_section_lines_and_new_indices_preserved(self):
        active = b'[One]\tValue\n0\t10\n\n[Two]\tValue\n0\t20\n'
        saved = recover.EXPECTED_ROWS
        try:
            recover.EXPECTED_ROWS = {'One': 2}
            staged, delta = recover.stage_catalog(active, {'One': [(30,), (40,)]})
        finally:
            recover.EXPECTED_ROWS = saved
        self.assertEqual(staged, b'[One]\tValue\n0\t10\n1\t30\n2\t40\n\n[Two]\tValue\n0\t20\n')
        self.assertEqual(delta, {'One': b'1\t30\n2\t40\n'})


if __name__ == '__main__':
    unittest.main()
