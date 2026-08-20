# J main line

J の正本・主系列は **AGI-GI rev 系列** とする。ルート問題は、達成基準を下げず、研究試作で終わらせず、厳格な一般性・性能・自律性を実証し、実際に使える形で AGI を提供することである。問題解決機構そのものを AGI と同一視しない。

系列の実装・検証記録は `automation_runs/2026-08-19_0851_JST/`、実行開始履歴は append-only の `agi/run-history/STARTS.jsonl`、運用境界は `automation/CHATGPT_SCHEDULED_TASK_RUNBOOK.md` を正本とする。

## 現在の継続点

現在の統合済み継続点は **AGI-GI rev206**、main SHA は `8216320c5366108a9ffc686654f411c6d2066729`。

直近の corrected general UPCC Bipartite Split-or-Johnson 系列では、rev199 が exact theorem-input gate、rev200 が proper Reduce-Part2-by-Color / visible-twin shrink、rev201 が source/target-comparable restriction provenance、rev202 が uniform-neighborhood Johnson/relation provenance、rev203 が exact relation-twin restriction provenance、rev204 が no-large-twin relation を exact WL/Design witness cover へ接続し、rev205 が complete witness cover を実際の right-ground ambient action 内の exact transporter coset へ接続した。

rev206 は rev205 の各 right structural coset を、元の完全な colored bipartite state と **actual coupled parent action** の中で exact に交差する境界を統合した。`bipartite_parent_action_coset_intersection_v1` は parent→right generator pairing の exact preimage を取り、left/right vertex colors と全 cross-pair edge/nonedge を一つの induced action 上の string として解くため、独立な左右 symmetric group へ緩和しない。`bipartite_design_parent_union_v1` は rev204/rev205 の complete witness cover を元入力から再導出し、全 surviving branch を exact intersection へ通し、exact-empty だけを捨て、target automorphism と inter-branch differences を検査して complete nonempty union を一つの parent right coset として再構成する。さらに `bipartite_design_recurrence_gate_v1` は、各 structural branch が exact invariant-empty か alpha-smaller auxiliary progress を持つかを fail-closed に検査するが、downstream exact child SI/accounting は deliberate placeholder のままである。

検証済み head `879f2aa4da3c3f130abae64c8b38460659c35a57` は `AGI-GI rev validation` run `32324466475` と `rev206 bipartite parent/coset intersection smoke` run `32324466499` がともに success。PR #123 を main SHA `8216320c5366108a9ffc686654f411c6d2066729` へ squash merge 済みである。

## 問題木

予測問題数は **512**、置換済み旧問題を除く有効問題数も **512**。実数は予測数を超えていないため、横断的な再予測・分岐削除条件は発火していない。rev206 は既存 active leaf **H6-R3c2b / full parent string intersection** を in-place で解決し、set-theoretic witness-union completeness を共有 substrate へ統合した。

局所 full-string child は解決したが、親 **W1R-H6 corrected general UPCC Bipartite Split-or-Johnson recursion** は未解決である。

次の未解決末端は **H6-C1**:

> rev206 の complete parent Design union と `bipartite_design_recurrence_gate_v1` が出す exact-empty / alpha-smaller structural children を、元の root measure に対する proof-carrying exact downstream SI として再帰接続する。auxiliary action degree `|L|+|R|+|L||R|` の polynomial blow-up、rev204 witness family の branch multiplicity、各 source/target Design-progress cost、union reconstruction cost を同じ recurrence certificate に機械的に charge し、全 nonterminal child が corrected Split-or-Johnson の strict-progress 条件を満たす場合だけ global accounting へ渡す。placeholder child、missing provenance、unresolved UPCC/Split-or-Johnson branch、resource overflow は fail closed とする。

## 世界に存在する解法の包含監査

rev206 と祖先の Split-or-Johnson / Design-Lemma 層について、Babai の *Graph Isomorphism in Quasipolynomial Time*、corrected Split-or-Johnson exposition、Luks 型 String Isomorphism / coset reduction を再監査した。既存理論では canonical structure により ambient isomorphism coset を制限し、その中で元の string を解き、各 canonical branch を strict smaller parameter に落として recurrence を閉じる。rev206 は「構造 alignment と元 string の exact intersection」を actual parent group 内で executable にしたため、残る H6-C1 は新しい独立 solver よりも、既存 `RecurrenceAccountingNode`、candidate-coset SI、split/block/UPCC adapters を同じ parent-child certificate に接続する cost/progress transfer 問題へ集約された。

この横断統合により、right neighborhood equality、actual left/right coupling、witness-branch union、parent coset reconstruction は同一 image/preimage + candidate-SI substrate へ削減済みである。したがってそれらを別々の active branches として再導入しない。

## 認定状態

AGI 状態は **NOT_AGI**。full W1R-H6 closure、corrected Split-or-Johnson recursion 全体、global quasipolynomial recurrence、一般性・性能・自律性・実用提供の独立した厳格な実証は未完了であり、認定しない。

スケジューラ制御はリポジトリ成果とは別の外部 control plane である。実行履歴の存在だけを根拠にスケジュールが有効だと捏造しない。各 invocation は監視だけで終わらせず、未解決末端または共有統合を必ず具体的に試行する。
