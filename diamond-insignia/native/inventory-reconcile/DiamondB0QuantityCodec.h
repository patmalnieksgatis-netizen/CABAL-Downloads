#pragma once
// CABAL v291 Material kind 0xB0, item 33554961. Observed evidence:
// two saved inventory rows each have 64-bit ItemOption 0x00000000000003E7,
// and runtime item metadata has kind=0xB0, max stack=999.
// BOTH low10 and low16 give 999. For *plain* option values 1..999 with
// no flags they also agree for every possible valid stack quantity.
// The new PlainPositiveOptionNoFlags profile permits this restricted case
// after independent SAME-STACK UI/native evidence, never from the raw 999
// sample alone. Other layouts still fail closed.
// Pure, allocation-free, read-only. NOT a GameData writer.
#include <cstdint>

namespace diamond_v291::inventory {
constexpr std::uint32_t kRealB0TicketItem=33554961u;
constexpr std::uint32_t kRealB0MaterialKind=0xB0u;
constexpr std::uint32_t kRealB0TicketMaxStack=999u;
constexpr std::uint64_t kObservedTicketOption20261123=0x3E7ULL;
enum class B0CountProfile : std::uint8_t {
    Unknown, OptionLow10, OptionLow16, PlainPositiveOptionNoFlags
};
struct B0QuantityEvidence {
    B0CountProfile provenProfile=B0CountProfile::Unknown;
    // Source attestation must be established from a known *actual* UI
    // count on the SAME material stack or the matched native decoding
    // implementation; sample of 999 alone never makes either true.
    bool independentlyMatchedKnownQuantity=false;
    bool sameGameBuildAndMaterialKindVerified=false;
    bool optionLayoutVerified=false;
    bool extraOptionFlagsProvenAbsent=false;
};
struct B0QuantityCandidates {
    std::uint32_t low10=0;
    std::uint32_t low16=0;
    bool bothMatchObserved999=false;
    bool profileIdentified=false; // Always false from raw option alone.
};
inline B0QuantityCandidates InspectUnprovenB0Option(
    std::uint64_t rawOption) noexcept {
    return {static_cast<std::uint32_t>(rawOption&0x3FFULL),
            static_cast<std::uint32_t>(rawOption&0xFFFFULL),
            rawOption==kObservedTicketOption20261123,
            false};
}
enum class B0QuantityVerdict : std::uint8_t {
    MissingIndependentEvidence, UnexpectedMetadata, UnknownProfile,
    UnverifiedOptionFlags, InvalidCount, VerifiedCount
};
struct B0QuantityResult {
    B0QuantityVerdict verdict=B0QuantityVerdict::MissingIndependentEvidence;
    std::uint32_t quantity=0;
};
// MAX stack 999 does NOT automatically attest the measured count.
// Never allow negative, zero, >999, or unverified option flag bits.
inline B0QuantityResult DecodeB0QuantityWithIndependentProof(
    std::uint64_t rawOption,std::uint32_t trustedKind,
    std::int32_t trustedStackLimit,
    const B0QuantityEvidence& proof) noexcept {
    if(trustedKind!=kRealB0MaterialKind ||
       trustedStackLimit!=static_cast<std::int32_t>(kRealB0TicketMaxStack))
        return {B0QuantityVerdict::UnexpectedMetadata,0};
    if(!proof.independentlyMatchedKnownQuantity ||
       !proof.sameGameBuildAndMaterialKindVerified ||
       !proof.optionLayoutVerified)
        return {B0QuantityVerdict::MissingIndependentEvidence,0};
    std::uint64_t mask=0;
    switch(proof.provenProfile) {
        case B0CountProfile::Unknown:
            return {B0QuantityVerdict::UnknownProfile,0};
        case B0CountProfile::OptionLow10:
            mask=0x3FFULL;break;
        case B0CountProfile::OptionLow16:
            mask=0xFFFFULL;break;
        case B0CountProfile::PlainPositiveOptionNoFlags:
            // Unknown bit-width is immaterial when entire raw option
            // consists solely of a positive count <=999: low10/low16
            // and whole-value interpretations must agree.
            mask=~std::uint64_t{0};break;
    }
    // If other bits of ItemOption exist, they may encode item flags
    // or high count bits. Refuse to tamper with them until independently
    // proven. The two real sampled ticket options have all other bits zero.
    if(!proof.extraOptionFlagsProvenAbsent || (rawOption&~mask)!=0)
        return {B0QuantityVerdict::UnverifiedOptionFlags,0};
    // Validate BEFORE narrowing to 32 bits. High option bits are never
    // permitted, including under PlainPositiveOptionNoFlags mode.
    const auto rawCount=rawOption&mask;
    if(rawCount<1 || rawCount>kRealB0TicketMaxStack)
        return {B0QuantityVerdict::InvalidCount,0};
    const auto count=static_cast<std::uint32_t>(rawCount);
    if(count<1 || count>kRealB0TicketMaxStack)
        return {B0QuantityVerdict::InvalidCount,0};
    return {B0QuantityVerdict::VerifiedCount,count};
}
} // namespace diamond_v291::inventory
