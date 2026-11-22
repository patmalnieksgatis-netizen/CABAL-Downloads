import shutil
import unittest
from analyze_v9_call_graph import CLIENT, MERIT, inspect, validate

def fixture():
    ts=[]
    for name,rva in [("buffer_processing_step",0x2b8004),
                     ("buffer_copy_like_callee",0xa37890),
                     ("linked_buffer_free_callee",0xa6be2c)]:
        ts.append({"name":name,"requested_rva":hex(rva),
                   "classification":"PDATA_BOUNDED_FUNCTION",
                   "pdata_range_proven":True,"function_begin_rva":hex(rva),
                   "function_end_rva":hex(rva+1),"total_bytes":1,
                   "code_complete":True,"leading_bytes_hex":"c3"})
    return {"schema":9,"mode":"READ_ONLY_X64_MERIT_PROCESSING_STEP_CALLEES",
            "exe_sha256":CLIENT,"merit_enc_sha256":MERIT,"targets":ts,
            "game_launched":False,"process_memory_read":False,
            "sql_or_vm_access":False,"client_modified":False,
            "actual_merit_decoder_proven":False,"diamond_opcode_proven":False}

class TestV9(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(len(validate(fixture())),3)
        if shutil.which("objdump"):
            result,listing=inspect(fixture(),shutil.which("objdump"))
            self.assertEqual(len(result["functions"]),3)
            self.assertIn("ret",listing["buffer_processing_step"])
            self.assertFalse(result["diamond_decoder_proven"])
    def test_direct_call(self):
        if not shutil.which("objdump"): return
        r=fixture();t=r["targets"][0]
        t["function_end_rva"]="0x2b800a"
        t["total_bytes"]=6
        t["leading_bytes_hex"]="e800000000c3"
        result,_=inspect(r,shutil.which("objdump"))
        self.assertEqual(result["functions"][0]["direct_calls"][0]["target_rva"],"0x2b8009")
    def test_sha_rejected(self):
        r=fixture();r["exe_sha256"]="0"*64
        with self.assertRaises(ValueError): validate(r)
    def test_wrong_rva_rejected(self):
        r=fixture();r["targets"][0]["requested_rva"]="0x400"
        with self.assertRaises(ValueError): validate(r)
    def test_false_complete_rejected(self):
        r=fixture();r["targets"][0]["total_bytes"]=200
        with self.assertRaises(ValueError): validate(r)
    def test_mutation_rejected(self):
        r=fixture();r["client_modified"]=True
        with self.assertRaises(ValueError): validate(r)

if __name__=="__main__":unittest.main()
