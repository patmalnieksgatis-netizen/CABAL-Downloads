#pragma once
// Read-only preflight for actual WorldSvr user-procedure registration table.
// Owner's archived WorldSvrRealm/PacketManager/PacketManager.cpp maps
// g_sUsrProcedureMap to 0x0235F8C0 (fixed exact ELF; not portable).
// PacketManager/Protodefs.h defines MAX_MAINCMDNUMBER 3999.
// This module NEVER writes a procedure map, allocates a PROCEDUREMAP, or
// hooks/dereferences hardcoded guest addresses. Runtime host owns table memory.
#include <cstddef>
#include <cstdint>
namespace diamond_v291::gradeup0bda {
constexpr std::uintptr_t kExactWorldUserProcMapAddr=0x0235F8C0u;
constexpr std::size_t kUserProcSlotCount=3999u;
constexpr std::size_t kOriginalPlatinumGradeUpSlot=0x0B10u;
constexpr std::size_t kOriginalPlatinumSlotCancelSlot=0x0B13u;
constexpr std::size_t kCandidateGrade2GradeUpSlot=0x0BDAu;
static_assert(kCandidateGrade2GradeUpSlot<kUserProcSlotCount);
enum class RegistryStatus : std::uint8_t {
    BadSnapshot, UnverifiedWorldBinaryOrLock, PlatinumHandlersMissing,
    CandidateSlotOccupied, FreeSlotNeedsHostProcedureMapAbiProof
};
struct RegistryInspection {
    RegistryStatus status=RegistryStatus::BadSnapshot;
    bool mayInstall=false; // deliberately ALWAYS false: host STL ABI unverified
    bool originalPlatinumPreserved=false;
};
// The trusted host must own the read-lock and attest exact same ELF hash.
// The parameter is an already safely mapped *snapshot* of the registry
// pointer array; never derive it from an unauthenticated network field.
inline RegistryInspection InspectUserProcedureSnapshot(
    const void* const* slots,std::size_t readableSlots,
    bool exactWorldBinaryAttested,bool hostRegistrationLockHeld) noexcept {
    RegistryInspection out{};
    if(!slots || readableSlots<kUserProcSlotCount)
        return out;
    if(!exactWorldBinaryAttested || !hostRegistrationLockHeld) {
        out.status=RegistryStatus::UnverifiedWorldBinaryOrLock;
        return out;
    }
    const auto* original=slots[kOriginalPlatinumGradeUpSlot];
    const auto* cancel=slots[kOriginalPlatinumSlotCancelSlot];
    if(!original || !cancel || original==cancel) {
        out.status=RegistryStatus::PlatinumHandlersMissing;
        return out;
    }
    out.originalPlatinumPreserved=true;
    if(slots[kCandidateGrade2GradeUpSlot]) {
        out.status=RegistryStatus::CandidateSlotOccupied;
        return out;
    }
    out.status=RegistryStatus::FreeSlotNeedsHostProcedureMapAbiProof;
    // CRITICAL: Even an empty slot is not authorization to write an
    // extension-allocated PROCEDUREMAP into a different glibc++ ABI.
    out.mayInstall=false;
    return out;
}
} // namespace diamond_v291::gradeup0bda
