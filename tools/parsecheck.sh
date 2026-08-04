#!/bin/sh
# Parse every source and tool file. Catches the class of error that a browser
# audit only surfaces twelve minutes in, and a pure-node unit check never
# reaches because it imports three modules out of forty.
fail=0
for f in $(find src tools -name '*.mjs' -o -name '*.js' | sort); do
  node --check "$f" >/dev/null 2>&1 || { echo "PARSE FAIL: $f"; fail=1; }
done
[ $fail -eq 0 ] || exit $fail

# Parsing is not resolving. A helper declared in the wrong scope passes
# node --check, runs the entire twelve-minute audit, prints every measurement,
# and throws on the last line before the verdict — which is exactly what
# happened. AUDIT_DRY reaches the report path in about a second without a
# browser and without writing any report file.
AUDIT_DRY=1 node tools/audit.mjs >/dev/null 2>/tmp/auditdry.err || {
  echo "報告経路の検査に失敗:"
  head -5 /tmp/auditdry.err
  exit 1
}

echo "構文検査: src/ tools/ 全ファイル通過、報告経路も通過"
exit 0
