#!/bin/sh
set -eu
cd "$(dirname "$0")"
mkdir -p bin build
cp upstream/sparrow.c build/sparrow.c
patch -s -d build sparrow.c < platform/macos/sparrow.patch
# Match the Windows build's XOR heuristic, optimisation and GNU inline semantics.
"${CC:-cc}" -std=gnu99 -fgnu89-inline -O3 -funroll-loops -DXOR build/sparrow.c -lm -o bin/sparrow
