# J main line

J の正本・主系列は **AGI-GI rev系列** とする。

この系列は `automation_runs/2026-08-19_0851_JST/AGI_GI_REV_SERIES.md` に定義された、rev91 から継続する graph alignment / symmetry / graph isomorphism / permutation-group / canonical-labeling 系である。

現在の継続点は **rev183**。rev140〜143 で独立 `labelg` differential oracle を実 CI まで検証して B1 を解決し、rev144〜168 で canonical local-certificate partition、exact transporter/coset、quotient/kernel、affected/unaffected、growing-beard、fail-closed quasipolynomial accounting を proof-carrying SI substrate へ統合・横断整理した。rev169〜177 で candidate-fiber recursion、imprimitive closure、Johnson small-ground / relational lift / signed-ground terminals、point-profile partition orbit を追加した。

rev178〜182 は W1R の Johnson hard branch を進めた。first-order point-profile が一様でも actual colored k-subset relation から complement-safe pair relationを作り、smaller relation image SI と exact image-to-original preimage を実装した。`paired_action_coset_preimage_v1` は generator-paired action の image/kernel を Schreier で証明し、任意の exact image `RightCoset` を complete original-domain preimage cosetへ戻す。続いて v=2k complement を含む signed Johnson lower-arity image、full colored k-subset candidate restriction、pair が一様なら higher arity を選ぶ adaptive selectorまで追加した。

rev183 は **W1R-H4 joint lower-arity relation image closure** を実装した。複数の informative complement-safe lower-arity relation を同一 original group の generator pairing のまま disjoint-union auxiliary actionへ結合し、総 auxiliary degree を `0.9 * C(v,k)` 以下に制限する。joint image で exact string/coset intersection を解き、generic paired-action preimage で kernel を含む complete original-domain candidate を復元し、その中で既存 U2/S1/V2 machinery により full colored k-subset stringを解く。source/target lower-arity multiplicity mismatch は exact empty、node cap・relation不足・shrink budget不足は fail closed。J(10,4) の pair+triple 同時選択、small exact joint-image/preimage closure、budget fail-closed を regression 化した。

PR #56 の workflow run **32289134006 / run #357** で `validate-w1r-fast`、regular-prime/master integration、Babai recurrence contract suite、実 `nauty-labelg` differential gate がすべて **success**。PR は main SHA `7e3902f46ae278fc72ef7ac4993c39f9efce2184` へ squash merge 済み。CI は同一 PR の stale head run を自動キャンセルし、外部 `nauty` install より前に Python integration を実行するよう整理した。

予測問題数は **512**、有効問題数も **512**。すでに上限に達しているため rev183 を別 active child として追加せず、W1R-H4 を内部共有 substrate として解決し、active leaf を in-place で **W1R-H5** に置換する。次の未解決末端は **W1R-H5: joint lower-arity image で閉じないケースについて、logarithmic test-set local certificates を canonical higher-arity relationへ集約する。certificate incidence から label-invariant significant point split を得られる場合は既存 recursionへ接続し、homogeneous nontrivial relationが残る場合は proof-carrying Design-Lemma-style descentで split/Johnson/candidate machineryへ落とす。theorem parameter gate、exactness、quasipolynomial accounting を満たせない経路は fail closed とする**。

AGI 状態は **NOT_AGI** のまま。AGI 達成、一般性、性能、自律性、実用提供、または full Babai-style quasipolynomial closure は未認定であり、未確認の成果を達成済みとは扱わない。

以後、J の主進捗・CURRENT_STATUS・次の未解決末端はこの系列を基準に更新する。別系統の AGI 評価基盤・custodian/federation 系は、明示的に再指定されない限り J の main line として扱わない。
