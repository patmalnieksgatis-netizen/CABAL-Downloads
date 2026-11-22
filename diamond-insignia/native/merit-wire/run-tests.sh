#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build
g++ -std=c++17 -Wall -Wextra -Werror -Wpedantic -O2 -I. DiamondMeritWire.cpp test_merit_wire.cpp -o build/test_merit_wire
./build/test_merit_wire
g++ -std=c++17 -Wall -Wextra -Werror -Wpedantic -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -I. DiamondMeritWire.cpp test_merit_wire.cpp -o build/test_merit_wire_asan
ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 ./build/test_merit_wire_asan
