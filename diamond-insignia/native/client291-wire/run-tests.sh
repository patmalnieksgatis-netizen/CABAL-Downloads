#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build
g++ -std=c++17 -O2 -Wall -Wextra -Werror -Wpedantic -Isrc src/Client291MeritWire.cpp tests/test_client291_wire.cpp -o build/test
./build/test
g++ -std=c++17 -O1 -g -Wall -Wextra -Werror -Wpedantic -fsanitize=address,undefined -fno-omit-frame-pointer -Isrc src/Client291MeritWire.cpp tests/test_client291_wire.cpp -o build/test_asan
ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 ./build/test_asan
