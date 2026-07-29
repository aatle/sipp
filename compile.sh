#!/usr/bin/env bash

# Compiler path, from:
# https://adafruit-circuit-python.s3.amazonaws.com/index.html?prefix=bin/mpy-cross/windows/
COMPILER="C:\Users\user\development\sipp\mpy-cross-windows-10.2.1.static.exe"

# Optimization level from 0 to 3
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
