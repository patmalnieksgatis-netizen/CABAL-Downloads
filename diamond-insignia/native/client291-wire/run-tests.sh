#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build
g++ -std=c++17 -O2 -Wall -Wextra -Werror -Wpedantic -Isrc src/Client291MeritWire.cpp tests/test_client291_wire.cpp -o build/test
./build/test
g++ -std=c++17 -O1 -g -Wall -Wextra -Werror -Wpedantic -fsanitize=address,undefined -fno-omit-frame-pointer -Isrc src/Client291MeritWire.cpp tests/test_client291_wire.cpp -o build/test_asan
ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 ./build/test_asan
# Additional fail-closed boundary regressions: malformed/truncated C2S and S2C.
g++ -std=c++17 -O2 -Wall -Wextra -Werror -Wpedantic -Isrc src/Client291MeritWire.cpp tests/test_client291_wire_boundaries.cpp -o build/test_boundaries
./build/test_boundaries
g++ -std=c++17 -O1 -g -Wall -Wextra -Werror -Wpedantic -fsanitize=address,undefined -fno-omit-frame-pointer -Isrc src/Client291MeritWire.cpp tests/test_client291_wire_boundaries.cpp -o build/test_boundaries_asan
ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 ./build/test_boundaries_asan

# Branch-sensitive S2C check: all three actual v291 map lookups.
# Never promote a 7-byte success to a verified Diamond purchase.
g++ -std=c++17 -O2 -Wall -Wextra -Werror -Wpedantic -Isrc \
  src/Client291MeritWire.cpp tests/test_client291_s2c_branches.cpp \
  -o build/test_s2c_branches
./build/test_s2c_branches
g++ -std=c++17 -O1 -g -Wall -Wextra -Werror -Wpedantic \
  -fsanitize=address,undefined -fno-omit-frame-pointer -Isrc \
  src/Client291MeritWire.cpp tests/test_client291_s2c_branches.cpp \
  -o build/test_s2c_branches_asan
ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 ./build/test_s2c_branches_asan
