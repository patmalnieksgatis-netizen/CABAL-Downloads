#include "DiamondInventoryReconcile.h"
#include <cstring>
#include <limits>
#include <map>
#include <set>

namespace diamond_v291::inventory {
namespace {
Record30 ReadRow(const unsigned char* p) noexcept {
    Record30 row{};
    // Never dereference an unaligned 30-byte row via a native struct pointer.
    std::memcpy(&row.itemId,p+0x00,8);
    std::memcpy(&row.itemSerial,p+0x08,8);
    std::memcpy(&row.itemOption,p+0x10,8);
    std::memcpy(&row.physicalSlot,p+0x18,2);
    std::memcpy(&row.duration,p+0x1A,4);
    return row;
}
bool Equal(const Record30& a,const Record30& b) noexcept {
    return a.itemId==b.itemId && a.itemSerial==b.itemSerial &&
           a.itemOption==b.itemOption && a.physicalSlot==b.physicalSlot &&
           a.duration==b.duration;
}
struct Parsed {
    std::map<std::uint64_t,Record30> records;
    std::set<std::uint16_t> slots;
    std::uint64_t units=0;
    std::size_t targetRows=0;
};
AuditStatus Parse(PersistedBlob blob,QuantityDecoder decoder,void* context,
                  Parsed& out) {
    if((blob.length && !blob.bytes) ||
       blob.length>kPersistedRowBytes*kMaxInventoryRows ||
       blob.length%kPersistedRowBytes!=0)
        return AuditStatus::MalformedSnapshot;
    const auto* bytes=static_cast<const unsigned char*>(blob.bytes);
    for(std::size_t i=0;i<blob.length;i+=kPersistedRowBytes) {
        const Record30 row=ReadRow(bytes+i);
        // v14 normal inventory stores physical slots 47..511.
        if(!row.itemId || !row.itemSerial ||
           row.physicalSlot<47 || row.physicalSlot>511)
            return AuditStatus::InvalidRecord;
        if(!out.records.emplace(row.itemSerial,row).second ||
           !out.slots.insert(row.physicalSlot).second)
            return AuditStatus::DuplicateSerialOrSlot;
        if(row.itemId!=kExchangeTicketItemId)continue;
        std::uint32_t quantity=0;
        if(!decoder(context,row,&quantity) || !quantity ||
           out.units>std::numeric_limits<std::uint64_t>::max()-quantity)
            return AuditStatus::QuantityCodecFailed;
        out.units+=quantity;++out.targetRows;
    }
    return AuditStatus::Verified;
}
}
Audit VerifyPersistedTicketDebit(PersistedBlob before,PersistedBlob after,
     std::uint64_t expectedBeforeUnits,std::uint64_t expectedAfterUnits,
     QuantityDecoder decoder,void* decoderContext) noexcept {
    Audit result{};
    if(!before.independentGameDataRead || !after.independentGameDataRead)
        return result;
    if(!decoder) {
        result.status=AuditStatus::MissingQuantityCodec;
        return result;
    }
    try {
        Parsed original{},saved{};
        result.status=Parse(before,decoder,decoderContext,original);
        if(result.status!=AuditStatus::Verified)return result;
        result.status=Parse(after,decoder,decoderContext,saved);
        if(result.status!=AuditStatus::Verified)return result;
        result.beforeUnits=original.units;result.afterUnits=saved.units;
        result.beforeTargetRows=original.targetRows;
        result.afterTargetRows=saved.targetRows;
        // No unrelated inventory record may be created, removed or changed
        // in a Diamond-only operation. That would be an ambiguous save.
        for(const auto& entry:original.records) {
            if(entry.second.itemId==kExchangeTicketItemId)continue;
            const auto pos=saved.records.find(entry.first);
            if(pos==saved.records.end() || !Equal(pos->second,entry.second)) {
                result.status=AuditStatus::UnrelatedInventoryChanged;
                return result;
            }
        }
        for(const auto& entry:saved.records) {
            if(entry.second.itemId==kExchangeTicketItemId)continue;
            const auto pos=original.records.find(entry.first);
            if(pos==original.records.end() || !Equal(pos->second,entry.second)) {
                result.status=AuditStatus::UnrelatedInventoryChanged;
                return result;
            }
        }
        // A consumed stack may shrink or vanish, but may not move slots,
        // change serial identity, become another item, or spawn new items.
        for(const auto& entry:original.records) {
            if(entry.second.itemId!=kExchangeTicketItemId)continue;
            const auto found=saved.records.find(entry.first);
            if(found==saved.records.end())continue; // fully consumed stack
            const Record30& prior=entry.second;
            const Record30& current=found->second;
            if(current.itemId!=kExchangeTicketItemId ||
               current.physicalSlot!=prior.physicalSlot ||
               current.duration!=prior.duration) {
                result.status=AuditStatus::TicketIdentityChanged;
                return result;
            }
        }
        for(const auto& entry:saved.records) {
            if(entry.second.itemId!=kExchangeTicketItemId)continue;
            if(original.records.find(entry.first)==original.records.end()) {
                result.status=AuditStatus::TicketIdentityChanged;
                return result;
            }
        }
        // Rank-up must actually decrease independent persisted game resources.
        if(expectedBeforeUnits<=expectedAfterUnits ||
           original.units!=expectedBeforeUnits ||
           saved.units!=expectedAfterUnits) {
            result.status=AuditStatus::TicketTotalsMismatch;
            return result;
        }
        result.status=AuditStatus::Verified;
        return result;
    }catch(...){
        result.status=AuditStatus::MalformedSnapshot;
        return result;
    }
}
const char* Name(AuditStatus s) noexcept {
    switch(s) {
        case AuditStatus::Verified:return "Verified";
        case AuditStatus::UnattestedSnapshot:return "UnattestedSnapshot";
        case AuditStatus::MalformedSnapshot:return "MalformedSnapshot";
        case AuditStatus::InvalidRecord:return "InvalidRecord";
        case AuditStatus::DuplicateSerialOrSlot:return "DuplicateSerialOrSlot";
        case AuditStatus::MissingQuantityCodec:return "MissingQuantityCodec";
        case AuditStatus::QuantityCodecFailed:return "QuantityCodecFailed";
        case AuditStatus::UnrelatedInventoryChanged:return "UnrelatedInventoryChanged";
        case AuditStatus::TicketIdentityChanged:return "TicketIdentityChanged";
        case AuditStatus::TicketTotalsMismatch:return "TicketTotalsMismatch";
    }
    return "Unknown";
}
} // namespace diamond_v291::inventory
