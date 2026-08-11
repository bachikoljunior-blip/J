#!/bin/sh
# 全ゲームスクリプトの構文検査。1つでも構文エラーがあれば非0で終了する。
set -eu
cd "$(dirname "$0")/.."
status=0
for f in js/core.js js/audio.js js/world.js js/systems.js js/entities.js js/ui.js js/main.js eldria-v4.js sw.js; do
  if node --check "$f"; then
    echo "OK   $f"
  else
    echo "FAIL $f"
    status=1
  fi
done
exit $status
