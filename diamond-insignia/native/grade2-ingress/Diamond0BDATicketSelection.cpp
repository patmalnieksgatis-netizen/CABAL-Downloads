#include "Diamond0BDATicketSelection.h"
#include <algorithm>
#include <array>
#include <cstdint>
namespace diamond_v291::gradeup0bda {
TicketDebitPlan PlanTicketDebit(const Candidate& request,
                               const AttestedInventory& world) noexcept {
    TicketDebitPlan out{};
    if(request.state!=PacketState::Candidate || request.count==0 ||
       request.count>kMaxAttestableEntries) return out;
    if(!world.authenticatedWorldSession ||
       world.boundWorldSession!=world.authenticatedWorldSession ||
       !world.acquiredUnderExclusiveOwnerLock ||
       !world.recordsVerifiedFromWorldSession ||
       !world.registeredUserNum || !world.registeredCharacterIdx ||
       !world.trustedRevision) {
        out.status=SelectionVerdict::MissingOwnerAuthority;
        return out;
    }
    // The Platinum 0B10 server treats u16 entries as inventory indices,
    // but the corresponding 0BDA server handler is not in the original ELF.
    // Similar client packet shape is NOT proof of the new command's meaning.
    // Reject by default; even synthetic tests must opt in explicitly.
    if(!world.opcode0bdaSelectionMeansTicketSlotsVerified ||
       !world.selectionSemanticsBoundToGradeUpVerified) {
        out.status=SelectionVerdict::UnverifiedSelectionSemantics;
        return out;
    }
    if(!world.trustedRecords ||
       world.trustedRecordsBytes!=kWorldInventorySlots*kWorldInventoryEntryBytes) {
        out.status=SelectionVerdict::WrongSnapshotSize;
        return out;
    }
    if(!world.itemCatalog.fromTrustedWorldCatalog ||
       world.itemCatalog.catalogItemIndex!=(kTicket33554961&0xFFFu) ||
       world.itemCatalog.catalogVariant!=((kTicket33554961>>25u)&3u)) {
        out.status=SelectionVerdict::ItemMetadataMissing;
        return out;
    }
    // This predicate is only a READ-ONLY validation of the current snapshot.
    // The game backend must revalidate identities, slot versions and amount
    // while performing a separate durable debit, never copy this plan blindly.
    std::array<bool,kWorldInventorySlots> seen{};
    std::uint64_t sum=0;
    for(std::size_t i=0;i<request.count;++i) {
        const auto slot=request.rawEntries[i];
        if(slot>kWorldInventoryMaxSlot) {
            out.status=SelectionVerdict::SlotOutOfRange;
            return out;
        }
        if(seen[slot]) {
            out.status=SelectionVerdict::DuplicateSlot;
            return out;
        }
        seen[slot]=true;
        const auto* data=world.trustedRecords+
            static_cast<std::size_t>(slot)*kWorldInventoryEntryBytes;
        const auto decoded=DecodeTicketSlot48(
            data,kWorldInventoryEntryBytes,world.itemCatalog);
        switch(decoded.verdict) {
            case TicketUnitsVerdict::DecodedTicketQuantity:break;
            case TicketUnitsVerdict::UnverifiedMetadata:
                out.status=SelectionVerdict::ItemMetadataMissing;return out;
            case TicketUnitsVerdict::ZeroUnits:
                out.status=SelectionVerdict::ZeroOrInvalidTicketCount;return out;
            case TicketUnitsVerdict::MalformedRecord:
            case TicketUnitsVerdict::NotTicket:
                out.status=SelectionVerdict::InvalidTicketRecord;return out;
        }
        // Exact code branches bound the per-stack decoded amount to <=65535;
        // still use u64 so a future decoder cannot overflow a subtotal.
        sum+=decoded.quantity;
        if(sum>UINT32_MAX) {
            out.status=SelectionVerdict::ZeroOrInvalidTicketCount;
            return out;
        }
        out.slots[i].slot=slot;
        out.slots[i].availableBefore=decoded.quantity;
    }
    out.selectedCount=request.count;
    out.selectedUnits=static_cast<std::uint32_t>(sum);
    if(sum<kRequiredRankUpTickets) {
        out.status=SelectionVerdict::InsufficientTickets;
        return out;
    }
    std::uint32_t remaining=kRequiredRankUpTickets;
    for(std::size_t i=0;i<request.count;++i) {
        auto& row=out.slots[i];
        row.debitPlanned=std::min(remaining,row.availableBefore);
        row.expectedRemaining=row.availableBefore-row.debitPlanned;
        row.removeEmptyRecord=(row.debitPlanned!=0 && row.expectedRemaining==0);
        remaining-=row.debitPlanned;
    }
    if(remaining!=0) {
        out.status=SelectionVerdict::InsufficientTickets;
        return out;
    }
    out.exactPlannedDebit=kRequiredRankUpTickets;
    out.status=SelectionVerdict::ExactDebitPlan;
    return out;
}
} // namespace diamond_v291::gradeup0bda
