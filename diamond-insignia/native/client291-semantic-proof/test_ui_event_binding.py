import struct
import unittest
from verify_ui_event_binding import (
    parse_registrations, EVENT_CONSTRUCTOR, CALLBACK_BINDER,
    RVA_START, EXPECTED, MERIT_CALLBACK
)

def make_bindings():
    base=RVA_START
    raw=bytearray(b"\x90"*0x800)
    for index,(event,handler) in enumerate(sorted(EXPECTED.items())):
        pos=0x80+index*0x40
        start=base+pos
        raw[pos:pos+7]=b"\xc7\x45\x10"+struct.pack("<I",event)
        raw[pos+7:pos+14]=bytes.fromhex("488d55b0488bcb")
        raw[pos+14:pos+19]=b"\xe8"+struct.pack("<i",EVENT_CONSTRUCTOR-(start+19))
        raw[pos+19:pos+23]=bytes.fromhex("488b4db0")
        raw[pos+23:pos+30]=bytes.fromhex("488d15")+struct.pack("<i",handler-(start+30))
        raw[pos+30:pos+34]=bytes.fromhex("4883c118")
        raw[pos+34:pos+39]=b"\xe8"+struct.pack("<i",CALLBACK_BINDER-(start+39))
    return raw

class UiBindingTests(unittest.TestCase):
    def test_registration_is_1a1_not_1a2(self):
        m=parse_registrations(make_bindings(),RVA_START)
        self.assertEqual(int(m[0x1a1]["handler_rva"],16),MERIT_CALLBACK)
        self.assertEqual(int(m[0x1a2]["handler_rva"],16),0x6fcd44)
        self.assertNotEqual(m[0x1a1]["handler_rva"],m[0x1a2]["handler_rva"])
    def test_wrong_constructor_does_not_match(self):
        raw=make_bindings()
        pos=0x80+1*0x40+14
        raw[pos+1]^=1
        m=parse_registrations(raw,RVA_START)
        self.assertNotIn(0x1a1,m)
    def test_callback_binder_checked(self):
        raw=make_bindings()
        pos=0x80+2*0x40+34
        raw[pos+2]^=1
        m=parse_registrations(raw,RVA_START)
        self.assertNotIn(0x1a2,m)
    def test_duplicate_registration_refused(self):
        raw=make_bindings()
        raw[0x80+4*0x40+3:0x80+4*0x40+7]=struct.pack("<I",0x1a1)
        with self.assertRaisesRegex(ValueError,"duplicate"):
            parse_registrations(raw,RVA_START)

if __name__=="__main__":
    unittest.main()
