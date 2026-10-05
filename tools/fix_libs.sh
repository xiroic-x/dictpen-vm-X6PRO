#!/bin/sh
n=0
for d in /userdisk/miniapp/data/mini_app/pkg/*/; do
    id=$(basename $d)
    if [ ! -d "$d/a/libs" ]; then mkdir -p "$d/a/libs" && n=$((n+1)); fi
done
echo "created_libs=$n"