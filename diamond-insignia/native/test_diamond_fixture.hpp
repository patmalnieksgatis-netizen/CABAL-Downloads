#pragma once
#include <sstream>
#include <string>
// Synthetic fixture: no private donor/SCP bytes are stored in this repository.
static std::string fixture(bool drop_value=false,bool bad_upgrade=false) {
  std::ostringstream o;
  o<<"[MeritMastery_Base]\tMastery_Category\tBadge_Grade\tMastery_Type\tMastery_Index\tMax_Level\tPreMastery_Index\tPreMastery_Level\tLinkedMastery_Index\n";
  for(int i=1;i<=64;i++) o<<i-1<<"\t1\t0\t1\t"<<i<<"\t1\t0\t0\t0\n";
  for(int i=65;i<=158;i++) o<<i-1<<"\t2\t1\t1\t"<<i<<"\t1\t0\t0\t0\n";
  for(int i=159;i<=474;i++) {
    const int maxlevel=i<315?6:1;
    const int linked=i>=160&&i<=267?i-1:0;
    o<<i-1<<"\t"<<11+(i-159)%16<<"\t2\t1\t"<<i<<"\t"<<maxlevel
     <<"\t0\t0\t"<<linked<<"\n";
  }
  o<<"\n[MeritMastery_Value]\tMastery_Type\tMastery_Index\tMastery_Level\tReq_MeritPoint\tBase_ForceID\tBase_ForceValue\tBase_ValueType\tBonus_ForceID\tBonus_ForceValue\tBonus_ValueType\n";
  int row=0;
  for(int i=159;i<=474;i++) {
    for(int lvl=1;lvl<=(i<315?6:1);lvl++) {
      if(drop_value && i==159 && lvl==2)continue;
      o<<++row<<"\t1\t"<<i<<"\t"<<lvl<<"\t"<<lvl*5<<"\t180\t6\t1\t0\t0\t0\n";
    }
  }
  o<<"\n[UpGrade_Material]\tBadge_Grade\tWexp\tNeed_Item\tNeed_Count\n";
  o<<"0\t1\t20000\t33554961\t100\n";
  o<<"1\t2\t"<<(bad_upgrade?30001:30000)<<"\t33554961\t100\n";
  o<<"\n[SpecialMastery_Active]\tMastery_Index\tActive_Category\n";
  o<<"0\t83\t5\n1\t102\t6\n";
  o<<"2\t159\t11\n3\t175\t15\n4\t191\t19\n5\t207\t23\n";
  return o.str();
}
