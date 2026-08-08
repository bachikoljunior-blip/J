#!/bin/bash
# 1時間ごとのトークン使用量を token_usage.md に追記してプッシュする。
# DRYRUN=1 で git 操作をスキップ (動作確認用)。
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

NOW="$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M JST')"
python3 aggregate.py > /tmp/token_cum.json
python3 append.py /tmp/token_cum.json "$NOW"

if [ "$DRYRUN" = "1" ]; then
  echo "dry-run: skip git"
  exit 0
fi

git add token_usage.md state.json
git commit -q -m "token usage @ $NOW" || { echo "no change"; exit 0; }
for i in 1 2 3 4; do
  git push -q origin token-usage-log && exit 0
  sleep $((2 ** i))
done
echo "push failed" >&2
exit 1
