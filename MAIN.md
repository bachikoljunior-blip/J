# J main line

J の正本・主系列は **AGI-GI rev系列** とする。

この系列は `automation_runs/2026-08-19_0851_JST/AGI_GI_REV_SERIES.md` に定義された、rev91 から継続する graph alignment / symmetry / graph isomorphism / permutation-group / canonical-labeling 系である。

現在の継続点は **rev172**。rev140〜143 で独立 `labelg` differential oracle を実 CI まで検証して B1 を解決。rev144〜162 で canonical local-certificate partition、exact transporter/coset、quotient/kernel、affected/unaffected、growing-beard、fail-closed quasipolynomial accounting を proof-carrying SI substrate へ統合した。rev163〜168 では small/polylog terminal・intransitive recursion・imprimitive quotient/kernel の重複を横断整理し、予測問題数 512 を超えない形で **V1 [resolved substrate] + V2 [remaining transitive closure]** へ再編した。

rev169 は quotient degree ではなく Schreier-certified quotient image order を基準に exact generator-BFS enumeration を行い、large-degree/small-image imprimitive cases を閉じた。rev170 は degree-independent な proof-carrying small-order group SI terminal を追加。rev171 は同じ certified-order terminal を candidate right-coset H*r と kernel-orbit image に再帰適用し、large kernel / small orbit-image fibers を閉じた。

rev172 では rev171 の残る large-order transitive candidate leaf を直接試行した。candidate subgroup H が一意な canonical nontrivial block system を持つ場合、`H*r` 上の SI を `H` 上の `source∘r^{-1}` 対 `target` SI へ正確に座標変換し、既存 V2 の certified small quotient-image / kernel-orbit recursion へ接続、exact subgroup coset/emptiness を元の `H*r` へ right-translate して戻す。これにより **unique-canonical-imprimitive large-order transitive candidate** は exact に閉じた。PR #40 の workflow run 32267660987 / run #212 で、rev172 regression を含む Babai recurrence tests、既存 master integration、実 `nauty-labelg` differential gate がすべて success となり main へ統合済み。

予測問題数と現在の有効問題数は **512 / 512** で予測超過なし。V2 は canonical block-system family と genuinely primitive large-order casesについて未解決。次の未解決末端は **V2 primitive non-giant: proof-carrying canonical Split-or-Johnson / special-terminal reductionを実行し、strict progress・canonical/equivariant construction・local/global costを機械検証可能にして candidate coset へ exact に戻す**。その後 primitive giant は theorem-gated local certificates / growing-beard 経路で処理する。

AGI 状態は **NOT_AGI** のまま。AGI 達成、一般性、性能、自律性、実用提供、または full Babai-style quasipolynomial closure は未認定であり、未確認の成果を達成済みとは扱わない。

以後、J の主進捗・CURRENT_STATUS・次の未解決末端はこの系列を基準に更新する。別系統の AGI 評価基盤・custodian/federation 系は、明示的に再指定されない限り J の main line として扱わない。
