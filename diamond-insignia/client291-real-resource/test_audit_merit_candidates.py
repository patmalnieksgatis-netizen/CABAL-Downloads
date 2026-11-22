import hashlib
import io
import json
import unittest
import zipfile
import zlib
from audit_merit_candidates import CLIENT_SHA, XOR4, audit, inspect_payload

def make_enc(payload):
    stream = bytearray(zlib.compress(payload, level=6, wbits=-15))
    assert len(stream) >= 4
    for i in range(4):
        stream[i] ^= XOR4[i]
    return b"HEAD" + bytes(stream) + len(payload).to_bytes(4, "little")

def fixture(raw, path="Language/English/meritsystem.enc", *, sha_override=None, extra=False):
    manifest = {
        "client_sha256": CLIENT_SHA, "count": 1, "sources_modified": False,
        "files": [{
            "path": path,
            "sha256": sha_override or hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw), "language_path": True,
        }],
    }
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w") as z:
        z.writestr(path, raw)
        z.writestr("manifest.json", json.dumps(manifest))
        if extra:
            z.writestr("unrelated.dat", b"x")
    mem.seek(0)
    return mem

class MeritCandidateTests(unittest.TestCase):
    def test_matching_codec(self):
        payload = b"Diamond-Offline-Test-" * 200
        enc = make_enc(payload)
        item = inspect_payload(enc)
        self.assertTrue(item["success"])
        self.assertEqual(item["output_sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(item["loader_trailer_uncompressed_size"], len(payload))
        self.assertEqual(item["prefix_le32_observed"], int.from_bytes(b"HEAD", "little"))
        with fixture(enc) as _:  # BytesIO accepts context management
            pass

    def test_manifest_and_codec(self):
        enc = make_enc(b"Merit resource fixture" * 100)
        result = audit(fixture(enc))
        self.assertFalse(result["runtime_opened_path_proven"])
        self.assertFalse(result["diamond_ui_or_packet_proven"])
        self.assertFalse(result["loader_binding_to_these_assets_proven"])
        self.assertTrue(result["candidates"][0]["success"])
        self.assertEqual(result["candidates"][0]["path"], "Language/English/meritsystem.enc")

    def test_bad_hash_and_extra_content_fail_closed(self):
        enc = make_enc(b"Test payload" * 100)
        with self.assertRaisesRegex(ValueError, "SHA mismatch"):
            audit(fixture(enc, sha_override="0" * 64))
        with self.assertRaisesRegex(ValueError, "unrelated/missing"):
            audit(fixture(enc, extra=True))

    def test_path_traversal_refused(self):
        enc = make_enc(b"Test payload" * 100)
        with self.assertRaisesRegex(ValueError, "unsafe candidate path"):
            audit(fixture(enc, "../meritsystem.enc"))

    def test_invalid_codec_and_bounded_output(self):
        self.assertEqual(inspect_payload(b"")["reason"], "invalid_input_size")
        forbidden = b"HEAD" + bytes(
            [0x07 ^ XOR4[0], 0 ^ XOR4[1], 0 ^ XOR4[2], 0 ^ XOR4[3]]) + b"123456" + (100).to_bytes(4, "little")
        self.assertEqual(inspect_payload(forbidden)["reason"], "reserved_deflate_btype_3")
        over = b"HEADabcdefgh" + (9 * 1024 * 1024).to_bytes(4, "little")
        self.assertEqual(inspect_payload(over)["reason"], "uncompressed_size_out_of_bounds")

if __name__ == "__main__":
    unittest.main()
