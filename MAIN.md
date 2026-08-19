# J main line

J の正本・主系列は **AGI-GI rev系列** とする。

この系列は `automation_runs/2026-08-19_0851_JST/AGI_GI_REV_SERIES.md` に定義された、rev91 から継続する graph alignment / symmetry / graph isomorphism / permutation-group / canonical-labeling 系である。

現在の継続点は **rev153**。rev140〜143 で独立 `labelg` differential oracle を実 CI まで検証して B1 を解決。rev144〜149 では canonical local-certificate partition を exact ambient transporter/coset、二-string partition coset、exact value-coset intersection、end-to-end relabeling invariant な string-isomorphism coset まで接続し、B2.3 の correctness plumbing を閉じた。rev150 では global quasipolynomial recurrence accounting verifier を実装したが、既存 exact primitives が証明済み局所コストを出さないため B2.4 は未解決と判定した。

rev150 の通常分解では有効問題数が予測 512 を超えるため、rev151 で全有効問題を横断し、B2.4 と B3 の重複した complexity/correctness obligations を **K1: kernel-lifted logarithmic local certificates** と **K2: proof-carrying canonical recurrence closure** に置換した。再予測・実数はいずれも **512**。rev152 は paired-Schreier quotient preimage coset を実装し、巨大 quotient を列挙せず exact lift + exact kernel を返す経路を作った。

rev153 では `kernel_lifted_local_fullness_v1.py` により O(log n) test set の各 A(T) generator を rev152 の exact preimage coset へ lift し、string-preserving Young coset と exact intersection して genuine fullness witness / missing-generator nonfullness witness を得る。rev114 の affected-kernel orbit bound も機械監査され、旧 exact-global certificate との differential tests を含む validation gate に入っている。

ただし **K1 は未解決**。現在の `right_coset_intersection_recursive` は exact・resource-bounded だが、quasipolynomial asymptotic bound を証明する局所 cost certificate を持たない。次の末端は **K1 の affected-kernel intersection work を、未証明の flat local cost として数えるのではなく、strictly shrinking proof-carrying recurrence children として表現・実行すること**。これができるまで Babai 型 quasipolynomial complexity を達成済みとは扱わない。

AGI 状態は **NOT_AGI** のまま。

以後、J の主進捗・CURRENT_STATUS・次の未解決末端はこの系列を基準に更新する。別系統の AGI 評価基盤・custodian/federation 系は、明示的に再指定されない限り J の main line として扱わない。
