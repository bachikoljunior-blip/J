#!/usr/bin/env python3
"""Claude Code のローカルトランスクリプト (~/.claude/projects/**/*.jsonl) を走査し、
モデル別の累計トークン使用量を JSON で出力する。

- ストリーミングで同一メッセージが複数行に書かれるため message.id で重複排除 (最後の行が最終値)
- input  = input_tokens (キャッシュを除く直接入力)
- output = output_tokens
- cache_write / cache_read はキャッシュ作成・読出 (参考値として別掲)
"""
import json
import glob

seen = {}
for path in glob.glob('/root/.claude/projects/**/*.jsonl', recursive=True):
    try:
        with open(path, encoding='utf-8', errors='replace') as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                m = d.get('message') or {}
                u = m.get('usage')
                model = m.get('model')
                if not u or not model or model == '<synthetic>':
                    continue
                mid = m.get('id') or (path + ':' + str(d.get('timestamp', '')))
                seen[mid] = (model, u)
    except OSError:
        continue

totals = {}
for model, u in seen.values():
    t = totals.setdefault(model, {'input': 0, 'output': 0, 'cache_write': 0, 'cache_read': 0})
    t['input'] += u.get('input_tokens') or 0
    t['output'] += u.get('output_tokens') or 0
    t['cache_write'] += u.get('cache_creation_input_tokens') or 0
    t['cache_read'] += u.get('cache_read_input_tokens') or 0

print(json.dumps(totals, ensure_ascii=False))
