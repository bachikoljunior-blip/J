#!/bin/sh
# Parse every source and tool file. Catches the class of error that a browser
# audit only surfaces twelve minutes in, and a pure-node unit check never
# reaches because it imports three modules out of forty.
fail=0
for f in $(find src tools -name '*.mjs' -o -name '*.js' | sort); do
  node --check "$f" >/dev/null 2>&1 || { echo "PARSE FAIL: $f"; fail=1; }
done
[ $fail -eq 0 ] && echo "構文検査: src/ tools/ 全ファイル通過"
exit $fail
