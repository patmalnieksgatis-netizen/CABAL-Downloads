#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build
CXXFLAGS=(-std=c++17 -Wall -Wextra -Wpedantic -Werror -O2 -I.)
g++ "${CXXFLAGS[@]}" DiamondWorldSaveBarrier.cpp test_world_save.cpp -o build/test_world_save
./build/test_world_save
g++ -std=c++17 -Wall -Wextra -Wpedantic -Werror -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -I. DiamondWorldSaveBarrier.cpp test_world_save.cpp -o build/test_world_save_asan
ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 ./build/test_world_save_asan
