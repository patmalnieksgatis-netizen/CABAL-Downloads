#include "../DiamondB0PersistedQuantity.h"
#include <array>
#include <cassert>
#include <cstdint>
#include <iostream>

using namespace diamond_v291::inventory;
namespace {
void U64(unsigned char* p,std::uint64_t n){
    for(unsigned i=0;i<8;++i)p[i]=static_cast<unsigned char>(n>>(i*8u));
}
void U32(unsigned char* p,std::uint32_t n){
    for(unsigned i=0;i<4;++i)p[i]=static_cast<unsigned char>(n>>(i*8u));
}
void U16(unsigned char* p,std::uint16_t n){
    for(unsigned i=0;i<2;++i)p[i]=static_cast<unsigned char>(n>>(i*8u));
}
std::array<unsigned char,30> Row(std::uint64_t opt){
    std::array<unsigned char,30> row{};
    U64(row.data()+0,33554961ULL);
    U64(row.data()+8,773311ULL); // synthetic serial, never live
    U64(row.data()+16,opt);
    U16(row.data()+24,47u);
    U32(row.data()+26,0u);
    return row;
}
B0QuantityEvidence SyntheticProof(){
    B0QuantityEvidence p{};
    p.provenProfile=B0CountProfile::OptionLow10;
    p.independentlyMatchedKnownQuantity=true; // SYNTHETIC ONLY
    p.sameGameBuildAndMaterialKindVerified=true; // SYNTHETIC ONLY
    p.optionLayoutVerified=true; // SYNTHETIC ONLY
    p.extraOptionFlagsProvenAbsent=true; // SYNTHETIC ONLY
    return p;
}
}
int main(){
    const auto observed=InspectUnprovenB0Option(0x3E7ULL);
    assert(observed.low10==999 && observed.low16==999);
    assert(observed.bothMatchObserved999 && !observed.profileIdentified);

    auto x=SyntheticProof();
    auto read=DecodeB0QuantityWithIndependentProof(
        999,0xB0,999,x);
    assert(read.verdict==B0QuantityVerdict::VerifiedCount &&
           read.quantity==999);
    x.independentlyMatchedKnownQuantity=false;
    assert(DecodeB0QuantityWithIndependentProof(999,0xB0,999,x).verdict==
           B0QuantityVerdict::MissingIndependentEvidence);
    x=SyntheticProof();
    assert(DecodeB0QuantityWithIndependentProof(1000,0xB0,999,x).verdict==
           B0QuantityVerdict::InvalidCount);
    assert(DecodeB0QuantityWithIndependentProof(0,0xB0,999,x).verdict==
           B0QuantityVerdict::InvalidCount);
    assert(DecodeB0QuantityWithIndependentProof(0x1000u|999u,0xB0,999,x).verdict==
           B0QuantityVerdict::UnverifiedOptionFlags);
    assert(DecodeB0QuantityWithIndependentProof(999,0xAF,999,x).verdict==
           B0QuantityVerdict::UnexpectedMetadata);
    assert(DecodeB0QuantityWithIndependentProof(999,0xB0,127,x).verdict==
           B0QuantityVerdict::UnexpectedMetadata);

    auto before=Row(999);
    auto after=Row(899);
    const PersistedBlob old{before.data(),before.size(),true};
    const PersistedBlob now{after.data(),after.size(),true};
    PersistedB0QuantityAuthority authority{};
    authority.codecProof=SyntheticProof();
    auto unchecked=VerifyPersistedTicketDebit(old,now,999,899,
        &DecodeVerifiedB0PersistedRecord,&authority);
    assert(unchecked.status==AuditStatus::QuantityCodecFailed);
    authority.gameDataRow30LayoutIndependentlyVerified=true;
    authority.sameCharacterSnapshotAndSessionVerified=true;
    authority.originalSqlTableAttested=true;
    const auto proven=VerifyPersistedTicketDebit(old,now,999,899,
        &DecodeVerifiedB0PersistedRecord,&authority);
    assert(proven.Verified() && proven.beforeUnits==999 &&
           proven.afterUnits==899);
    const auto wrong=VerifyPersistedTicketDebit(old,now,999,898,
        &DecodeVerifiedB0PersistedRecord,&authority);
    assert(wrong.status==AuditStatus::TicketTotalsMismatch);
    const PersistedBlob unverifiedNow{after.data(),after.size(),false};
    assert(VerifyPersistedTicketDebit(old,unverifiedNow,999,899,
        &DecodeVerifiedB0PersistedRecord,&authority).status==
        AuditStatus::UnattestedSnapshot);
    assert(VerifyPersistedTicketsUnchanged(old,now,999,
        &DecodeVerifiedB0PersistedRecord,&authority).status==
        AuditStatus::TicketIdentityChanged);
    authority.codecProof.independentlyMatchedKnownQuantity=false;
    assert(VerifyPersistedTicketDebit(old,now,999,899,
        &DecodeVerifiedB0PersistedRecord,&authority).status==
        AuditStatus::QuantityCodecFailed);
    assert(before==Row(999) && after==Row(899)); // never write to buffers
    std::cout<<"B0_SAVED_TWO_RAW_999_VALUES_NOT_A_VERIFIED_PROFILE=PASS\n"
             <<"B0_SYNTHETIC_INDEPENDENT_COUNT_999_TO_899_RECONCILIATION=PASS\n"
             <<"B0_UNVERIFIED_CATALOG_AND_PERSISTED_OWNER_FAIL_CLOSED=PASS\n";
}
