# J main line

J の正本・主系列は **AGI-GI rev系列** とする。

この系列は `automation_runs/2026-08-19_0851_JST/AGI_GI_REV_SERIES.md` に定義された、rev91 から継続する graph alignment / symmetry / graph isomorphism / permutation-group / canonical-labeling 系である。

現在の継続点は **rev176**。rev140〜143 で独立 `labelg` differential oracle を実 CI まで検証して B1 を解決。rev144〜162 で canonical local-certificate partition、exact transporter/coset、quotient/kernel、affected/unaffected、growing-beard、fail-closed quasipolynomial accounting を proof-carrying SI substrate へ統合した。rev163〜168 では small/polylog terminal・intransitive recursion・imprimitive quotient/kernel の重複を横断整理し、予測問題数 512 を超えない形で **V1 [resolved substrate] + V2 [remaining transitive closure]** へ再編した。

rev169〜172 では quotient degree ではなく Schreier-certified image/order を基準に exact generator-BFS terminal と candidate-fiber recursionを追加し、unique-canonical-imprimitive large-order transitive candidate を exact に閉じた。rev173 は certified J(8,2) primitive non-giant actionを8点の Johnson ground 上の完全列挙へ落として exact SI coset を再構成。rev174 は small-ground terminal を一般 J(v,k) に拡張し、v=2k の complement automorphism coset も候補集合として正確に扱うようにした。

rev175 では large-ground Johnson leaf を直接試行し、J(v,k) domain から strictly smaller な ground relation へ進む exact interface を追加した。既存 canonical Johnson recognizer が座標を認証した場合、source/target を standard k-subsets に輸送し、ambient generator を ground permutation + v=2k complement bit へ decode、再誘導して元 generator と一致することまで fail-closed に検証する。最初の J(6,3) complement-expanded end-to-end test は orbital-size coarsening が equal-size orbitals を併合して Johnson color を失う実限界を露呈したため成功扱いしなかった。

rev176 ではその失敗を直接処理した。bounded degree では unordered-pair の exact ambient orbit family を列挙し、各 orbit relation を exact Johnson recognizer に掛け、採用した座標系について全 ambient generator の signed-ground decode / exact re-induction を再検証する fallback を追加した。これにより complement-expanded J(6,3) を safe orbital-size coarsening に依存せず認証できる。また、faithfully represented signed-ground group の Schreier-certified order が明示 cap 内なら、その signed group だけを完全列挙して colored k-subset relation を検査し、元 J(v,k) domain 上の exact SI right coset を再構成・第二走査監査する proof-carrying terminal を追加した。large-ground J(9,2) の PGL(2,8) action（Johnson domain 36、represented group order 504）を含む regression は PR #47 系の workflow run 32276514515 で既存 recurrence/master/real `nauty-labelg` gate とともに success となり、検証済み rev176 部分を PR #48 から main へ統合した。

V2 primitive-non-giant を JG1〜JG3 として単純追加すると有効問題数が 512→515 になり予測超過するため、rev175 で **W1 signed-ground relational SI closure** へ横断書換え済み。rev176 の修正・terminal は W1 内の横断解であり新しい active branch を追加しない。予測問題数 / 現在の有効問題数は **512 / 512** で予測超過なし。次の未解決末端は引き続き **W1: signed-ground group が列挙 cap を超える場合に、actual colored k-subset relation から canonical significant split または local-certificate recurrence を得て、complement bit・quasipolynomial cost certificate・exact original-domain coset reconstruction を同時に維持する**。

AGI 状態は **NOT_AGI** のまま。AGI 達成、一般性、性能、自律性、実用提供、または full Babai-style quasipolynomial closure は未認定であり、未確認の成果を達成済みとは扱わない。

以後、J の主進捗・CURRENT_STATUS・次の未解決末端はこの系列を基準に更新する。別系統の AGI 評価基盤・custodian/federation 系は、明示的に再指定されない限り J の main line として扱わない。
