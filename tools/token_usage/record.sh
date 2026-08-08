#!/bin/bash
# このセッションの1時間ごとのトークン使用量をリポジトリ直下の token_usage.md に
# 追記してプッシュする。23:00 JST の初回実行は基準スナップショットのみ保存し、
# 以降は毎時「直前の1時間分」の差分を追記する。DRYRUN=1 で git 操作をスキップ。
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"
cd "$ROOT"

NOW="$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M JST')"
python3 "$DIR/aggregate.py" > /tmp/token_cum.json
python3 "$DIR/append.py" /tmp/token_cum.json "$NOW"

if [ "$DRYRUN" = "1" ]; then
  echo "dry-run: skip git"
  exit 0
fi

git add token_usage.md "$DIR/state.json"
git commit -q -m "トークン使用量の記録 @ $NOW" || { echo "no change"; exit 0; }
for i in 1 2 3 4; do
  git push -q origin claude/mobile-open-world-action-rpg-8uw40p && { echo pushed; exit 0; }
  sleep $((2 ** i))
done
echo "push failed" >&2
exit 1
