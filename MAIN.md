# J main line

J の正本・主系列は **AGI-GI rev系列** とする。

この系列は `automation_runs/2026-08-19_0851_JST/AGI_GI_REV_SERIES.md` に定義された、rev91 から継続する graph alignment / symmetry / graph isomorphism / permutation-group / canonical-labeling 系である。

現在の継続点は **rev186**。rev140〜143 で独立 `labelg` differential oracle を実 CI まで検証して B1 を解決し、rev144〜168 で canonical local-certificate partition、exact transporter/coset、quotient/kernel、affected/unaffected、growing-beard、fail-closed quasipolynomial accounting を proof-carrying SI substrate へ統合・横断整理した。rev169〜177 で candidate-fiber recursion、imprimitive closure、Johnson small-ground / relational lift / signed-ground terminals、point-profile partition orbit を追加した。

rev178〜183 は W1R の Johnson hard branchを進めた。actual colored k-subset relation から complement-safe lower-arity relationを作り、smaller relation image SI、exact image-to-original preimage、adaptive arity selection、複数 relation の joint image closureを実装した。`paired_action_coset_preimage_v1` は generator-paired action の image/kernel を Schreier で証明し、任意の exact image `RightCoset` を complete original-domain preimage cosetへ戻す。rev183 の W1R-H4 は、joint auxiliary degree、node cap、relation availability、shrink budgetを機械的に検査し、満たさない経路を fail closed とした。

rev184 は **W1R-H5 logarithmic certificate Design-Lemma descent** を実装した。認識済み Johnson ground 上で `t=min(k-1, ceil(log2(v)))` の complete complement-safe colored t-subset relationを構築し、joint source/target incidence refinement、canonical lower-arity codegree descent、coherent/Johnson pair reduction、significant point split の exact signed-partition transport、original-domain candidate-coset continuationを proof-carrying に接続した。relation invariant mismatch は exact empty、theorem/test-count gate、partition-orbit cap、candidate continuationを満たさない経路は fail closed とし、lower-codegree homogeneous designを未解決のまま残した。

rev185 は **exact colored-subset symmetry-defect gate** を追加した。complete colored t-subset relationについて、各 transposition が全 relation entryを保存するかを直接検査して twin classesを構成し、最大 twin classが最大 symmetric subsetであることを証明境界として記録する。これにより Design-Lemma の strong symmetry-defect hypothesisを推定ではなく exact certificateとして判定できる。complete homogeneous relationでは gateが閉じ、distinguished-point relationおよび Fano 2-(7,3,1) design regressionでは期待された defect certificateを得る。

rev186 は **rev184 homogeneous-design boundary と rev185 exact symmetry-defect gate の proof-carrying接続**を実装した。rev184 が `undetermined_log_certificate_design_gate` を返した場合だけ同一の certified Johnson gaugeで complete complement-safe logarithmic relationを再構成し、source/target の exact relation-color multiplicity、twin-class size multiset、strong symmetry-defect gateを比較する。relation-color または twin-shape mismatchは exact empty terminal、両側の defect gate成立は次の Design-Lemma childへ進める verified structural result、gate不成立は実行量を記録した fail-closed nonterminalとする。その他の rev184 出力は再分類せずそのまま通す。

PR #71 の head SHA `dbf9b9435dff0dd8a86cc68245aad66ac9e33720` に対し、workflow **AGI-GI rev validation / run 32305113816** は `validate-w1r-fast` と full `validate-rev-series` の両方が success。fast suiteは rev186 regressionを含め **26 passed**、full suiteは recurrence/master integration と実 `nauty-labelg` differential gateまで success。PR は main SHA `9760ab64c6123d77bd8592d39aad77adae28604b` へ squash merge済み。

既存世界解の包含監査では、Babai の Design Lemma が残る数学的出口を包含することを確認した。strong symmetry defect の仮定下で高々 `t-1` 点を individualizeし、`t`-dimensional Weisfeiler–Leman refinement後に canonical alpha-partition または大きな canonically embedded uniprimitive coherent configurationを得る。ただし J にまだ内包されていないのは、paired/canonical individualization familyの選択、一般 `t`-WL、alpha-partition/UPCC verifier、signed Johnson/original-domain transport、これらの quasipolynomial recurrence compositionであり、文献名だけを closure として扱わない。

予測問題数は **512**、有効問題数も **512**。上限に達しているため rev186 を別 active childとして追加せず、W1R-H6 を共有 substrateとして内部化し、active leafを in-place で **W1R-H7** に置換する。次の未解決末端は **W1R-H7: exact paired symmetry-defect gateが成立した complete logarithmic t-subset relationに対し、長さ高々 t-1 の paired individualization familyを label-invariantに生成・比較し、standard correlated-replacement t-WLを bounded/execution-accountedに実行する。各結果から alpha-bounded point partitionまたは canonically embedded UPCCを機械検証し、signed Johnson actionを介して original-domain partition/candidate cosetへ完全にtransportする。個別化選択、source/target comparability、UPCC primitivity/coherence、strict progress、recurrence accountingのいずれかを証明できない経路は fail closed とする**。

AGI 状態は **NOT_AGI** のまま。AGI 達成、一般性、性能、自律性、実用提供、または full Babai-style quasipolynomial closure は未認定であり、未確認の成果を達成済みとは扱わない。

以後、J の主進捗・CURRENT_STATUS・次の未解決末端はこの系列を基準に更新する。別系統の AGI 評価基盤・custodian/federation 系は、明示的に再指定されない限り J の main line として扱わない。ChatGPT Scheduled Tasks を含む実行運用は `automation/CHATGPT_SCHEDULED_TASK_RUNBOOK.md` に従い、スケジュール自己更新の失敗をアルゴリズム成果の失敗と混同しない。
