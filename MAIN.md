# J main line

J の正本・主系列は **AGI-GI rev系列** とする。

この系列は `automation_runs/2026-08-19_0851_JST/AGI_GI_REV_SERIES.md` に定義された、rev91 から継続する graph alignment / symmetry / graph isomorphism / permutation-group / canonical-labeling 系である。

現在の継続点は **rev175**。rev140〜143 で独立 `labelg` differential oracle を実 CI まで検証して B1 を解決。rev144〜162 で canonical local-certificate partition、exact transporter/coset、quotient/kernel、affected/unaffected、growing-beard、fail-closed quasipolynomial accounting を proof-carrying SI substrate へ統合した。rev163〜168 では small/polylog terminal・intransitive recursion・imprimitive quotient/kernel の重複を横断整理し、予測問題数 512 を超えない形で **V1 [resolved substrate] + V2 [remaining transitive closure]** へ再編した。

rev169〜172 では quotient degree ではなく Schreier-certified image/order を基準に exact generator-BFS terminal と candidate-fiber recursionを追加し、unique-canonical-imprimitive large-order transitive candidate を exact に閉じた。

rev173 は certified J(8,2) primitive non-giant actionを8点の Johnson ground 上の完全列挙へ落として exact SI coset を再構成。rev174 は small-ground terminal を一般 J(v,k) に拡張し、v=2k の complement automorphism coset も候補集合として正確に扱うようにした。

rev175 では large-ground Johnson leaf を直接試行した。small-ground 列挙はそのまま拡張できないため、J(v,k) domain から strictly smaller な ground relation へ進む exact interface を追加した。既存 canonical Johnson recognizer が座標を認証した場合、source/target を standard k-subsets に輸送し、ambient generator を ground permutation + v=2k complement bit へ decode、再誘導して元 generator と一致することまで fail-closed に検証する。J(9,2) の large-ground lift と complement-bit decoder を CI で検証済み。最初の J(6,3) complement-expanded end-to-end test は orbital-size coarsening が Johnson color を失う実限界を露呈したため成功扱いせず、その境界を明示して修正した。PR #45 の workflow run 32274080877 / run #244 で、rev175 regression、既存 Babai recurrence tests、master integration、実 `nauty-labelg` differential gate がすべて success となり main へ統合済み。

V2 primitive-non-giant を JG1〜JG3 として単純追加すると有効問題数が 512→515 になり予測超過するため横断書換えを実施し、同じ relational/coset machinery を later giant local-certificate outputs にも再利用する **W1 signed-ground relational SI closure** へ置換した。予測問題数 / 現在の有効問題数は **512 / 512** で予測超過なし。次の未解決末端は **W1: colored k-subset relation を strictly smaller な signed Johnson ground 上で proof-carrying に再帰処理し、robust Johnson certification・Split-or-Johnson/local-certificate compatible progress・exact coset reconstruction を統合する**。補集合を含む ambient で safe orbital coarsening が Johnson structure を失う場合は fail-closed のまま扱う。

AGI 状態は **NOT_AGI** のまま。AGI 達成、一般性、性能、自律性、実用提供、または full Babai-style quasipolynomial closure は未認定であり、未確認の成果を達成済みとは扱わない。

以後、J の主進捗・CURRENT_STATUS・次の未解決末端はこの系列を基準に更新する。別系統の AGI 評価基盤・custodian/federation 系は、明示的に再指定されない限り J の main line として扱わない。
