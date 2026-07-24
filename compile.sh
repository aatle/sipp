compiler="C:\Users\user\development\sipp\mpy-cross-windows-10.2.1.static.exe"

for file in _*.py; do
    # Verify it is actually a file, not a directory
    [[ -f "$file" ]] || continue
    echo "Compiling: $file"
    stripped_name=${file:1}
    $compiler -o ${stripped_name%.*}.mpy -s $stripped_name -O3 $file
done
echo "Finished compiling"
