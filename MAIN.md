# J main line

J の正本・主系列は **AGI-GI rev 系列** とする。ルート問題は、達成基準を下げず、研究試作で終わらせず、厳格な一般性・性能・自律性を実証し、実際に使える形で AGI を提供することである。問題解決機構そのものを AGI と同一視しない。

系列の実装・検証記録は `automation_runs/2026-08-19_0851_JST/`、実行開始履歴は append-only の `agi/run-history/STARTS.jsonl`、運用境界は `automation/CHATGPT_SCHEDULED_TASK_RUNBOOK.md` を正本とする。

## 現在の継続点

現在の統合済み継続点は **AGI-GI rev205**、main SHA は `67fde8e615fa8b88a6d2c0e3cff91cc5bd3dd06a`。

直近の corrected general UPCC Bipartite Split-or-Johnson 系列では、rev199 が exact theorem-input gate、rev200 が proper Reduce-Part2-by-Color / visible-twin shrink、rev201 が source/target-comparable restriction provenance、rev202 が uniform-neighborhood Johnson/relation provenance、rev203 が exact relation-twin restriction provenance、rev204 が no-large-twin relation を exact WL/Design witness cover へ接続した。

rev205 は rev204 の complete first-successful Design witness cover を、実際に許された right-ground `StabilizerChain` の中の exact transporter coset へ接続した。ordered individualized tuple ごとに Schreier orbit/stabilizer で exact transporter を構成し、到達不能 tuple pair は厳密に除外する。unary relation は既存の exact canonical partition transporter を用いる。source/target witness cover の全候補を処理するため、ambient right action の範囲では true isomorphism を落とさない complete coset cover を返す。full original bipartite/string intersection はまだ未統合である。

検証済み head `03b833030a820e42078b88aed3f20fb3b78862e1` は `AGI-GI rev validation` run `32323091271` と `rev205 ambient Design tuple transport smoke` run `32323091240` がともに success。PR #121 を main SHA `67fde8e615fa8b88a6d2c0e3cff91cc5bd3dd06a` へ squash merge 済みである。

## 問題木

予測問題数は **512**、置換済み旧問題を除く有効問題数も **512**。実数は予測数を超えていないため、横断的な再予測・分岐削除条件は発火していない。rev205 を別 active node として追加せず、W1R-H6 の既存 active leaf **H6-R3c2a / ambient Design witness pairing** を in-place で解決済みにした。

局所子問題は解決したが、親 **W1R-H6 corrected general UPCC Bipartite Split-or-Johnson recursion** は未解決である。

次の未解決末端は **H6-R3c2b**:

> rev205 が返す各 exact ambient witness coset の中で、元の完全な source/target bipartite/string state を exact に交差させる。右側構造だけでなく左側の許可 action / color constraints も親 provenance から保持し、true parent isomorphism の union completeness を証明する。非空 child は既存 split / block / UPCC recurrence と proof-carrying shrink・quasipolynomial accounting に接続する。left-action provenance、subset/image lift、resource gate、または recurrence accounting が不足する経路は fail closed とする。

## 世界に存在する解法の包含監査

rev205 と祖先の Split-or-Johnson / Design-Lemma 層について、Babai の *Graph Isomorphism in Quasipolynomial Time* と Luks の color-automorphism / String Isomorphism 型 group-action reduction を再監査した。既存理論での canonical structure は、source/target の structure を ambient group 内で align する subcoset を作り、その subcoset の中で元の string isomorphism を解くための制約として使われる。rev205 はこの alignment-domain 構成の right-ground 部分を executable にしたが、元の bipartite incidence 全体と左側 action を同時に交差する責務は H6-R3c2b に残る。

J には `RightCoset`、Schreier chain、generic paired-action image/preimage、candidate-coset String Isomorphism が既に存在する。次段はこれらを再利用し、left-neighborhood family を右側 subgroup の induced subset action 上の exact string として扱える範囲を横断的に統合する。親 left action が full color-symmetric でない場合は、右側だけの family equality を full parent SI と誤認せず、actual left subgroup との coupled transporter を別 proof obligation とする。

## 認定状態

AGI 状態は **NOT_AGI**。full W1R-H6 closure、corrected Split-or-Johnson recursion 全体、global quasipolynomial recurrence、一般性・性能・自律性・実用提供の独立した厳格な実証は未完了であり、認定しない。

スケジューラ制御はリポジトリ成果とは別の外部 control plane である。実行履歴の存在だけを根拠にスケジュールが有効だと捏造しない。各 invocation は監視だけで終わらせず、未解決末端または共有統合を必ず具体的に試行する。
