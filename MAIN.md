# J main line

J の正本・主系列は **AGI-GI rev系列** とする。

この系列は `automation_runs/2026-08-19_0851_JST/AGI_GI_REV_SERIES.md` に定義された、rev91 から継続する graph alignment / symmetry / graph isomorphism / permutation-group / canonical-labeling 系である。

現在の継続点は **rev142**。rev139 で既存世界解の包含監査を行い、一般 nonregular primitive/coherent obstruction を Babai 型 recurrence と独立 differential-oracle 問題へ再編。rev140 で candidate 実装に依存しない graph6 interchange と nauty `labelg` fail-closed adapter を追加。rev141 で executable differential suite を追加したが、rev142 の直接試行で、テストが未存在 API を参照していたことと Ubuntu の nauty 実行ファイルが `nauty-labelg` 名であることを確認した。rev142 では adapter を `labelg`/`nauty-labelg` 両対応に修正し、テストを実在 adapter API に接続、oracle 不在の skip 経路を除去し、complete bipartite / paired cliques / hypercube を含む高対称 adversarial families へ拡張した。AGI-GI CI は Ubuntu `nauty` を実インストールしてこの differential gate を実行する。

予測問題数は **512**。B1a を直接試行後、B1a.1〜B1a.4 に分解したため現在の有効問題数は **504** で予測超過なし。B1a.1（実行ファイル探索正規化）、B1a.2（実在 adapter API への修復）、B1a.4（adversarial family 拡張）は解決済み。次の未解決末端は **B1a.3: trigger 済みの実 nauty/labelg-backed CI run を観測し、具体的な pass/fail 証拠を永続化する**。passing run を実際に観測するまでは解決扱いにしない。

AGI 状態は **NOT_AGI** のまま。

以後、J の主進捗・CURRENT_STATUS・次の未解決末端はこの系列を基準に更新する。別系統の AGI 評価基盤・custodian/federation 系は、明示的に再指定されない限り J の main line として扱わない。
