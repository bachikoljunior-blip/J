# J main line

J の正本・主系列は **AGI-GI rev 系列** とする。ルート問題は、達成基準を下げず、研究試作で終わらせず、厳格な一般性・性能・自律性を実証し、実際に使える形で AGI を提供することである。問題解決機構そのものを AGI と同一視しない。

系列の実装・検証記録は `automation_runs/2026-08-19_0851_JST/`、実行開始履歴は append-only の `agi/run-history/STARTS.jsonl`、運用境界は `automation/CHATGPT_SCHEDULED_TASK_RUNBOOK.md` を正本とする。

## 現在の継続点

現在の統合済み継続点は **AGI-GI rev204**、main SHA は `6faeca0956346f61c323a5f63dc5f4738c662102`。

直近の corrected general UPCC Bipartite Split-or-Johnson 系列では、rev199 が exact theorem-input gate、rev200 が proper Reduce-Part2-by-Color / visible-twin shrink、rev201 が source/target-comparable restriction provenance、rev202 が uniform-neighborhood Johnson/relation provenance、rev203 が exact relation-twin restriction provenanceを追加した。

rev204 は、rev202・rev203 の親 provenance を毎回再導出し、no-large-twin relation を exact WL/Design descent へ接続する `relation_twin_design_wiring_v1` を統合した。unary relation は half-bounded coloring、arity 2 以上は actual containment palette と complete source/target witness Cartesian productへ進める。完全 witness 集合は明示的 cap の内側でのみ exact とし、mismatch、resource cap、親の非適用、未決定を成功扱いせず fail closed とする。

検証済み head は `5bfd0d479ded35829d8656a5dc4a10aa1857d006`。`AGI-GI rev validation` run `32318413846` と `rev204 relation Design wiring smoke` run `32318413871` は success。PR #119 を上記 main SHA へ squash merge 済みである。

## 問題木

予測問題数は **512**、置換済み旧問題を除く有効問題数も **512**。実数は予測数を超えていないため、今回の横断的な再予測・分岐削除条件は発火していない。rev204 を別 active node として追加せず、W1R-H6 の既存 active leaf **H6-R3c1** を in-place で解決済みにした。

H6-R3c1 の局所子問題は解決したが、親 **W1R-H6 corrected general UPCC Bipartite Split-or-Johnson recursion** は未解決である。

次の未解決末端は **H6-R3c2**:

> complete exact witness の全分岐を ambient structural transporter と full-string branch union へ接続し、union の exact completeness と strict progress を証明する。unmatched witness、resource cap、transport failure、source/target incompatibility、または recurrence accounting の不足は fail closed とする。

## 世界に存在する解法の包含監査

H6-R3c1 と祖先の Split-or-Johnson / Design-Lemma 層について、Babai の *Graph Isomorphism in Quasipolynomial Time*（arXiv:1512.03547）を最も近い既存解法として再監査した。同論文は theorem-level の Split-or-Johnson と Design-Lemma の構造的選択肢を与えるが、このリポジトリが必要とする executable な二側 complete witness 列挙、cap-certified exact completeness、ambient transporter/full-string branch union、機械検査可能な fail-closed 統合をそのまま包含しない。この境界を埋めることが H6-R3c2 以降の実装・証明責務である。

## 認定状態

AGI 状態は **NOT_AGI**。full W1R-H6 closure、corrected Split-or-Johnson recursion 全体、global quasipolynomial recurrence、一般性・性能・自律性・実用提供の独立した厳格な実証は未完了であり、認定しない。

スケジューラ制御はリポジトリ成果とは別の外部 control plane である。このセッションから scheduler の作成・有効化・状態読取を行える機能が露出していない場合、実行履歴の存在だけを根拠にスケジュールが有効だと捏造しない。各 invocation は監視だけで終わらせず、未解決末端または共有統合を必ず具体的に試行する。
