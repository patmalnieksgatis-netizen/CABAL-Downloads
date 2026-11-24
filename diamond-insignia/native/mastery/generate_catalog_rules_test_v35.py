#!/usr/bin/env python3
"""Generate a standalone C++ rules test from the validated donor catalog JSON."""
import argparse
import json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('catalog',type=Path)
p.add_argument('output',type=Path)
a=p.parse_args()
catalog=json.loads(a.catalog.read_text(encoding='utf8'))
if catalog['status']!='OFFLINE_DONOR_CATALOG_VALIDATED':
    raise ValueError('Run donor audit first')
rows=[]
for x in catalog['mastery']:
    i=int(x['id'])
    vals=','.join(str(int(x[k])) for k in ('id','category','max_level','prerequisite_id','prerequisite_level','linked_id'))
    costs=','.join(str(int(v)) for v in x['level_cost'])
    rows.append('{'+str(i)+',{'+vals+',{'+costs+'}}}')
s='''#include "diamond_rules.hpp"
#include <cassert>
#include <iostream>
using namespace diamond;
int main(){
const std::map<int,Mastery> specs={
'''+',\n'.join(rows)+'''};
unsigned allowed=0,linked=0,levels=0;
for(const auto& pair:specs){
 const int id=pair.first; const auto& m=pair.second;
 assert(valid_mastery_definition(specs,id));
 TrustedState s{}; s.authoritative=true;s.badge_grade=2;s.revision=1;s.free_points=100000;
 s.active_categories.insert(m.category);s.server_open_slots.insert(id);
 if(m.prerequisite_id)s.levels[m.prerequisite_id]=m.prerequisite_level;
 if(m.linked_id){assert(mastery_level_up(s,specs,id,1).result==Error::LinkedSemanticsUnverified);++linked;continue;}
 for(int level=0;level<m.max_level;++level){
  const auto before=s.free_points; const auto rev=s.revision;
  const auto r=mastery_level_up(s,specs,id,rev);
  assert(r.result==Error::Ok && r.requires_atomic_commit);
  assert(r.after.free_points==before-m.level_cost[level] && r.after.levels.at(id)==level+1 && r.after.revision==rev+1);
  s=r.after;++levels;
 }
 assert(mastery_level_up(s,specs,id,s.revision).result==Error::MaxLevel);++allowed;
}
std::cout<<"DONOR_CATALOG_RULES=PASS definitions="<<specs.size()<<" unlinked="<<allowed<<" level_transitions="<<levels<<" linked_rejected="<<linked<<"\\n";
}
'''
a.output.write_text(s,encoding='utf8')
