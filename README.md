# J — 最短で動く自律型汎用エージェント研究基盤

Jは、目標を受け取り、状況を調べ、1回に1つの行動を実行し、結果を検証し、失敗時には別経路へ切り替える小型エージェントです。実行履歴は `state/memory.jsonl` に残り、検証済みの追加能力は `skills/` として組み込めます。

**現在の成果は、人間級AGIの達成ではありません。** 動作確認できるのは、計画、複数種類の問題解決、記憶、回帰テスト、能力ベンチマーク、停滞検知、安全な拡張点を備えた基盤です。達成判定は [AGI_CRITERIA.md](AGI_CRITERIA.md) に固定し、内部スコアだけでAGIを名乗らない設計です。

## 実行

鍵なしの最短経路:

```bash
python -m j_agent \
  --goal "未知課題への汎化能力を改善し、証拠で検証する" \
  --provider auto \
  --max-steps 8
```

`auto` はモデルが利用可能なら使い、認証・SDK・APIで問題が起きた場合は、テストとベンチマークを行うオフライン経路へ切り替えます。

OpenAIモデルを任意で有効化する場合:

```bash
pip install -e ".[openai]"
export OPENAI_API_KEY="..."
python -m j_agent --goal "目標" --provider openai
```

検証:

```bash
python -m unittest discover -v
python -m j_agent --benchmark
python -m j_agent --doctor
```

個別の内蔵能力:

```bash
python -m j_agent --solve-json '{"kind":"arithmetic","expression":"2+3*4"}'
python -m j_agent --solve-json '{"kind":"shortest_path","grid":["...",".#.","..."],"start":[0,0],"goal":[2,2]}'
```

## 実装済みの最小機構

- 算術、依存順序、最短経路、テキスト正規化、JSON変換、目標分解
- JSONL長期記憶と過去イベント検索
- `blocked` を記録し、別の目標・経路へ切り替える反復ループ
- 同じ行動の反復検知
- 固定受入テストとcriticalベンチマークによる証拠ベースの完了判定
- 静的検査を通った `skills/*.py` による能力追加
- 作業領域、書込先、サブプロセス、秘密情報に対する境界

## 書込可能領域

エージェント自身が書き込めるのは `skills/`, `tests/generated/`, `docs/`, `state/`, `reports/`, `workspace/` だけです。コア、GitHub Actions、固定テスト、評価基準は保護されています。詳細は [SECURITY.md](SECURITY.md) を参照してください。
