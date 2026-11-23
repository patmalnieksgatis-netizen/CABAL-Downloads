#include "DiamondWorldProcRegistryPreflight.h"
#include <array>
#include <cassert>
#include <iostream>
using namespace diamond_v291::gradeup0bda;
int main(){
    int original=1,cancel=2,newer=3;
    std::array<const void*,kUserProcSlotCount> slots{};
    assert(InspectUserProcedureSnapshot(nullptr,0,true,true).status==
           RegistryStatus::BadSnapshot);
    assert(InspectUserProcedureSnapshot(slots.data(),17,true,true).status==
           RegistryStatus::BadSnapshot);
    slots[kOriginalPlatinumGradeUpSlot]=&original;
    slots[kOriginalPlatinumSlotCancelSlot]=&cancel;
    auto check=[&](bool exact,bool locked) {
        return InspectUserProcedureSnapshot(slots.data(),slots.size(),exact,locked);
    };
    assert(check(false,true).status==RegistryStatus::UnverifiedWorldBinaryOrLock);
    assert(check(true,false).status==RegistryStatus::UnverifiedWorldBinaryOrLock);
    slots[kOriginalPlatinumSlotCancelSlot]=nullptr;
    assert(check(true,true).status==RegistryStatus::PlatinumHandlersMissing);
    slots[kOriginalPlatinumSlotCancelSlot]=&original;
    assert(check(true,true).status==RegistryStatus::PlatinumHandlersMissing);
    slots[kOriginalPlatinumSlotCancelSlot]=&cancel;
    slots[kCandidateGrade2GradeUpSlot]=&newer;
    const auto collision=check(true,true);
    assert(collision.status==RegistryStatus::CandidateSlotOccupied);
    assert(collision.originalPlatinumPreserved && !collision.mayInstall);
    slots[kCandidateGrade2GradeUpSlot]=nullptr;
    const auto empty=check(true,true);
    assert(empty.status==RegistryStatus::FreeSlotNeedsHostProcedureMapAbiProof);
    assert(empty.originalPlatinumPreserved && !empty.mayInstall);
    assert(slots[kOriginalPlatinumGradeUpSlot]==&original);
    assert(slots[kOriginalPlatinumSlotCancelSlot]==&cancel);
    assert(slots[kCandidateGrade2GradeUpSlot]==nullptr);
    assert(kExactWorldUserProcMapAddr==0x235F8C0u);
    assert(kCandidateGrade2GradeUpSlot==0x0BDAu);
    std::cout<<"WORLDSVR_REGISTRY_SLOT_0BDA_COLLISION_PREFLIGHT=PASS\n"
             <<"WORLDSVR_EXISTING_0B10_0B13_PRESERVED=PASS\n"
             <<"WORLDSVR_PROCEDUREMAP_ABI_UNPROVEN_INSTALL_DISABLED=PASS\n";
}
