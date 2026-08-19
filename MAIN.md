# J main line

J の正本・主系列は **AGI-GI rev系列** とする。

この系列は `automation_runs/2026-08-19_0851_JST/AGI_GI_REV_SERIES.md` に定義された、rev91 から継続する graph alignment / symmetry / graph isomorphism / permutation-group / canonical-labeling 系である。

現在の継続点は **rev140**。rev136 で prime-degree regular cyclic action に対する relabeling-invariant affine canonical terminal を独立検証し、rev137–rev138 で master canonical reduction v5 へ統合した。rev138 の repository CI 完了結果は独立確認できていないため統合部分は未認定。rev139 で既存世界解の包含監査を行い、一般 nonregular primitive/coherent obstruction を Babai 型 recurrence と独立 differential-oracle 問題へ再編した。rev140 では B1 の直接試行として、candidate 実装に依存しない graph6 interchange と nauty `labelg` の fail-closed adapter、および決定的 interchange test を追加した。実際の labelg-backed differential run と repository CI はまだ独立確認前なので B1 は未解決のまま。

予測問題数は **512**、現在の有効問題数は **499** で予測超過なし。次の末端は **B1a: labelg-backed relabeling/adversarial differential run を実行し、mismatch/certificate を永続化する**。

AGI 状態は **NOT_AGI** のまま。

以後、J の主進捗・CURRENT_STATUS・次の未解決末端はこの系列を基準に更新する。別系統の AGI 評価基盤・custodian/federation 系は、明示的に再指定されない限り J の main line として扱わない。
