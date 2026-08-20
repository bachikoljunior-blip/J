# J main line

J の正本・主系列は **AGI-GI rev 系列** とする。ルート問題は、達成基準を下げず、研究試作で終わらせず、厳格な一般性・性能・自律性を実証し、実際に使える形で AGI を提供することである。問題解決機構そのものを AGI と同一視しない。

系列の実装・検証記録は `automation_runs/2026-08-19_0851_JST/`、実行開始履歴は append-only の `agi/run-history/STARTS.jsonl`、運用境界は `automation/CHATGPT_SCHEDULED_TASK_RUNBOOK.md` を正本とする。

## 現在の継続点

現在の統合済み継続点は **AGI-GI rev207**。rev206 までに corrected general UPCC Bipartite Split-or-Johnson の exact theorem-input / restriction provenance / Design witness cover / ambient transporter / actual coupled parent full-string intersection と complete branch-union reconstructionを統合した。

rev207 は既存 active leaf **H6-C1** を横断整理した。`bipartite_parent_polynomial_lift_accounting_v2.py` は rev206 が実際に exact solve できた各 branch について、同じ paired parent→right preimage と coupled auxiliary action を再現し、実際に実行された `candidate_coset_string_isomorphism_u2` の proof-carrying accounting tree を `validate_quasipoly_recurrence_tree_v3` で再検証する。left/right は parent domain の互いに素な部分集合なので auxiliary degree

`M = |L| + |R| + |L||R| <= root_n + root_n^2`

を機械的に確認し、Design structural local cost、実 branch 数、rev206 union bookkeeping、固定次数 polynomial wrapper と子 SI work を original root の quasipolynomial envelope へ charge する。rev206 自体が exact でない branch、子 accounting failure、degree gate failure、translated envelope overflow は fail closed のままである。one-shot iterable は v2 entry point で一度だけ materialize し、union→proof replay 間の消費差異も regression 化した。

検証済み head `20872d2a9a9f229b0eeb9526643d852d2b6b9e82` は `AGI-GI rev validation` run `32327521033` と `rev207 polynomial auxiliary accounting smoke` run `32327521040` がともに success。PR #124 を merge SHA `52db33dc0cadbf0ad9f4f6bfb658279bc241e393` として main へ squash merge 済み。

## 問題木

予測問題数は **512**、置換済み旧問題を除く有効問題数も **512**。実数は予測数を超えていないため mandatory over-count full-tree rewrite trigger は発火していない。

rev207 により、**exact rev206 instance について quadratic auxiliary action を説明するためだけの artificial structural-child recursion は不要**になった。これは H6-C1 を in-place で共有 substrate へ置換したもので、rev206 が未解決の candidate SI branchを解決済みとみなすものではない。

次の未解決末端は **H6-C2**:

> rev206 coupled parent action 内でまだ typed unresolved となる proof-carrying candidate SI を閉じる。特に literal primitive giant A/S、primitive non-giant / larger Johnson ground、genuinely unresolved Split-or-Johnson image statesを既存 exact group/coset substrateへ接続し、rev207 polynomial-lift invariant を維持する。未確認 theorem gate、resource overflow、nonexact child は fail closed とする。

## 世界に存在する解法の包含監査

Babai の quasipolynomial GI / corrected Split-or-Johnson と Luks 型 String Isomorphism / coset reduction を親問題レベルまで再監査した。rev207 の要点は、polynomial-size induced action を新しい独立主問題として再帰する必要はなく、実行済み child SI が exact proof-carrying recurrence を持ち induced degree が original root の fixed polynomial で抑えられるなら、その work を original root measure へ戻せるという横断統合である。right neighborhood equality、actual parent coupling、Design branch union、candidate full-string SI、polynomial auxiliary accounting は同じ image/preimage + coset SI substrate として扱い、別 active branches として再導入しない。

## 認定状態

AGI 状態は **NOT_AGI**。full W1R-H6 closure、corrected Split-or-Johnson recursion 全体、global quasipolynomial recurrence、一般性・性能・自律性・実用提供の独立した厳格な実証は未完了であり、認定しない。

スケジューラ制御はリポジトリ成果とは別の外部 control plane である。実行履歴の存在だけを根拠にスケジュールが有効だと捏造しない。各 invocation は監視だけで終わらせず、未解決末端または共有統合を必ず具体的に試行する。
