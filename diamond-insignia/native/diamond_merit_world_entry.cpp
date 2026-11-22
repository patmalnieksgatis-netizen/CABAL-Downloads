#include "diamond_merit_world_entry.h"
#include <cstdint>
namespace {
std::uint16_t le16(const std::uint8_t* b) {
 return static_cast<std::uint16_t>(b[0] | (static_cast<std::uint16_t>(b[1])<<8u));
}
std::uint32_t le32(const std::uint8_t* b) {
 return static_cast<std::uint32_t>(b[0]) |
   (static_cast<std::uint32_t>(b[1])<<8u) |
   (static_cast<std::uint32_t>(b[2])<<16u) |
   (static_cast<std::uint32_t>(b[3])<<24u);
}
}
extern "C" int cabal_diamond_merit_classify_c2s(
 const void* buffer,size_t length,cabal_merit_packet_view* result) {
 if(!result)return -1;
 *result={};
 result->version=CABAL_DIAMOND_MERIT_GATE_VERSION;
 result->kind=CABAL_MERIT_PACKET_INVALID;
 if(!buffer || length<CABAL_DIAMOND_MERIT_C2S_HEADER_BYTES || length>65535u)return 0;
 const auto* data=static_cast<const std::uint8_t*>(buffer);
 if(le16(data)!=CABAL_DIAMOND_LEGACY_C2S_MAGIC) {
   // Other/extended packet header stays entirely with the original WorldSvr.
   result->kind=CABAL_MERIT_PACKET_ORIGINAL;
   return 0;
 }
 const auto declared=le16(data+2);
 const auto opcode=le16(data+8);
 result->packet_length=declared;
 result->main_command=opcode;
 if(declared!=length)return 0;
 result->kind=CABAL_MERIT_PACKET_ORIGINAL;
 // 0x0B10 is original Platinum Badge Grade Up: NEVER repurpose it as Diamond.
 if(opcode!=CABAL_DIAMOND_MERIT_C2S_MASTER_UP)return 0;
 // Current ELF reads two DWORDs at offsets +0xA / +0xE; only 18-byte
 // classic packets are supported by this opt-in, non-invasive classifier.
 if(length!=CABAL_DIAMOND_MERIT_C2S_LEVELUP_BYTES)return 0;
 result->candidate_mastery_index=le32(data+10);
 result->unknown_field_at_0x0e=le32(data+14);
 if(result->candidate_mastery_index>=159u && result->candidate_mastery_index<=474u)
   result->kind=CABAL_MERIT_PACKET_DIAMOND_CANDIDATE;
 return 0;
}
extern "C" int cabal_diamond_merit_shadow_route(
 const cabal_diamond_engine* engine,const void* bytes,size_t len,
 const void* session,uint32_t user,uint32_t trusted_revision,
 const cabal_diamond_world_callbacks* callbacks,void* callback_context,
 uint32_t enabled,cabal_diamond_world_result* world,
 cabal_merit_route_result* route) {
 if(!route || !world)return -1;
 *world={};
 *route=CABAL_MERIT_ROUTE_INVALID;
 cabal_merit_packet_view view{};
 if(cabal_diamond_merit_classify_c2s(bytes,len,&view)!=0)return -2;
 if(view.kind==CABAL_MERIT_PACKET_INVALID)return 0;
 if(view.kind!=CABAL_MERIT_PACKET_DIAMOND_CANDIDATE) {
   *route=CABAL_MERIT_ROUTE_ORIGINAL;
   return 0;
 }
#if !defined(DIAMOND_ENABLE_SHADOW_TRIAL)
 // Production builds are classification-only. No Diamond SQL/WExp/item effects.
 (void)engine;(void)session;(void)user;(void)trusted_revision;
 (void)callbacks;(void)callback_context;(void)enabled;
 *route=CABAL_MERIT_ROUTE_DISABLED;
 return 0;
#else
 if(enabled!=1){
   *route=CABAL_MERIT_ROUTE_DISABLED;
   return 0;
 }
 if(!engine || !session || !user || !callbacks || trusted_revision==0)
   return -3;
 const cabal_diamond_request cmd{
   CABAL_DIAMOND_ABI_VERSION,CABAL_DIAMOND_MASTERY_LEVEL_UP,
   trusted_revision,static_cast<std::int32_t>(view.candidate_mastery_index)
 };
 const int status=cabal_diamond_world_execute(engine,session,user,&cmd,
                                               callbacks,callback_context,world);
 if(status!=0)return status;
 *route=(world->status==CABAL_DIAMOND_WORLD_APPLIED)
   ? CABAL_MERIT_ROUTE_SHADOW_APPLIED:CABAL_MERIT_ROUTE_SHADOW_REJECTED;
 return 0;
#endif // DIAMOND_ENABLE_SHADOW_TRIAL
}
