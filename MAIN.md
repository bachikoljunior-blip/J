# J main line

J の正本・主系列は **AGI-GI rev系列** とする。

この系列は `automation_runs/2026-08-19_0851_JST/AGI_GI_REV_SERIES.md` に定義された、rev91 から継続する graph alignment / symmetry / graph isomorphism / permutation-group / canonical-labeling 系である。

現在の継続点は **rev166**。rev140〜143 で独立 `labelg` differential oracle を実 CI まで検証して B1 を解決。rev144〜149 で canonical local-certificate partition を exact ambient transporter/coset、二-string partition coset、exact value-coset intersection、end-to-end relabeling-invariant な string-isomorphism coset まで接続。rev150 で fail-closed global quasipolynomial accounting verifier を導入した。rev151〜162 では quotient/kernel・affected/unaffected・growing-beard 実行と証拠の重複を横断整理し、proof-carrying SI 方針へ再編した。

rev163 では `ProofCarryingCoset` を実行の正本として導入。small/polylog child は full `S_m` 実列挙による exact terminal と同じ実行由来 accounting を返し、非-polylog child は旧 node-capped exact SI へフォールバックせず typed unresolved で停止する。rev165 ではその次の S1 を直接進め、canonical structural classifier により small / intransitive / imprimitive / primitive non-giant / primitive giant を区別し、**intransitive two-string SI を実際に自己再帰**させた。各 invariant-orbit child は同じ proof object を返し、paired-Schreier preimage で exact lift・合成される。rev150 verifier には fixed-primary・strictly-smaller・disjoint-domain-sum を検査する `orbit_partition` 規則を追加した。PR #34 は最初の fixture 不備を CI が検出したため、global multiplicity は一致しつつ orbit-local multiplicity が不一致になる反例へ修正し、workflow run 32263105570 / run #153 で新規/既存 recurrence tests と実 `labelg` gate をすべて success にして main へ統合した。

S1 を通常分解すると有効問題数が 512→513 となるため rev166 で mandatory transversal rewrite を実施。resolved base + intransitive + classifier は一つの再利用 substrate なので **U1 [resolved]** に統合し、未解決リスクを **U2 [open]: transitive self-certifying SI closure** に集中した。U2 は canonical imprimitive quotient/kernel、primitive non-giant/Split-Johnson-special-terminal、theorem-gated giant local-certificates/growing-beard をすべて U1 proof objects だけで再帰し、exact coset/emptiness・actual children・canonical/equivariance・local/global cost を同じ返り値として閉じる。

予測問題数と現在の有効問題数は **512 / 512**。次の未解決末端は **U2: canonical block system の small/polylog quotient について、certified quotient image のみを列挙し、各 quotient fiber を exact lift、より小さい kernel-orbit children を U1 で再帰、成功 fiber を exact coset へ再構成する imprimitive operator**。large quotient または unresolved child は旧 exact node-cap へ逃げず fail closed とする。

AGI 状態は **NOT_AGI** のまま。Babai 型 quasipolynomial complexity も U2 の transitive closure が end-to-end に実行・検証されるまでは達成済みと扱わない。

以後、J の主進捗・CURRENT_STATUS・次の未解決末端はこの系列を基準に更新する。別系統の AGI 評価基盤・custodian/federation 系は、明示的に再指定されない限り J の main line として扱わない。
