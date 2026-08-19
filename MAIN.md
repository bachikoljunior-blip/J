# J main line

J の正本・主系列は **AGI-GI rev系列** とする。

この系列は `automation_runs/2026-08-19_0851_JST/AGI_GI_REV_SERIES.md` に定義された、rev91 から継続する graph alignment / symmetry / graph isomorphism / permutation-group / canonical-labeling 系である。

現在の継続点は **rev141**。rev139 で既存世界解の包含監査を行い、一般 nonregular primitive/coherent obstruction を Babai 型 recurrence と独立 differential-oracle 問題へ再編。rev140 で candidate 実装に依存しない graph6 interchange と nauty `labelg` fail-closed adapter を追加した。rev141 では B1a の executable differential suite を追加し、empty/complete/cycle/random graph families の各グラフについて8個の任意 relabelingを外部 labelg canonical form と比較する。labelg が存在しない場合の skip は成功扱いしない。

予測問題数は **512**、現在の有効問題数は **500** で予測超過なし。次の末端は **B1a: 実際の labelg-backed rev141 run を観測・永続化し、adversarial benchmark families まで拡張する**。

AGI 状態は **NOT_AGI** のまま。

以後、J の主進捗・CURRENT_STATUS・次の未解決末端はこの系列を基準に更新する。別系統の AGI 評価基盤・custodian/federation 系は、明示的に再指定されない限り J の main line として扱わない。
