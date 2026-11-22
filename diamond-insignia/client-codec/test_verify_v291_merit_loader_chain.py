import unittest
import struct
from verify_v291_merit_loader_chain import verify

def fn(name,begin,length):
    return {"name":name,"classification":"PDATA_BOUNDED_FUNCTION",
            "pdata_range_proven":True,"function_begin_rva":hex(begin),
            "function_end_rva":hex(begin+length),"total_bytes":length,
            "leading_bytes_hex":("90"*length)}

def fixture():
    a=fn("selector_wrapper",0x21cbd4,0x1d0)
    b=fn("indexed_path_wrapper_caller",0x21cda4,0x92)
    c=fn("enc_file_loader",0x2178e0,0x17c)
    def poke(item,addr,data):
        start=int(item["function_begin_rva"],16)
        body=bytearray.fromhex(item["leading_bytes_hex"])
        i=addr-start
        body[i:i+len(data)]=data
        item["leading_bytes_hex"]=body.hex()
    def call(item,at,dst):
        poke(item,at,b"\xe8"+struct.pack("<i",dst-at-5))
    call(a,0x21cc2a,0x21d938)
    poke(a,0x21cc34,bytes.fromhex("84c0"))
    poke(a,0x21cc90,bytes.fromhex("ff15625d9100"))
    call(a,0x21cca6,0x217244)
    call(a,0x21ccfa,0x216fac)
    call(b,0x21cdc6,0x21cbd4)
    call(b,0x21cde6,0x2178e0)
    for at,raw in ((0x21cdce,"4883781810"),(0x21cdd8,"488bd3"),
                   (0x21cddb,"48c1e204"),(0x21cde2,"4c8d4208")):
        poke(b,at,bytes.fromhex(raw))
    for at,raw in ((0x21793f,"ff1593ac9100"),(0x21794b,"83e804"),
                   (0x217975,"ff15f5ab9100"),(0x217987,"ff154bac9100"),
                   (0x2179c7,"488d4804"),(0x2179d0,"48634d00")):
        poke(c,at,bytes.fromhex(raw))
    call(c,0x217a17,0x2b7fac)
    return {"functions":[a]},{"targets":[b]},{"targets":[c]}

class VerifyMeritLoader(unittest.TestCase):
    def test_known_source_anchors(self):
        result=verify(*fixture())
        self.assertEqual(result["status"],"STATIC_CALL_CHAIN_PASS")
        self.assertFalse(result["actual_runtime_file_path_proven"])
        self.assertFalse(result["game_or_server_modified"])

    def test_wrong_loader_call_refused(self):
        a,b,c=fixture()
        t=c["targets"][0]
        raw=bytearray.fromhex(t["leading_bytes_hex"])
        raw[0x217a18-0x2178e0]^=1
        t["leading_bytes_hex"]=raw.hex()
        with self.assertRaisesRegex(ValueError,"wrong CALL target"):
            verify(a,b,c)

    def test_altered_path_branch_refused(self):
        a,b,c=fixture()
        t=a["functions"][0]
        raw=bytearray.fromhex(t["leading_bytes_hex"])
        raw[0x21cc90-0x21cbd4]=0x90
        t["leading_bytes_hex"]=raw.hex()
        with self.assertRaisesRegex(ValueError,"instruction mismatch"):
            verify(a,b,c)

if __name__=="__main__":unittest.main()
