#!/usr/bin/env python3
"""累計スナップショット (aggregate.py の出力) と前回 state.json の差分を
リポジトリ直下の token_usage.md に追記する。前回 state が無ければ基準のみ保存。

usage: append.py <cumulative.json path> <now label e.g. "2026-08-08 23:00 JST">
"""
import json
import os
import sys

CUM_PATH = sys.argv[1]
NOW = sys.argv[2]
DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(DIR, '..', '..'))
STATE = os.path.join(DIR, 'state.json')
LOG = os.path.join(ROOT, 'token_usage.md')

with open(CUM_PATH) as f:
    cum = json.load(f)

prev = None
if os.path.exists(STATE):
    with open(STATE) as f:
        prev = json.load(f)

if prev is not None:
    # 前回スナップショットからの1時間分の差分を追記
    window = f"{prev.get('_time', '?')} 〜 {NOW}"
    lines = [f"\n## {window}\n"]
    lines.append('| モデル | 入力 | 出力 | Cache書込 | Cache読出 |')
    lines.append('|---|---:|---:|---:|---:|')
    models = sorted(set(list(cum.keys()) + [k for k in prev.keys() if not k.startswith('_')]))
    any_use = False
    for m in models:
        c = cum.get(m, {})
        p = prev.get(m, {})
        d = {k: (c.get(k, 0) or 0) - (p.get(k, 0) or 0)
             for k in ('input', 'output', 'cache_write', 'cache_read')}
        if all(v == 0 for v in d.values()):
            continue
        any_use = True
        lines.append(f"| {m} | {d['input']:,} | {d['output']:,} | {d['cache_write']:,} | {d['cache_read']:,} |")
    if not any_use:
        lines.append('| (この1時間の使用なし) | 0 | 0 | 0 | 0 |')
    if not os.path.exists(LOG):
        with open(LOG, 'w') as f:
            f.write('# トークン使用量ログ (このセッションのモデル別 / 1時間ごと)\n')
    with open(LOG, 'a') as f:
        f.write('\n'.join(lines) + '\n')

state = dict(cum)
state['_time'] = NOW
with open(STATE, 'w') as f:
    json.dump(state, f, ensure_ascii=False, indent=1)

print('recorded' if prev is not None else 'baseline saved (first record next hour)')
