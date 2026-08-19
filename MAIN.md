# J main line

J の正本・主系列は **AGI-GI rev系列** とする。

この系列は `automation_runs/2026-08-19_0851_JST/AGI_GI_REV_SERIES.md` に定義された、rev91 から継続する graph alignment / symmetry / graph isomorphism / permutation-group / canonical-labeling 系である。

現在の継続点は **rev164**。rev140〜143 で独立 `labelg` differential oracle を実 CI まで検証して B1 を解決。rev144〜149 で canonical local-certificate partition を exact ambient transporter/coset、二-string partition coset、exact value-coset intersection、end-to-end relabeling-invariant な string-isomorphism coset まで接続。rev150 で fail-closed global quasipolynomial accounting verifier を導入した。rev151〜162 では quotient/kernel・affected/unaffected・growing-beard 実行と証拠の重複を横断整理し、最終的に R1/R2 の proof-carrying SI 方針へ再編した。

rev163 で R1 を直接試行し、**`ProofCarryingCoset` を実行の正本として導入**した。small/polylog child は full `S_m` を実列挙して exact intersection coset/emptiness を構成し、同じ実行から terminal accounting node を生成する。affected kernel-orbit executor v2 は各 active child のこの proof object を保持する。非-polylog child は旧 `right_coset_intersection_recursive(..., max_nodes=...)` へフォールバックせず、候補列挙 0 の typed unresolved object を返して fail closed する。PR #33 の workflow run 32262075028 / run #141 で新規 R1 tests、既存 recurrence tests、実 `labelg` differential gate がすべて success となり main へ統合済み。

R1 の直接試行後も non-polylog structural recursion は未解決で、通常の R1.a/R1.b 分解では 512→513 と予測数を超えるため rev164 で mandatory transversal rewrite を実施した。rev163 の proof object により、open な structural recursion と旧 R2 canonical/accounting closure は同じ executed child objects を必要とすることが明確になったため、R1/R2 を **T1 + S1** へ置換した。T1 は rev163 で解決済みの proof-carrying base operator。S1 は intransitive/imprimitive/primitive/giant-local-certificates/Split-Johnson の各 non-polylog path を自己再帰し、exact coset/emptiness、actual child proofs、canonical/equivariance、local/global accounting を一つの返り値として閉じる問題である。別の post-hoc proof tree の作成は禁止する。

予測問題数と現在の有効問題数は **512 / 512**。次の未解決末端は **S1: 最初の non-polylog transitive stop を structural S1 operator へ置換する**。まず canonical structural classifier を実装し、intransitive/imprimitive reduction、既存の exact special terminal、primitive/giant continuation を証明付きで区別し、どの分岐でも旧 node-capped child SI を呼ばない状態にする。

AGI 状態は **NOT_AGI** のまま。Babai 型 quasipolynomial complexity も S1 の自己再帰実行と一体化した証拠が end-to-end で閉じるまでは達成済みと扱わない。

以後、J の主進捗・CURRENT_STATUS・次の未解決末端はこの系列を基準に更新する。別系統の AGI 評価基盤・custodian/federation 系は、明示的に再指定されない限り J の main line として扱わない。
