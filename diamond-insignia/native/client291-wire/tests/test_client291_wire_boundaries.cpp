#include "Client291MeritWire.h"
#include <array>
#include <cassert>
#include <cstdint>
#include <iostream>

using namespace diamond_v291::wire;

int main() {
    const auto valid = BuildOfflineClientRequest(159u, 0x11223344u);
    RequestFields fields{};
    // A truncated buffer must never be interpreted as a complete C2S request.
    for (std::size_t size = 0; size < valid.size(); ++size) {
        fields = {99u, 99u, 99u};
        assert(ReadClientRequest(valid.data(), size, fields) == Status::Short);
        assert(fields.transportField == 0 && fields.state118 == 0 &&
               fields.state11C == 0);
    }
    assert(ReadClientRequest(valid.data(), valid.size(), fields) == Status::Ok);
    // Merit IDs cannot by themselves prove the Diamond action or payload meaning.
    assert(fields.state118 == 159u && fields.state11C == 0x11223344u);

    auto broken = valid;
    broken[0] ^= 1;
    assert(ReadClientRequest(broken.data(), broken.size(), fields) ==
           Status::MagicMismatch);
    broken = valid;
    broken[2] ^= 1;
    assert(ReadClientRequest(broken.data(), broken.size(), fields) ==
           Status::LengthMismatch);
    broken = valid;
    broken[8] ^= 1;
    assert(ReadClientRequest(broken.data(), broken.size(), fields) ==
           Status::OpcodeMismatch);
    // No untrusted request data survives failed parsing.
    assert(fields.transportField == 0 && fields.state118 == 0 &&
           fields.state11C == 0);

    const std::array<std::uint8_t, 7> legacySuccess{
        0xe2, 0xb7, 7, 0, 0xf3, 9, 1
    };
    const std::array<std::uint8_t, 7> legacyFailure{
        0xe2, 0xb7, 7, 0, 0xf3, 9, 0
    };
    assert(CheckServerResponseForClient291(legacySuccess.data(), 7) ==
           Status::ResponseTruncatedSuccess);
    assert(CheckServerResponseForClient291(legacyFailure.data(), 7) ==
           Status::ResponseRejected);
    for (std::size_t size = 0; size < 7; ++size) {
        assert(CheckServerResponseForClient291(legacySuccess.data(), size) ==
               Status::Short);
    }

    // Even with the four extra bytes, semantics are unknown: not an approval.
    std::array<std::uint8_t, 11> candidate{
        0xe2, 0xb7, 11, 0, 0xf3, 9, 1, 0x78, 0x56, 0x34, 0x12
    };
    assert(CheckServerResponseForClient291(candidate.data(), candidate.size()) ==
           Status::ResponseSuccessShapeUnknown);
    candidate[6] = 0;
    assert(CheckServerResponseForClient291(candidate.data(), candidate.size()) ==
           Status::ResponseRejected);
    candidate[6] = 1;
    candidate[4] ^= 1;
    assert(CheckServerResponseForClient291(candidate.data(), candidate.size()) ==
           Status::OpcodeMismatch);
    candidate[4] ^= 1;
    candidate[2] = 7;
    assert(CheckServerResponseForClient291(candidate.data(), candidate.size()) ==
           Status::LengthMismatch);
    candidate[2] = 11;
    candidate[0] ^= 1;
    assert(CheckServerResponseForClient291(candidate.data(), candidate.size()) ==
           Status::MagicMismatch);
    assert(CheckServerResponseForClient291(nullptr, 11) == Status::Null);

    std::cout << "CLIENT291_WIRE_BOUNDARIES=PASS\n"
              << "LEGACY_7B_SUCCESS=NEVER_APPROVED\n"
              << "UNKNOWN_11B_SUCCESS=NEVER_APPROVED\n"
              << "NO_DIAMOND_OPCODE_OR_GAMEPLAY_CLAIM=YES\n";
}
