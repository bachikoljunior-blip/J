# J main line

J の正本・主系列は **AGI-GI rev系列** とする。

この系列は `automation_runs/2026-08-19_0851_JST/AGI_GI_REV_SERIES.md` に定義された、rev91 から継続する graph alignment / symmetry / graph isomorphism / permutation-group / canonical-labeling 系である。

現在の継続点は **rev162**。rev140〜143 で独立 `labelg` differential oracle を実 CI まで検証して B1 を解決。rev144〜149 で canonical local-certificate partition を exact ambient transporter/coset、二-string partition coset、exact value-coset intersection、end-to-end relabeling-invariant な string-isomorphism coset まで接続。rev150 で fail-closed global quasipolynomial accounting verifier を導入した。

rev151〜155 は quotient/kernel recurrence と canonical closure の証拠重複を横断整理し、Q1/Q2 を正本とした。rev156〜160 では invariant-orbit coset lifting、orbit-factored exact String-Isomorphism、affected child bound、exact Unaffected Stabilizer subgroup、Babai local-certificate parameter window、および theorem-scale evidence conjunction を機械化した。

rev161 では Q1 を直接進め、**affected-only string-segment SI、quotient point-image recursion → singleton quotient image → paired-Schreier kernel lift → affected kernel-orbit child SI、exact right-coset reassembly、growing-beard local certificate** を実装した。最初の quotient recursion は RightCoset の向きを誤り CI が branch-union cardinality mismatch を検出したが、各 child point stabilizer を transversal で共役する正しい分解へ修正。PR #31 の workflow run 32257287994 / run #126 で新規・既存・`labelg` の全 gate が success となり main へ統合済み。これにより、unaffected orbit を opaque SI へ送らず growing beard と Unaffected Stabilizer を exact に合成する correctness 境界は閉じた。

ただし Q1 はなお未解決だった。実際の affected kernel-orbit child が非-polylogarithmic な場合、rev161 は resource-bounded exact SI terminal を使い、その node cap は quasipolynomial cost certificate ではない。Q1 を通常どおり三つの子問題へ分解すると有効問題数が 512→515 となるため、rev162 で mandatory transversal rewrite を実施した。rev144〜149 correctness plumbing、rev150 accounting、rev157〜161 execution、Q1 child dispatch、Q2 closure が同じ exact coset / actual children / canonicality / progress / local cost を別々に再構築している点を横断し、**R1: self-recursive proof-carrying SI engine** と **R2: canonical proof closure over R1 objects** へ置換した。

予測問題数と現在の有効問題数は再び **512 / 512**。次の未解決末端は **R1**。一つの typed proof-carrying coset/emptiness object を実行の正本とし、各 non-polylog child は R1 自身へ再帰 dispatch、polylog/small child だけは closed-form の mechanically charged terminal とする。実行した child proof object そのものが recurrence/cost trace になり、後から別の complexity tree を捏造できない構造へする。R2 は同じ object を canonical aggregation と rev150 verifier に直接渡し、exact sets・relabeling equivariance・外部 canonical oracle・local/global cost を独立差分検証する。

AGI 状態は **NOT_AGI** のまま。Babai 型 quasipolynomial complexity も R1/R2 の実行・検証が閉じるまでは達成済みと扱わない。

以後、J の主進捗・CURRENT_STATUS・次の未解決末端はこの系列を基準に更新する。別系統の AGI 評価基盤・custodian/federation 系は、明示的に再指定されない限り J の main line として扱わない。
