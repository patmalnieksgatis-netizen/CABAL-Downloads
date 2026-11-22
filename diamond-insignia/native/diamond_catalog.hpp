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
struct NativeCatalog {
  std::map<int,Mastery> diamond;
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
  std::map<std::pair<int,int>,int> costs;
  std::set<std::pair<int,int>> cost_keys;
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
      if (m.id<159 || m.id>474 || category_root(m.category)<0 ||
          m.max_level<1 || m.max_level>100 ||
          m.prerequisite_id<0 || m.prerequisite_id>474 ||
          m.prerequisite_level<0 || m.linked_id<0 || m.linked_id>474 ||
          m.linked_id==m.id)
        throw std::invalid_argument("INVALID_DIAMOND_MASTERY");
      if (!out.diamond.emplace(m.id,std::move(m)).second)
        throw std::invalid_argument("DUPLICATE_DIAMOND_MASTERY");
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
      costs.emplace(std::make_pair(idx,level),cost);
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
      const auto v=costs.find(std::make_pair(id,level));
      if (v==costs.end())throw std::invalid_argument("SCP_MASTERY_LEVEL_COST_MISSING");
      m.level_cost[static_cast<std::size_t>(level-1)]=v->second;
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
  return out;
}
} // namespace diamond
