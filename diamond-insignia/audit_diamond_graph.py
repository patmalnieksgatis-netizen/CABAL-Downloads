#!/usr/bin/env python3
"""Read-only dependency/point graph verification for donor EP45 meritsystem XML.
NOT a WorldSvr hook, decoder, installer, SQL script or Diamond points grant.
Pass the decoded XML from the user's verified private source ZIP.
"""
import argparse,collections,hashlib,json,pathlib,xml.etree.ElementTree as ET
SHA='297078e4cff0918280c824252c4b46e5b17e15a4c57b941b75e8d9f3081c1b9e'
def audit(root):
 assert root.tag=='cabal_merit_system'
 nodes={};percat=collections.Counter();grades={}
 for c in root.find('meritmastery_base'):
  cat,grade=int(c.get('index')),int(c.get('Badge_Grade'))
  assert cat not in grades
  grades[cat]=grade
  for m in c:
   idx=int(m.get('mastery_index'));assert idx not in nodes
   nodes[idx]=dict(cat=cat,grade=grade,
       maxlvl=int(m.get('max_level')),pre=int(m.get('premastery_index')),
       prelevel=int(m.get('premastery_reqlevel')),
       linked=int(m.get('linkedmastery_index')))
   percat[cat]+=1
 assert sorted(nodes)==list(range(1,475))
 assert collections.Counter(n['grade'] for n in nodes.values())=={0:64,1:94,2:316}
 assert {k for k,g in grades.items() if g==2}==set(range(11,27))
 assert {i for i,n in nodes.items() if n['grade']==2}==set(range(159,475))
 groups={}
 for x in root.find('Category_Group'):
  assert int(x.get('Merit_type'))==2
  main=int(x.get('Category'));sub=tuple(int(y) for y in x.get('SubCategory').split(','))
  assert main not in groups and len(sub)==3
  groups[main]=sub
 assert set(groups)=={11,15,19,23}
 assert {v for k,subs in groups.items() for v in (k,*subs)}==set(range(11,27))
 active={(int(x.get('Mastery_Index')),int(x.get('Active_Category')))
         for x in root.find('SpecialCategory_Active')}
 assert len(active)==12
 for mid,cat in active:
  assert mid in nodes and any(nodes[mid]['cat']==main and cat in subs
                              for main,subs in groups.items())
 crossings=[];linked=[]
 for idx,n in nodes.items():
  p=n['pre']
  if p:
   assert p in nodes and nodes[p]['grade']==n['grade']
   assert n['prelevel']<=nodes[p]['maxlvl']
   if nodes[p]['cat']!=n['cat']:
    assert n['grade']==2 and nodes[p]['cat'] in groups
    assert n['cat'] in groups[nodes[p]['cat']] and (p,n['cat']) in active
    crossings.append((idx,p,nodes[p]['cat'],n['cat']))
  else:assert n['prelevel']==0
  if n['linked']:
   assert n['linked'] in nodes and nodes[n['linked']]['grade']==n['grade']
   if n['grade']==2:linked.append((idx,n['linked']))
  seen=set();walk=idx
  while walk:
   assert walk not in seen,('pre_cycle',idx)
   seen.add(walk);walk=nodes[walk]['pre']
 assert len(crossings)==12 and len(linked)==108
 values={}
 for item in root.find('meritmastery_value'):
  mid=int(item.get('index'));assert mid in nodes and mid not in values
  vv=list(item);assert len(vv)==nodes[mid]['maxlvl']
  assert [int(x.get('mastery_level')) for x in vv]==list(range(1,len(vv)+1))
  assert all(int(x.get('req_meritpoint'))>=0 for x in vv)
  values[mid]=vv
 assert len(values)==474
 mids=[i for i,n in nodes.items() if n['grade']==2]
 assert sum(len(values[i]) for i in mids)==1096
 rank=[x.attrib for x in root.find('UpGrade_Material') if x.get('upgrade_badge')=='2']
 assert len(rank)==1 and (rank[0]['upgrade_wexp'],rank[0]['upgrade_item'],rank[0]['upgrade_count'])==('30000','33554961','100')
 bands=list(root.find('dia_meritscore_fomula'));assert len(bands)==301
 assert all(int(x.get('max'))==int(y.get('min')) for x,y in zip(bands,bands[1:]))
 return {'status':'OFFLINE_DEPENDENCY_VALIDATED_ONLY',
  'masteries':{'gold':64,'platinum':94,'diamond':316},
  'diamond_mastery_index_range':[min(mids),max(mids)],
  'diamond_level_values':1096,
  'diamond_total_level_point_cost_if_all_purchased':
     sum(int(x.get('req_meritpoint')) for i in mids for x in values[i]),
  'diamond_categories':{str(k):percat[k] for k in range(11,27)},
  'groups':{str(k):list(v) for k,v in groups.items()},
  'category_activation_edges':len(active),
  'cross_category_prerequisites':crossings,
  'linked_mastery_edges':len(linked),
  'linked_mastery_semantics':'UNKNOWN',
  'rank_up_material':rank[0],
  'diamond_score_bands':len(bands),
  'client_packet_sql_and_worldsvr':'NOT_IMPLEMENTED'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('decoded_ep45_meritsystem_xml',type=pathlib.Path);p.add_argument('--output',type=pathlib.Path)
 a=p.parse_args();b=a.decoded_ep45_meritsystem_xml.read_bytes()
 assert hashlib.sha256(b).hexdigest()==SHA,'Donor XML checksum mismatch'
 report=audit(ET.fromstring(b));report['source_sha256']=SHA
 s=json.dumps(report,indent=2,ensure_ascii=False)+'\n'
 if a.output:a.output.write_text(s,encoding='utf-8')
 print(s)
