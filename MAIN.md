# J main line

J の正本・主系列は **AGI-GI rev 系列** とする。ルート問題は、達成基準を下げず、研究試作で終わらせず、厳格な一般性・性能・自律性を実証し、実際に使える形で AGI を提供することである。問題解決機構そのものを AGI と同一視しない。

系列の実装・検証記録は `automation_runs/2026-08-19_0851_JST/`、実行開始履歴は append-only の `agi/run-history/STARTS.jsonl`、運用境界は `automation/CHATGPT_SCHEDULED_TASK_RUNBOOK.md` を正本とする。

## 現在の継続点

現在の統合済み継続点は **AGI-GI rev210**。rev206 までに corrected general UPCC Bipartite Split-or-Johnson の exact theorem-input / restriction provenance / Design witness cover / ambient transporter / actual coupled parent full-string intersection と complete branch-union reconstructionを統合し、rev207 で exact rev206 branch の実 candidate SI accounting を polynomial auxiliary-degree lift として original root の quasipolynomial envelopeへ機械的に戻した。

rev208 は active leaf **H6-C2** の literal natural-domain giant subleafを解決した。represented subgroup が degree `n>=5` で order `n!` または `n!/2` なら、その action 自体が literal `S_n` / `A_n` なので、一般の local-certificates recursionへ送らず、色クラス間の exact transporter と target-color stabilizer（`A_n` では parity intersection）から full String-Isomorphism right cosetを直接復元する。

rev209 は H6-C2 の larger Johnson candidate を既存 rev184 logarithmic certificate / Design descentへ接続した。candidate 全体が full string を既に transport する場合の exact acceptance terminalを追加し、primitive non-giant candidate を exact Johnson ground lift、logarithmic test relation、canonical split/Design substrateへ送る。構造証拠だけの path は exact SI と誤認せず fail closed のまま残した。

rev210 は explicit `canonical_imprimitive_family` subleafを解決した。複数の equally minimum invariant block system から数値ラベルで1個を選ばず、family 全体を polynomial gate 内で処理する。各 block system について quotient imageを exact enumerationし、各 lifted fiberを exact candidate SIで解き、full SI right cosetを再構成する。全 block system の再構成結果が同一 right cosetであることを検証して初めて受理する。recurrence verifier v4 は same-domain `imprimitive_small_quotient` fiberについて、exact terminal leafまたは strict smaller kernel `orbit_partition` のどちらかだけを許すため、非再帰 terminalを人工的に拒否せず、same-size recursive chainは引き続き拒否する。

rev210 head `788df1bdea8c281bf6458ba13e6b100785a0c1bb` は AGI-GI rev validation run `32340533562`、rev210 smoke `32340533547`、rev209 smoke `32340533480`、rev208 smoke `32340533514` がすべて success。PR #138 を squash mergeし、main commit `0d242e5561167baa6d7250be913436f69e91013b` に統合済み。

## 問題木

予測問題数は **512**、置換済み旧問題を除く有効問題数も **512**。今回観測した実数は予測数を超えていないため mandatory over-count full-tree rewrite trigger は発火していない。上限を超えないよう事前に問題追加を抑えて trigger を回避したのではなく、rev209/rev210 は既存 H6-C2 typed subleaf の in-place replacement / branch deletion として扱う。

rev208 により literal natural `A_n/S_n` candidate branch、rev210 により label-dependent single-choice を要求していた multiple-minimum-block-system branchは削除可能になった。一方、primitive non-giant / larger Johnson の structural-only path、nonliteral giant/local-certificates、genuinely unresolved corrected Split-or-Johnson states は未解決のまま。

次の未解決末端は **H6-C2 / primitive non-giant / logarithmic codegree Johnson structural descent**:

> rev184 が `verified_log_certificate_johnson_structural_descent` として止めていた経路で、canonical logarithmic t-relation から exact codegrees により得られた homogeneous pair relationを、構造証拠だけでなく実際の induced pair-action String-Isomorphismとして解く。その exact image right cosetを generator-paired Schreier preimageで original Johnson domainへ戻し、残る full-string candidateを exact に解いて rev207-compatible recurrence accountingへ統合する。arbitrary second Johnson coordinate gauge、missing theorem gate、node/resource overflow、nonexact child は fail closed とする。

この末端に対する rev211 実装は別 branch/PR で検証中であり、CI成功・main統合前には解決済みと認定しない。

## 世界に存在する解法の包含監査

Babai の quasipolynomial SI/GI framework と corrected Split-or-Johnson、Luks 型 orbit/block/coset recursionを親問題レベルまで再監査している。large primitive barrierを Johnson structure と local certificates / Design Lemma / Split-or-Johnson / exact group-coset recursionへ落とす共有解法を優先し、J側では既存 lower-arity relation image、paired-action preimage、block quotient、candidate SI を再利用する。

rev210 の multiple block-system family は、1つのラベル依存代表を選ぶのではなく、複数の equally canonical coset/decomposition を family として保持し全結果の exact consensusを取ることで処理した。rev211 ではさらに、第二 Johnson groundを新solver branchとして増やすより、既に canonical に存在する codegree pair relationそのものを action-image stringとして解く横断策を試している。これにより pair-image / preimage / full-string SI という既存 substrateを上位 H6-C2 から共有できる可能性を検証する。

## 認定状態

AGI 状態は **NOT_AGI**。full W1R-H6 closure、corrected Split-or-Johnson recursion 全体、global quasipolynomial recurrence、一般性・性能・自律性・実用提供の独立した厳格な実証は未完了であり、認定しない。

スケジューラ制御はリポジトリ成果とは別の外部 control plane である。実行履歴の存在だけを根拠にスケジュールが有効だと捏造しない。各 invocation は監視だけで終わらせず、未解決末端または共有統合を必ず具体的に試行する。
