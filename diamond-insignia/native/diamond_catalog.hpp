// Parse the VERIFIED v291 MeritSystem.scp data contract into Diamond C++ specs.
// This parser does not ship or modify the private EP45 donor file.
#pragma once
#include "diamond_rules.hpp"
#include <algorithm>
#include <array>
#include <cstdint>
#include <istream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
namespace diamond {
struct ForceDefinition {
  int id=0;
  int value=0;
  int value_type=0;
};
struct MasteryLevelDefinition {
  int point_cost=0;
  ForceDefinition base{};
  ForceDefinition bonus{};
  int mastery_type=0;
};
struct SlotMaterial {
  int item=0;
  int count=0;
};
struct SlotOpeningDefinition {
  std::array<SlotMaterial,2> materials{};
  int seconds=0;
};
struct NativeCatalog {
  std::map<int,Mastery> diamond;
  std::map<int,int> mastery_types;
  // Preserve donor force definitions for the native effect provider. Parsing
  // these values does not authorize applying them or interpreting value_type
  // as a WorldSvr ABI. Linked rows must never become additive stat modifiers.
  std::map<std::pair<int,int>,MasteryLevelDefinition> levels;
  std::map<std::pair<int,int>,SlotOpeningDefinition> slot_openings;
  std::map<std::pair<int,int>,ForceDefinition> special_effects;
  int special_wexp=0;
  SlotMaterial special_material{};
  std::map<int,int> activation_edges;
  std::size_t imported_value_rows=0;
};
inline int strict_decimal(const std::string& s) {
  if (s.empty()) throw std::invalid_argument("SCP_EMPTY_INTEGER");
  std::size_t consumed=0;
  int n=0;
  try { n=std::stoi(s,&consumed,10); }
  catch(const std::exception&) { throw std::invalid_argument("SCP_INVALID_INTEGER"); }
  if (consumed!=s.size() || s[0]=='+')
    throw std::invalid_argument("SCP_INVALID_INTEGER");
  return n;
}
inline std::vector<std::string> split_tabs(const std::string& s) {
  std::vector<std::string> parts;
  std::size_t start=0;
  while (true) {
    const auto tab=s.find('\t',start);
    if (tab==std::string::npos) { parts.push_back(s.substr(start)); break; }
    parts.push_back(s.substr(start,tab-start));
    start=tab+1;
  }
  return parts;
}
inline NativeCatalog read_native_catalog(std::istream& stream) {
  NativeCatalog out;
  std::string section,line;
  std::size_t grade0=0,grade1=0,grade2=0,validUpgrades=0,linked=0;
  std::set<std::pair<int,int>> cost_keys;
  std::set<std::array<int,3>> slot_material_keys;
  std::set<std::pair<int,int>> slot_timer_keys;
  bool special_material_seen=false;
  std::set<std::string> section_names;
  std::size_t total_lines=0;
  while (std::getline(stream,line)) {
    if (++total_lines>300000) throw std::invalid_argument("SCP_LINE_LIMIT");
    if (!line.empty() && line.back()=='\r') line.pop_back();
    if (line.empty() || line[0]=='#' || line[0]==';') continue;
    if (line[0]=='[') {
      const auto end=line.find(']');
      if (end==std::string::npos)throw std::invalid_argument("SCP_SECTION_UNTERMINATED");
      section=line.substr(1,end-1);
      if (!section_names.insert(section).second)
        throw std::invalid_argument("SCP_DUPLICATE_SECTION");
      continue;
    }
    const auto f=split_tabs(line);
    if (section=="MeritMastery_Base") {
      if (f.size()!=9)throw std::invalid_argument("MASTERY_BASE_COLUMNS");
      const int grade=strict_decimal(f[2]);
      if (grade==0){++grade0;continue;}
      if (grade==1){++grade1;continue;}
      if (grade!=2)throw std::invalid_argument("UNKNOWN_GRADE");
      Mastery m;
      m.category=strict_decimal(f[1]);
      m.id=strict_decimal(f[4]);
      m.max_level=strict_decimal(f[5]);
      m.prerequisite_id=strict_decimal(f[6]);
      m.prerequisite_level=strict_decimal(f[7]);
      m.linked_id=strict_decimal(f[8]);
      const int mastery_type=strict_decimal(f[3]);
      if (m.id<159 || m.id>474 || category_root(m.category)<0 ||
          m.max_level<1 || m.max_level>100 ||
          m.prerequisite_id<0 || m.prerequisite_id>474 ||
          m.prerequisite_level<0 || m.linked_id<0 || m.linked_id>474 ||
          m.linked_id==m.id || (mastery_type!=1 && mastery_type!=2))
        throw std::invalid_argument("INVALID_DIAMOND_MASTERY");
      if (!out.diamond.emplace(m.id,std::move(m)).second)
        throw std::invalid_argument("DUPLICATE_DIAMOND_MASTERY");
      out.mastery_types.emplace(strict_decimal(f[4]),mastery_type);
      ++grade2;
    } else if (section=="MeritMastery_Value") {
      if (f.size()!=11) throw std::invalid_argument("MASTERY_VALUE_COLUMNS");
      const int idx=strict_decimal(f[2]);
      if (idx<159) continue;
      if (idx>474)throw std::invalid_argument("UNEXPECTED_MASTERY_VALUE_ID");
      const int level=strict_decimal(f[3]);
      const int cost=strict_decimal(f[4]);
      if (level<1 || level>100 || cost<0)throw std::invalid_argument("INVALID_DIAMOND_COST");
      if (!cost_keys.emplace(idx,level).second)
        throw std::invalid_argument("DUPLICATE_MASTERY_COST");
      MasteryLevelDefinition definition{};
      definition.point_cost=cost;
      definition.mastery_type=strict_decimal(f[1]);
      definition.base={strict_decimal(f[5]),strict_decimal(f[6]),strict_decimal(f[7])};
      definition.bonus={strict_decimal(f[8]),strict_decimal(f[9]),strict_decimal(f[10])};
      if(definition.base.id<0 || definition.bonus.id<0 ||
         definition.base.value_type<0 || definition.base.value_type>2 ||
         definition.bonus.value_type<0 || definition.bonus.value_type>2)
        throw std::invalid_argument("INVALID_DIAMOND_FORCE_DEFINITION");
      out.levels.emplace(std::make_pair(idx,level),definition);
      ++out.imported_value_rows;
    } else if (section=="UpGrade_Material") {
      if (f.size()!=5)throw std::invalid_argument("UPGRADE_COLUMNS");
      if (strict_decimal(f[1])==2) {
        if (strict_decimal(f[2])!=30000 ||
            strict_decimal(f[3])!=static_cast<int>(kRequiredDonorItemId) ||
            strict_decimal(f[4])!=100)
          throw std::invalid_argument("DIAMOND_UPGRADE_COST_MISMATCH");
        ++validUpgrades;
      }
    } else if (section=="SpecialMastery_Active") {
      if (f.size()!=3)throw std::invalid_argument("CATEGORY_ACTIVE_COLUMNS");
      const int id=strict_decimal(f[1]);
      const int category=strict_decimal(f[2]);
      if (category>=11 && category<=26) {
        if (!out.activation_edges.emplace(id,category).second)
          throw std::invalid_argument("DUPLICATE_DIAMOND_ACTIVATION");
      }
    } else if (section=="SlotOpen_Material" || section=="SlotOpen_Time") {
      const bool material=section=="SlotOpen_Material";
      if(f.size()!=(material?6u:4u))throw std::invalid_argument("SLOT_OPEN_COLUMNS");
      const int category=strict_decimal(f[1]);
      if(category<11)continue; // native Gold/Platinum rows retained separately
      if(category>26)throw std::invalid_argument("SLOT_OPEN_CATEGORY");
      const int slot=strict_decimal(f[2]);
      const int cap=(category==category_root(category))?17:20;
      if(slot<0 || slot>=cap)throw std::invalid_argument("SLOT_OPEN_RANGE");
      auto& entry=out.slot_openings[{category,slot}];
      if(material) {
        const int order=strict_decimal(f[3]);
        const int item=strict_decimal(f[4]),count=strict_decimal(f[5]);
        if(order<0 || order>1 || item<=0 || count<=0 ||
           !slot_material_keys.insert({category,slot,order}).second)
          throw std::invalid_argument("SLOT_OPEN_MATERIAL");
        entry.materials[static_cast<std::size_t>(order)]={item,count};
      } else {
        const int seconds=strict_decimal(f[3]);
        if(seconds<=0 || !slot_timer_keys.emplace(category,slot).second)
          throw std::invalid_argument("SLOT_OPEN_TIMER");
        entry.seconds=seconds;
      }
    } else if(section=="SpecialMastery_Material") {
      if(f.size()!=4)throw std::invalid_argument("SPECIAL_MATERIAL_COLUMNS");
      const int row=strict_decimal(f[0]);
      if(row==0)continue; // existing native Platinum cost
      if(row!=1 || special_material_seen)
        throw std::invalid_argument("SPECIAL_MATERIAL_ROW");
      special_material_seen=true;
      out.special_wexp=strict_decimal(f[1]);
      out.special_material={strict_decimal(f[2]),strict_decimal(f[3])};
      if(out.special_wexp!=1500 || out.special_material.item!=33554961 ||
         out.special_material.count!=3)
        throw std::invalid_argument("SPECIAL_MATERIAL_COST");
    } else if(section=="SpecialMastery_Value") {
      if(f.size()!=6)throw std::invalid_argument("SPECIAL_EFFECT_COLUMNS");
      const int id=strict_decimal(f[1]),grade=strict_decimal(f[2]);
      if(id<34)continue; // legacy Platinum special effect definitions
      if(id>53 || grade<1 || grade>5)
        throw std::invalid_argument("SPECIAL_EFFECT_ID_OR_GRADE");
      const ForceDefinition effect{strict_decimal(f[3]),strict_decimal(f[4]),strict_decimal(f[5])};
      if(effect.id<=0 || effect.value_type<0 || effect.value_type>2 ||
         !out.special_effects.emplace(std::make_pair(id,grade),effect).second)
        throw std::invalid_argument("SPECIAL_EFFECT_DEFINITION");
    }
  }
  if (!stream.eof() && stream.fail())throw std::invalid_argument("SCP_STREAM_READ_FAILED");
  if (grade0!=64 || grade1!=94 || grade2!=316 || out.diamond.size()!=316 ||
      validUpgrades!=1 || out.imported_value_rows!=1096 ||
      out.activation_edges.size()!=4)
    throw std::invalid_argument("SCP_DIAMOND_ROW_COUNTS_DIFFER");
  for (int id=159;id<=474;++id) {
    auto it=out.diamond.find(id);
    if (it==out.diamond.end())throw std::invalid_argument("SCP_DIAMOND_ID_GAP");
    auto& m=it->second;
    m.level_cost.resize(static_cast<std::size_t>(m.max_level));
    for (int level=1;level<=m.max_level;++level) {
      const auto v=out.levels.find(std::make_pair(id,level));
      if (v==out.levels.end())throw std::invalid_argument("SCP_MASTERY_LEVEL_COST_MISSING");
      if(v->second.mastery_type!=out.mastery_types.at(id))
        throw std::invalid_argument("SCP_MASTERY_VALUE_TYPE_DIFFERS");
      m.level_cost[static_cast<std::size_t>(level-1)]=v->second.point_cost;
    }
    if (m.linked_id) {
      auto linked_target=out.diamond.find(m.linked_id);
      if (linked_target==out.diamond.end())
        throw std::invalid_argument("SCP_LINKED_MASTERY_INVALID");
      ++linked;
    }
  }
  if (linked!=108)throw std::invalid_argument("SCP_LINKED_EDGE_COUNT_MISMATCH");
  for (const auto& edge:out.activation_edges) {
    auto mastery=out.diamond.find(edge.first);
    if (mastery==out.diamond.end() || category_root(edge.second)<0)
      throw std::invalid_argument("SCP_ACTIVATION_EDGE_INVALID");
  }
  // Old minimal rule fixtures may omit slot/special sections entirely.
  // Once an extension section is provided, require its complete catalog;
  // never silently interpret a partial real file as a usable definition.
  if(!out.slot_openings.empty()) {
    if(out.slot_openings.size()!=308 || slot_material_keys.size()!=616 ||
       slot_timer_keys.size()!=308)
      throw std::invalid_argument("SLOT_OPEN_INCOMPLETE");
    for(const auto& pair:out.slot_openings) {
      const auto& entry=pair.second;
      if(entry.seconds<=0 || entry.materials[0].item<=0 || entry.materials[1].item<=0 ||
         entry.materials[0].item==entry.materials[1].item)
        throw std::invalid_argument("SLOT_OPEN_RESOURCES_DIFFERS");
    }
  }
  if(!out.special_effects.empty() && out.special_effects.size()!=100)
    throw std::invalid_argument("SPECIAL_EFFECTS_INCOMPLETE");
  return out;
}
inline bool has_complete_slot_catalog(const NativeCatalog& catalog) noexcept {
  return catalog.slot_openings.size()==308 && catalog.special_effects.size()==100 &&
         catalog.special_wexp==1500 && catalog.special_material.item==33554961 &&
         catalog.special_material.count==3;
}
} // namespace diamond
