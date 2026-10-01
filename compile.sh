#!/usr/bin/env bash

# Compiler path, from:
# https://adafruit-circuit-python.s3.amazonaws.com/index.html?prefix=bin/mpy-cross/windows/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPILER="${SCRIPT_DIR}/mpy-cross-windows-10.2.1.static.exe"

# Optimization level from 0 to 3
# Note that level 3 strips line numbers
OPT_LEVEL="3"

echo "Using optimization level: -O$OPT_LEVEL"

shopt -s globstar nullglob

for path in **/_*.py; do
    [[ -f "$path" ]] || continue

    dir=$(dirname "$path")
    file=$(basename "$path")
    stripped_file="${file#_}"

    out_path="${dir}/${stripped_file%.*}.mpy"

    if [[ "$dir" == "." ]]; then
        traceback_source="$stripped_file"
    else
        traceback_source="${dir}/${stripped_file}"
    fi

    echo "Compiling: $path -> $out_path"

    "$COMPILER" -o "$out_path" -s "$traceback_source" -O"$OPT_LEVEL" "$path"
done

echo "Finished compiling"
