# J main line

J の正本・主系列は **AGI-GI rev系列** とする。

この系列は `automation_runs/2026-08-19_0851_JST/AGI_GI_REV_SERIES.md` に定義された、rev91 から継続する graph alignment / symmetry / graph isomorphism / permutation-group / canonical-labeling 系である。

現在の継続点は **rev155**。rev140〜143 で独立 `labelg` differential oracle を実 CI まで検証して B1 を解決。rev144〜149 では canonical local-certificate partition を exact ambient transporter/coset、二-string partition coset、exact value-coset intersection、end-to-end relabeling invariant な string-isomorphism coset まで接続し、B2.3 の correctness plumbing を閉じた。rev150 の global quasipolynomial accounting verifier は有効だが、既存 exact primitives に証明済み局所コストが無いため B2.4 は未解決と判定した。

rev151 では予測数 512 超過を回避する横断書き換えにより B2.4/B3 を K1/K2 に統合。rev152 は paired-Schreier quotient preimage coset、rev153 は O(log n) test set 上の kernel-lifted local fullness/nonfullness、rev154 は affected kernel を exact kernel-orbit children へ分けて rev114 の orbit bound を strict child-domain shrink として機械化した。ただし generic coset intersection はまだその子問題を実行単位にしておらず、K1 の complexity execution は未認定だった。

rev154 の K1 通常分解は一時的に有効問題数を 514 にし予測 512 を超えるため、rev155 で置換済みを除く問題を再横断した。K1 の exact orbit-factorization/cost trace と K2 の exact-coset/accounting closure は同じ証拠を二重に要求していたため、両者を **Q1: orbit-factored proof-carrying SI kernel** と **Q2: canonical proof closure** に置換した。再予測・現在実数はいずれも **512**。

次の未解決末端は **Q1**。各 affected-kernel/value-preserving coset intersection を certified smaller kernel-orbit children として実際に実行し、その exact coset composition と同一の recurrence/cost trace を出力する。既存の generic exact intersection は tractable instance の differential oracle としてのみ再利用し、opaque な node cap を complexity 証拠にはしない。Q2 は Q1 の trace を canonical aggregation / Split-or-Johnson / B2.3 coset recursion と rev150 verifier に直接通し、独立差分検証まで閉じる。

AGI 状態は **NOT_AGI** のまま。Babai 型 quasipolynomial complexity も Q1/Q2 が実行・検証されるまでは達成済みと扱わない。

以後、J の主進捗・CURRENT_STATUS・次の未解決末端はこの系列を基準に更新する。別系統の AGI 評価基盤・custodian/federation 系は、明示的に再指定されない限り J の main line として扱わない。
