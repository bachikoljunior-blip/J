# J main line

J の正本・主系列は **AGI-GI rev系列** とする。

この系列は `automation_runs/2026-08-19_0851_JST/AGI_GI_REV_SERIES.md` に定義された、rev91 から継続する graph alignment / symmetry / graph isomorphism / permutation-group / canonical-labeling 系である。

現在の継続点は **rev179**。rev140〜143 で独立 `labelg` differential oracle を実 CI まで検証して B1 を解決。rev144〜162 で canonical local-certificate partition、exact transporter/coset、quotient/kernel、affected/unaffected、growing-beard、fail-closed quasipolynomial accounting を proof-carrying SI substrate へ統合した。rev163〜168 では重複する terminal / recursion を横断整理して **V1 [resolved substrate] + V2 [remaining transitive closure]** へ再編した。rev169〜177 で Schreier-certified image/order terminal、candidate-fiber recursion、imprimitive closure、Johnson small-ground / relational lift / signed-ground terminals、point-profile partition orbit を順次追加した。

rev178 は W1R の first-order point-profile exhaustionを直接処理し、actual colored k-subset relation から complement-safe unordered-ground-pair relationを構成した。intersection size 0/1/2 ごとの color histogram を pair signature とし、v=2k complement が signed image にある場合は 0/2 histogram を unordered に保持する。この relation の coherent refinementから significant ground split を得た場合は original-domain generator word を保持した exact signed partition-transporter candidate cosetを復元する。K3 ⊔ C5 on J(8,2) では全点の first-order profile が一様でも 3/5 split を復元した。C9 on J(9,2) の homogeneous relation は strictly smaller 9-point recurrence targetになり、さらに represented S9 order 362880 自体ではなく 20160 個の distinct pair-relation imagesだけを Schreier探索することで、k=2 の exact SI coset（stabilizer order 18）を再構成した。state cap 超過は fail closed。PR #51 / workflow run 32282814320 で fast 5 tests、integrated 116 tests、real `nauty-labelg` 2 tests が success。

rev179 は **W1R-H の image-to-original exact composition** を直接試行した。J に既存だった block-action 専用 paired Schreier lift を action-agnostic な `paired_action_coset_preimage_v1` へ一般化した。domain generator と対応する image generator から image Schreier chain と full kernel を同時に構成し、`|G| = |ker|·|im|` を機械確認する。smaller ground / pair / higher-arity / local-certificate SI が返した image `RightCoset` について、その representative と subgroup generators を original domain へ liftし、kernel を加えた preimage subgroup の order が `|ker|·|target subgroup|` と一致することを検証して、complete original-domain coset preimageを返す。target が image 外なら typed fail-closed、generator pairing が homomorphismを定義しない場合も拒否する。GAP が提供する generator-image homomorphism / kernel / PreImage / PreImagesRepresentative と同型の既存世界解を、J の proof-carrying Schreier substrateへ統合した。

PR #52 の workflow run **32283616306 / run #319** で W1R/image-plumbing fast suite **8 passed**、integrated recurrence/master suite **119 passed**、real `nauty-labelg` differential gate **2 passed** を確認し、main SHA `3b5ad239b4b3c439a09544bdb9cd7b760f0fb16c` へ統合した。

予測問題数はすでに **512**、有効問題数も **512**。rev178/179 の pair split、relation orbit、generic preimageを別 active child として加えれば予測超過するため、すべて W1R-H の内部共有 fast path / substrate として横断統合し、active leaf は in-place で **W1R-H2** に置換した。再予測は **512 / 512** のまま。次の未解決末端は **W1R-H2: signed Johnson generator の complement-safe pair/higher-arity image action を明示的に構成し、その smaller image relation SI を既存 proof-carrying S1/V2/candidate machinery で解ける範囲まで解き、exact image coset を rev179 generic preimage で元 J(v,k) domainへ戻す。k>=3 で残る full k-subset color restrictionや hard primitive image は logarithmic local-certificate / Design-Lemma-style aggregationへ再帰する**。

AGI 状態は **NOT_AGI** のまま。AGI 達成、一般性、性能、自律性、実用提供、または full Babai-style quasipolynomial closure は未認定であり、未確認の成果を達成済みとは扱わない。

以後、J の主進捗・CURRENT_STATUS・次の未解決末端はこの系列を基準に更新する。別系統の AGI 評価基盤・custodian/federation 系は、明示的に再指定されない限り J の main line として扱わない。
