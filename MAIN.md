# J main line

J の正本・主系列は **AGI-GI rev系列** とする。

この系列は `automation_runs/2026-08-19_0851_JST/AGI_GI_REV_SERIES.md` に定義された、rev91 から継続する graph alignment / symmetry / graph isomorphism / permutation-group / canonical-labeling 系である。

現在の継続点は **rev185**。rev140〜143 で独立 `labelg` differential oracle を実 CI まで検証して B1 を解決し、rev144〜168 で canonical local-certificate partition、exact transporter/coset、quotient/kernel、affected/unaffected、growing-beard、fail-closed quasipolynomial accounting を proof-carrying SI substrate へ統合・横断整理した。rev169〜177 で candidate-fiber recursion、imprimitive closure、Johnson small-ground / relational lift / signed-ground terminals、point-profile partition orbit を追加した。

rev178〜183 は W1R の Johnson hard branchを進めた。actual colored k-subset relation から complement-safe lower-arity relationを作り、smaller relation image SI、exact image-to-original preimage、adaptive arity selection、複数 relation の joint image closureを実装した。`paired_action_coset_preimage_v1` は generator-paired action の image/kernel を Schreier で証明し、任意の exact image `RightCoset` を complete original-domain preimage cosetへ戻す。rev183 の W1R-H4 は、joint auxiliary degree、node cap、relation availability、shrink budgetを機械的に検査し、満たさない経路を fail closed とした。

rev184 は **W1R-H5 logarithmic certificate Design-Lemma descent** を実装した。認識済み Johnson ground 上で `t=min(k-1, ceil(log2(v)))` の complete complement-safe colored t-subset relationを構築し、joint source/target incidence refinement、canonical lower-arity codegree descent、coherent/Johnson pair reduction、significant point split の exact signed-partition transport、original-domain candidate-coset continuationを proof-carrying に接続した。relation invariant mismatch は exact empty、theorem/test-count gate、partition-orbit cap、candidate continuationを満たさない経路は fail closed とし、lower-codegree homogeneous designを未解決のまま残した。

rev185 は **exact colored-subset symmetry-defect gate** を追加した。complete colored t-subset relationについて、各 transposition が全 relation entryを保存するかを直接検査して twin classesを構成し、最大 twin classが最大 symmetric subsetであることを証明境界として記録する。これにより Design-Lemma の symmetry-defect hypothesisを推定ではなく exact certificateとして判定できる。complete homogeneous relationでは gateが閉じ、distinguished-point relationおよび Fano 2-(7,3,1) design regressionでは期待された defect certificateを得る。full individualization/WL Design Lemma または full W1R closure はまだ実装・認定していない。

PR #62 の head SHA `14cd6bf323aff88c607da309d32325d1a5a49783` に対し、workflow **AGI-GI rev validation / run 32298170149** と **rev185 symmetry defect smoke / run 32298170199** はともに success。PR は main SHA `38d7fffd1f504b5d30b66bd332d9435b49f2f65c` へ squash merge済み。

予測問題数は **512**、有効問題数も **512**。すでに上限に達しているため rev184・rev185 を別 active childとして追加せず、W1R-H5 の共有 substrateとして解決済み部分を内部化し、active leafを in-place で **W1R-H6** に置換する。次の未解決末端は **W1R-H6: rev184 が返す lower-codegree homogeneous logarithmic relationへ rev185 の exact symmetry-defect certificateを proof-carryingに接続する。defect gateが成立する場合、canonical logarithmic individualization/test familyと bounded WL/local-certificate refinementを実行し、label-invariant significant split、certified Johnson descent、または exact candidate cosetへ落とす。theorem hypotheses、source/target comparability、exactness、strict progress、quasipolynomial recurrence accountingを満たせない経路は fail closed とする**。

AGI 状態は **NOT_AGI** のまま。AGI 達成、一般性、性能、自律性、実用提供、または full Babai-style quasipolynomial closure は未認定であり、未確認の成果を達成済みとは扱わない。

以後、J の主進捗・CURRENT_STATUS・次の未解決末端はこの系列を基準に更新する。別系統の AGI 評価基盤・custodian/federation 系は、明示的に再指定されない限り J の main line として扱わない。ChatGPT Scheduled Tasks を含む実行運用は `automation/CHATGPT_SCHEDULED_TASK_RUNBOOK.md` に従い、スケジュール自己更新の失敗をアルゴリズム成果の失敗と混同しない。
