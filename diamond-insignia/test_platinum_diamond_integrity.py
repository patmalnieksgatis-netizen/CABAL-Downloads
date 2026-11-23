#!/usr/bin/env python3
"""Offline-only integrity check: old Gold/Platinum intact; Diamond add-only."""
import argparse,collections,hashlib,json,zipfile

EXPECTED_ORIGINAL="307fc981ec3efe66f6cc1b0606ed7d86cd9e5a6e46205769a9bb34b012464295"
EXPECTED_STAGE="26c9c4cbe3136f67f0298c8e412a4aa7620ba46d62b5c3950880fe821f2ee2e5"
DELTA={"MeritMastery_Base":316,"MeritMastery_Value":1096,
       "SlotOpen_Material":616,"SlotOpen_Time":308,
       "SpecialMastery_Active":4,"SpecialMastery_Material":1,
       "SpecialMastery_Value":100,"UpGrade_Material":1}

def parse(data):
    out={}; section=None
    for line in data.decode("utf-8").splitlines():
        if line.startswith("["):
            section=line.split("]",1)[0][1:]
            assert section not in out
            out[section]={"header":line,"rows":[]}
        elif section and line.strip() and not line.startswith(("#",";")):
            out[section]["rows"].append(line)
    return out

def sha(data):return hashlib.sha256(data).hexdigest()
def run(sources,staged):
    with zipfile.ZipFile(sources) as f:
        source_name=next(n for n in f.namelist() if n.replace("\\","/")=="server/active-v291/MeritSystem.scp")
        original=f.read(source_name)
    with zipfile.ZipFile(staged) as f:
        candidate=f.read("MeritSystem.DIAMOND_STAGED_DO_NOT_INSTALL.scp")
    assert sha(original)==EXPECTED_ORIGINAL
    assert sha(candidate)==EXPECTED_STAGE
    old,new=parse(original),parse(candidate)
    assert list(old)==list(new)
    for name in old:
        base=old[name]["rows"]
        rows=new[name]["rows"]
        assert old[name]["header"]==new[name]["header"],name
        assert rows[:len(base)]==base,name+" EXISTING_ROWS_CHANGED"
        assert len(rows)-len(base)==DELTA.get(name,0),name+" UNEXPECTED_DELTA"
        if len(rows)>len(base):
            keys=[int(row.split("\t")[0]) for row in rows[len(base):]]
            prev=int(base[-1].split("\t")[0])
            assert keys==list(range(prev+1,prev+1+len(keys))),name+" INDEX_GAP"
    original_master=old["MeritMastery_Base"]["rows"]
    staged_master=new["MeritMastery_Base"]["rows"]
    assert collections.Counter(int(s.split("\t")[2]) for s in original_master)=={0:64,1:94}
    assert collections.Counter(int(s.split("\t")[2]) for s in staged_master)=={0:64,1:94,2:316}
    diamond=staged_master[len(original_master):]
    assert {int(s.split("\t")[1]) for s in diamond}==set(range(11,27))
    all_ids={int(s.split("\t")[4]) for s in staged_master}
    assert all_ids==set(range(1,475))
    for row in new["MeritMastery_Value"]["rows"][len(old["MeritMastery_Value"]["rows"]):]:
        assert int(row.split("\t")[2]) in all_ids
    upgrades=new["UpGrade_Material"]["rows"]
    assert upgrades[0]==old["UpGrade_Material"]["rows"][0]
    grade2=[s.split("\t") for s in upgrades if s.split("\t")[1]=="2"]
    assert len(grade2)==1 and grade2[0][2:]==["30000","33554961","100"]
    print(json.dumps({"status":"PASS_OFFLINE_ONLY","gold_original_rows":64,
          "platinum_original_rows":94,"diamond_added_rows":316,
          "diamond_mastery_categories":16,"total_new_rows":sum(DELTA.values()),
          "existing_merit_rows_unchanged":True,
          "gameplay_sql_packet_compatibility":"NOT_VERIFIED",
          "next_system":"Anima Mastery — after Platinum and Diamond working"},indent=2))

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("source_zip")
    parser.add_argument("staged_zip")
    a=parser.parse_args()
    run(a.source_zip,a.staged_zip)
