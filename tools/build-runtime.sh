#!/bin/sh
# 最古のService Workerキャッシュともパスが衝突しない、公開用ランタイムを生成する。
set -eu
cd "$(dirname "$0")/.."

runtime=eldria-v5.js
: > "$runtime"
for file in js/core.js js/audio.js js/world.js js/systems.js js/entities.js js/ui.js js/main.js; do
  printf '\n/* ===== %s ===== */\n' "$file" >> "$runtime"
  sed -n '1,$p' "$file" >> "$runtime"
done
cp style.css style-v5.css
cp manifest.json manifest-v5.json
