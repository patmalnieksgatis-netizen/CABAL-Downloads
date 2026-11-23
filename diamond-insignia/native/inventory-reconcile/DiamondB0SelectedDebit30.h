#pragma once
// CABAL v291: staged, non-mutating 100-ticket GameData debit from multiple
// B0 material stacks, with explicit authoritative WorldSvr->SQL slot mapping.
// NEVER applies SQL, changes a live WorldSvr record or sends an S2C success.
// A 0BDA selection plan and independent same-character mapping are mandatory.
// Even full deletion is not allowed until exact WorldSvr removal semantics
// are proven. No upstream code may set these proof flags on mere catalog data.
#include "DiamondB0PartialDebit30.h"
#include "../grade2-ingress/Diamond0BDATicketSelection.h"
#include <cstddef>
#include <cstdint>
#include <set>
#include <utility>
#include <vector>

namespace diamond_v291::inventory {
struct B0WorldToPersistedSlot {
    std::uint16_t selectedWorldSlot=0;
    std::uint16_t persistedPhysicalSlot=0;
    std::uint64_t persistedSerial=0;
};
struct B0SelectionPersistenceProof {
    PersistedB0QuantityAuthority persisted{};
    std::uint32_t userNum=0;
    std::uint32_t characterIdx=0;
    bool authenticatedWorldOwnerLockHeld=false;
    bool sameUserAndCharacterProvenFromServer=false;
    bool worldSlotsMappedToPersistedRowsUnderOwnerLock=false;
    // Full depletion is NOT proven on the owner's WorldSvr. Keep false.
    bool fullStackRecordRemovalVerified=false;
};
enum class B0SelectedDebitVerdict : std::uint8_t {
    UnverifiedOwner, UnverifiedSelection, InvalidBlob,
    InvalidWorldToSavedSlotMap, WrongItemOrAmount,
    CannotRemoveFullStack, InvalidOtherInventory,
    PostDebitReconcileFailed, PreparedClone, AllocationFailed
};
struct B0SelectedDebitClone {
    B0SelectedDebitVerdict verdict=B0SelectedDebitVerdict::UnverifiedOwner;
    std::vector<std::uint8_t> proposedGameData{};
    std::uint64_t allTicketUnitsBefore=0;
    std::uint64_t allTicketUnitsAfter=0;
    std::size_t consumedWholeRecords=0;
    bool liveWorldOrSqlChanged=false; // never true
};
inline B0SelectedDebitClone StageVerifiedB0SelectedDebit100(
    const std::uint8_t* before,std::size_t bytes,
    const diamond_v291::gradeup0bda::TicketDebitPlan& plan,
    const B0WorldToPersistedSlot* binding,std::size_t bindingCount,
    const B0SelectionPersistenceProof& evidence) noexcept {
    B0SelectedDebitClone result{};
    if(!evidence.userNum || !evidence.characterIdx ||
       !evidence.authenticatedWorldOwnerLockHeld ||
       !evidence.sameUserAndCharacterProvenFromServer ||
       !evidence.worldSlotsMappedToPersistedRowsUnderOwnerLock ||
       !evidence.persisted.gameDataRow30LayoutIndependentlyVerified ||
       !evidence.persisted.sameCharacterSnapshotAndSessionVerified ||
       !evidence.persisted.originalSqlTableAttested)
        return result;
    using diamond_v291::gradeup0bda::SelectionVerdict;
    if(plan.status!=SelectionVerdict::ExactDebitPlan ||
       plan.exactPlannedDebit!=100 ||
       !plan.selectedCount ||
       plan.selectedCount>diamond_v291::gradeup0bda::kMaxAttestableEntries ||
       plan.selectedCount!=bindingCount || !binding ||
       plan.selectedUnits<100) {
        result.verdict=B0SelectedDebitVerdict::UnverifiedSelection;
        return result;
    }
    if(!before || bytes==0 || bytes>kPersistedRowBytes*kMaxInventoryRows ||
       (bytes%kPersistedRowBytes)!=0) {
        result.verdict=B0SelectedDebitVerdict::InvalidBlob;
        return result;
    }
    try {
        std::set<std::uint16_t> worldSlots;
        std::set<std::uint16_t> mappedSlots;
        std::set<std::uint64_t> mappedSerials;
        std::uint32_t toDebit=0;
        for(std::size_t i=0;i<bindingCount;++i) {
            const auto& row=plan.slots[i];
            const auto& map=binding[i];
            if(!row.availableBefore || !row.debitPlanned ||
               row.availableBefore>kRealB0TicketMaxStack ||
               row.debitPlanned>row.availableBefore ||
               row.expectedRemaining!=row.availableBefore-row.debitPlanned ||
               row.removeEmptyRecord!=(row.expectedRemaining==0) ||
               row.slot!=map.selectedWorldSlot ||
               map.selectedWorldSlot>diamond_v291::gradeup0bda::kWorldInventoryMaxSlot ||
               map.persistedPhysicalSlot<47 || map.persistedPhysicalSlot>511 ||
               !map.persistedSerial ||
               !worldSlots.insert(map.selectedWorldSlot).second ||
               !mappedSlots.insert(map.persistedPhysicalSlot).second ||
               !mappedSerials.insert(map.persistedSerial).second) {
                result.verdict=B0SelectedDebitVerdict::InvalidWorldToSavedSlotMap;
                return result;
            }
            toDebit+=row.debitPlanned;
        }
        if(toDebit!=100) {
            result.verdict=B0SelectedDebitVerdict::InvalidWorldToSavedSlotMap;
            return result;
        }
        std::vector<bool> found(bindingCount,false);
        std::set<std::uint64_t> seenSerials;
        std::set<std::uint16_t> seenSlots;
        std::vector<std::uint8_t> staged;
        staged.reserve(bytes);
        std::uint64_t beforeTotal=0;
        std::uint64_t afterTotal=0;
        std::size_t removed=0;
        for(std::size_t offset=0;offset<bytes;offset+=kPersistedRowBytes) {
            const auto* ptr=before+offset;
            Record30 row{
                internal::GetU64(ptr+0),
                internal::GetU64(ptr+8),
                internal::GetU64(ptr+16),
                internal::GetU16(ptr+24),
                internal::GetU32(ptr+26)
            };
            if(!row.itemId || !row.itemSerial ||
               row.physicalSlot<47 || row.physicalSlot>511 ||
               !seenSerials.insert(row.itemSerial).second ||
               !seenSlots.insert(row.physicalSlot).second) {
                result.verdict=B0SelectedDebitVerdict::InvalidOtherInventory;
                return result;
            }
            std::size_t match=bindingCount;
            for(std::size_t i=0;i<bindingCount;++i) {
                if(row.physicalSlot==binding[i].persistedPhysicalSlot ||
                   row.itemSerial==binding[i].persistedSerial) {
                    if(row.physicalSlot!=binding[i].persistedPhysicalSlot ||
                       row.itemSerial!=binding[i].persistedSerial) {
                        result.verdict=B0SelectedDebitVerdict::InvalidWorldToSavedSlotMap;
                        return result;
                    }
                    match=i;
                    break;
                }
            }
            if(match==bindingCount) {
                if(row.itemId==kRealB0TicketItem) {
                    std::uint32_t unchangedUnits=0;
                    auto codec=evidence.persisted;
                    if(!DecodeVerifiedB0PersistedRecord(
                        &codec,row,&unchangedUnits)) {
                        result.verdict=B0SelectedDebitVerdict::WrongItemOrAmount;
                        return result;
                    }
                    beforeTotal+=unchangedUnits;
                    afterTotal+=unchangedUnits;
                }
                staged.insert(staged.end(),ptr,ptr+kPersistedRowBytes);
                continue;
            }
            const auto& selected=plan.slots[match];
            if(found[match] || row.itemId!=kRealB0TicketItem) {
                result.verdict=B0SelectedDebitVerdict::InvalidWorldToSavedSlotMap;
                return result;
            }
            found[match]=true;
            std::uint32_t units=0;
            auto codec=evidence.persisted;
            if(!DecodeVerifiedB0PersistedRecord(&codec,row,&units) ||
               units!=selected.availableBefore) {
                result.verdict=B0SelectedDebitVerdict::WrongItemOrAmount;
                return result;
            }
            beforeTotal+=units;
            if(selected.expectedRemaining==0) {
                if(!evidence.fullStackRecordRemovalVerified) {
                    result.verdict=B0SelectedDebitVerdict::CannotRemoveFullStack;
                    return result;
                }
                ++removed;
                continue;
            }
            auto updated=std::vector<std::uint8_t>(
                ptr,ptr+kPersistedRowBytes);
            // All supported profiles reject unknown option flag bits.
            // Record30 only changes bytes +16..+23. No serial moves.
            internal::PutU64(updated.data()+16,
                static_cast<std::uint64_t>(selected.expectedRemaining));
            staged.insert(staged.end(),updated.begin(),updated.end());
            afterTotal+=selected.expectedRemaining;
        }
        for(bool ok:found) if(!ok) {
            result.verdict=B0SelectedDebitVerdict::InvalidWorldToSavedSlotMap;
            return result;
        }
        if(beforeTotal<100 || beforeTotal-afterTotal!=100) {
            result.verdict=B0SelectedDebitVerdict::WrongItemOrAmount;
            return result;
        }
        auto proof=evidence.persisted;
        const PersistedBlob beforeBlob{before,bytes,true};
        const PersistedBlob afterBlob{staged.data(),staged.size(),true};
        const auto audit=VerifyPersistedTicketDebit(
            beforeBlob,afterBlob,beforeTotal,afterTotal,
            &DecodeVerifiedB0PersistedRecord,&proof);
        if(!audit.Verified()) {
            result.verdict=B0SelectedDebitVerdict::PostDebitReconcileFailed;
            return result;
        }
        result.allTicketUnitsBefore=beforeTotal;
        result.allTicketUnitsAfter=afterTotal;
        result.consumedWholeRecords=removed;
        result.proposedGameData=std::move(staged);
        result.verdict=B0SelectedDebitVerdict::PreparedClone;
    }catch(...) {
        result.verdict=B0SelectedDebitVerdict::AllocationFailed;
        result.proposedGameData.clear();
    }
    return result;
}
} // namespace diamond_v291::inventory
