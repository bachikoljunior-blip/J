# J main line

J の正本・主系列は **AGI-GI rev 系列** とする。ルート問題は、達成基準を下げず、研究試作で終わらせず、厳格な一般性・性能・自律性を実証し、実際に使える形で AGI を提供することである。問題解決機構そのものを AGI と同一視しない。

系列の実装・検証記録は `automation_runs/2026-08-19_0851_JST/`、実行開始履歴は append-only の `agi/run-history/STARTS.jsonl`、運用境界は `automation/CHATGPT_SCHEDULED_TASK_RUNBOOK.md` を正本とする。

## 現在の継続点

現在の統合済み継続点は **AGI-GI rev208**。rev206 までに corrected general UPCC Bipartite Split-or-Johnson の exact theorem-input / restriction provenance / Design witness cover / ambient transporter / actual coupled parent full-string intersection と complete branch-union reconstructionを統合し、rev207 で exact rev206 branch の実 candidate SI accounting を polynomial auxiliary-degree lift として original root の quasipolynomial envelopeへ機械的に戻した。

rev208 は active leaf **H6-C2** の literal natural-domain giant subleafを解決した。represented subgroup が degree `n>=5` で order `n!` または `n!/2` なら、その action 自体が literal `S_n` / `A_n` なので、一般の local-certificates recursionへ送らず、色クラス間の exact transporter と target-color stabilizer（`A_n` では parity intersection）から full String-Isomorphism right cosetを直接復元する。candidate `H*r` は fixed representative を exact に剥がして subgroup SI を解き、既存 right-coset translation primitive で戻す。rev206 parent intersection と rev207 proof replay は同じ rev208 candidate dispatcherを使うため、execution/replay status の対応を保つ。

rev208 head は AGI-GI rev validation run `32332190089` と rev208 literal giant SI smoke run `32332190156` が success。main commit `861328e56a74ae240092bfbd671c23d993b893e9` に統合済み。

## 問題木

予測問題数は **512**、置換済み旧問題を除く有効問題数も **512**。実数は予測数を超えていないため mandatory over-count full-tree rewrite trigger は発火していない。

rev208 により、singleton-block classifier が literal natural `A_n/S_n` と認定する candidateを general giant/local-certificates branch として残す必要はなくなった。これは上位 H6-C2 内の branch deletion であり、nonliteral giant quotient、primitive non-giant / larger Johnson、remaining Split-or-Johnson statesを解決済みとは扱わない。

次の未解決末端は **H6-C2** の残部:

> primitive non-giant / larger Johnson-ground candidate と genuinely unresolved Split-or-Johnson image stateを、既存 exact lower-arity relation image・paired preimage・signed-ground/profile・log-certificate/Design substrateへ接続し、rev207 polynomial-lift invariantを維持する。exact でない structural evidence、missing theorem gate、resource overflow は fail closed とする。

## 世界に存在する解法の包含監査

Babai の quasipolynomial SI/GI framework と corrected Split-or-Johnson、Luks 型 orbit/block/coset recursionを親問題レベルまで再監査している。Babai の主結果では large primitive barrier が Johnson actionへ還元され、local certificates / Design Lemma / Split-or-Johnson と exact group/coset recursionの組合せで quasipolynomial SI を得る。rev208 の literal `A_n/S_n` はその一般 theorem machineryより強い特殊条件を持つため direct color-class coset terminalで branchを削除できる一方、larger Johnson と nonliteral quotient は既存 W1R relation/preimage/Design substrateへ戻すのが共有解法であり、別の独立 solver treeを増やさない。

## 認定状態

AGI 状態は **NOT_AGI**。full W1R-H6 closure、corrected Split-or-Johnson recursion 全体、global quasipolynomial recurrence、一般性・性能・自律性・実用提供の独立した厳格な実証は未完了であり、認定しない。

スケジューラ制御はリポジトリ成果とは別の外部 control plane である。実行履歴の存在だけを根拠にスケジュールが有効だと捏造しない。各 invocation は監視だけで終わらせず、未解決末端または共有統合を必ず具体的に試行する。
