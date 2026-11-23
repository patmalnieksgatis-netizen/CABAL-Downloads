#pragma once
// CABAL v291: stage ONLY a 100-ticket partial debit in an owned COPY of
// an independently verified 30-byte GameData inventory. No SQL or live writes.
// This is a narrow candidate adapter, NOT the live WorldSvr 0BDA handler.
// Full-stack deletion, slot remapping and any unknown B0 encoding fail closed.
#include "DiamondB0PersistedQuantity.h"
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <set>
#include <vector>

namespace diamond_v291::inventory {
struct B0PartialDebitOwnerProof {
    PersistedB0QuantityAuthority persisted{};
    bool worldUserAndCharacterOwnerLockVerified=false;
    bool persistedPhysicalSlotMatchesWorldSelectionVerified=false;
    bool callerHoldsExclusiveGameInventoryLease=false;
    std::uint64_t expectedItemSerial=0;
    std::uint16_t expectedPhysicalSlot=0;
    std::uint32_t expectedStackAmount=0;
};
enum class B0PartialDebitStatus : std::uint8_t {
    MissingOwnerOrSlotProof, InvalidBlob, DuplicateSlotOrSerial,
    MissingTarget, WrongTicketOrQuantity, CannotDeleteEntireStack,
    PreparedClone, AllocationFailed
};
struct B0PartialDebitProposal {
    B0PartialDebitStatus status=B0PartialDebitStatus::MissingOwnerOrSlotProof;
    std::vector<std::uint8_t> proposedGameData{};
    std::uint32_t beforeUnits=0;
    std::uint32_t afterUnits=0;
    bool wroteLiveGameData=false;  // ALWAYS false
};
namespace internal {
inline std::uint64_t GetU64(const std::uint8_t* p) noexcept {
    std::uint64_t out=0;
    for(unsigned i=0;i<8;++i)out|=(std::uint64_t(p[i])<<(8u*i));
    return out;
}
inline std::uint16_t GetU16(const std::uint8_t* p) noexcept {
    return static_cast<std::uint16_t>(p[0] | (std::uint16_t(p[1])<<8));
}
inline std::uint32_t GetU32(const std::uint8_t* p) noexcept {
    std::uint32_t out=0;
    for(unsigned i=0;i<4;++i)out|=(std::uint32_t(p[i])<<(8u*i));
    return out;
}
inline void PutU64(std::uint8_t* p,std::uint64_t x) noexcept {
    for(unsigned i=0;i<8;++i)p[i]=static_cast<std::uint8_t>(x>>(8u*i));
}
} // namespace internal

inline B0PartialDebitProposal StageB0TicketPartialDebit100(
    const std::uint8_t* original,std::size_t bytes,
    const B0PartialDebitOwnerProof& proof) noexcept {
    B0PartialDebitProposal out{};
    if(!proof.worldUserAndCharacterOwnerLockVerified ||
       !proof.persistedPhysicalSlotMatchesWorldSelectionVerified ||
       !proof.callerHoldsExclusiveGameInventoryLease ||
       !proof.persisted.gameDataRow30LayoutIndependentlyVerified ||
       !proof.persisted.sameCharacterSnapshotAndSessionVerified ||
       !proof.persisted.originalSqlTableAttested ||
       !proof.expectedItemSerial ||
       proof.expectedPhysicalSlot<47 || proof.expectedPhysicalSlot>511 ||
       !proof.expectedStackAmount)
        return out;
    if(!original || bytes==0 ||
       bytes>kPersistedRowBytes*kMaxInventoryRows ||
       bytes%kPersistedRowBytes!=0) {
        out.status=B0PartialDebitStatus::InvalidBlob;
        return out;
    }
    try {
        // A copy is the ONLY output; no edits to caller's input bytes.
        std::vector<std::uint8_t> clone(original,original+bytes);
        std::set<std::uint64_t> serials;
        std::set<std::uint16_t> slots;
        std::size_t matched=0;
        std::size_t targetOffset=0;
        std::uint32_t verifiedUnits=0;
        for(std::size_t offset=0;offset<bytes;offset+=kPersistedRowBytes) {
            const auto* row=original+offset;
            const auto id=internal::GetU64(row);
            const auto serial=internal::GetU64(row+8);
            const auto slot=internal::GetU16(row+24);
            if(!id || !serial || slot<47 || slot>511) {
                out.status=B0PartialDebitStatus::InvalidBlob;
                return out;
            }
            if(!serials.insert(serial).second ||
               !slots.insert(slot).second) {
                out.status=B0PartialDebitStatus::DuplicateSlotOrSerial;
                return out;
            }
            if(serial==proof.expectedItemSerial ||
               slot==proof.expectedPhysicalSlot) {
                if(serial!=proof.expectedItemSerial ||
                   slot!=proof.expectedPhysicalSlot ||
                   id!=kRealB0TicketItem) {
                    out.status=B0PartialDebitStatus::WrongTicketOrQuantity;
                    return out;
                }
                ++matched;
                targetOffset=offset;
                const Record30 src{
                    id,serial,internal::GetU64(row+16),
                    slot,internal::GetU32(row+26)
                };
                if(!DecodeVerifiedB0PersistedRecord(
                       const_cast<PersistedB0QuantityAuthority*>(&proof.persisted),
                       src,&verifiedUnits) ||
                   verifiedUnits!=proof.expectedStackAmount) {
                    out.status=B0PartialDebitStatus::WrongTicketOrQuantity;
                    return out;
                }
            }
        }
        if(matched!=1) {
            out.status=B0PartialDebitStatus::MissingTarget;
            return out;
        }
        if(verifiedUnits<=100) {
            out.status=B0PartialDebitStatus::CannotDeleteEntireStack;
            return out;
        }
        const std::uint32_t next=verifiedUnits-100;
        const auto raw=internal::GetU64(original+targetOffset+16);
        const auto mode=proof.persisted.codecProof.provenProfile;
        const std::uint64_t mask=
            mode==B0CountProfile::OptionLow10 ? 0x3FFULL :
            mode==B0CountProfile::OptionLow16 ? 0xFFFFULL : 0ULL;
        if(!mask || (raw&~mask)) {
            out.status=B0PartialDebitStatus::WrongTicketOrQuantity;
            return out;
        }
        internal::PutU64(clone.data()+targetOffset+16,
                         (raw&~mask)|next);
        out.beforeUnits=verifiedUnits;
        out.afterUnits=next;
        out.proposedGameData=std::move(clone);
        out.status=B0PartialDebitStatus::PreparedClone;
    } catch(...) {
        out.status=B0PartialDebitStatus::AllocationFailed;
        out.proposedGameData.clear();
    }
    return out;
}
} // namespace diamond_v291::inventory
