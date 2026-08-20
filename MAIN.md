# J main line

J の正本・主系列は **AGI-GI rev 系列** とする。ルート問題は、達成基準を下げず、研究試作で終わらせず、厳格な一般性・性能・自律性を実証し、実際に使える形で AGI を提供することである。問題解決機構そのものを AGI と同一視しない。

系列の実装・検証記録は `automation_runs/2026-08-19_0851_JST/`、実行開始履歴は append-only の `agi/run-history/STARTS.jsonl`、運用境界は `automation/CHATGPT_SCHEDULED_TASK_RUNBOOK.md` を正本とする。

## 現在の継続点

現在の統合済み継続点は **AGI-GI rev212**。rev206 までに corrected general UPCC Bipartite Split-or-Johnson の exact theorem-input / restriction provenance / Design witness cover / ambient transporter / actual coupled parent full-string intersection と complete branch-union reconstructionを統合し、rev207 で exact rev206 branch の実 candidate SI accounting を polynomial auxiliary-degree lift として original root の quasipolynomial envelopeへ機械的に戻した。

rev208 は active leaf **H6-C2** の literal natural-domain giant subleafを解決した。represented subgroup が degree `n>=5` で order `n!` または `n!/2` なら、その action 自体が literal `S_n` / `A_n` なので、色クラス間の exact transporter と target-color stabilizerから full String-Isomorphism right cosetを直接復元する。

rev209 は larger Johnson candidate を既存 rev184 logarithmic certificate / Design descentへ接続し、candidate全体が full stringをtransportする場合のexact acceptanceと、canonical relation filterからの継続を追加した。構造証拠だけのpathはexact SIと誤認せずfail closedのまま残した。

rev210 は explicit `canonical_imprimitive_family` subleafを解決した。複数の equally minimum invariant block systemから数値ラベルで1個を選ばず、family全体のquotient/preimage SIをpolynomial gate内で解き、全再構成結果が同一right cosetである場合だけ受理する。recurrence verifier v4はsame-domain quotient fiberについてexact terminalまたはstrict smaller kernel-orbit progressだけを許す。

rev211 は rev184 の second-Johnson structural residualを、第二groundの任意座標を選ばず解決した。既にcanonicalなcodegree pair relationそのものをinduced action上のstringとしてexactに解き、generator-paired Schreier preimageでoriginal Johnson domainへ戻し、full stringをexact filter内で解く。さらに `J(2m+1,m)` のcomplement pairがcanonical blockとなるためclassifierがimprimitiveを返す場合も、bridge自身のJohnson relation証明を必須として試行できるよう修復した。identity candidateには不要なtranslation wrapperを付けず証明status契約を保つ。

rev212 は既存rev177のcomplement-safe signed Johnson ground-profile SIを、transitive candidate境界とintransitive orbitのS1 child境界へ再接続した。profile invariant mismatchはexact empty、profile-determined relationはexact right cosetとして閉じ、rev208 literal giant terminalもS1 childで再利用する。significant partitionがfilterだけを与える場合、partition orbit cap、recognition failure、非profile-determined residualは未確認のexact解とせずfail closedを維持する。

rev212 proposed head `b4ad4d399c8d06660e44b191e6bdd885c12a44e0` は AGI-GI rev validation run `32344669426`、rev212 smoke `32344669444`、rev211 smoke `32344669402`、rev210 smoke `32344669405`、rev209 smoke `32344669433`、rev208 smoke `32344669483` がすべて success。PR #140 をsquash mergeし、main commit `a4b426f9a43b7142395ff289e5a419a834cadf53` に統合済み。競合していた旧PR #139は未mergeのままsupersededとして閉じた。

## 問題木

予測問題数は **512**、置換済み旧問題を除く有効問題数も **512**。今回観測した実数は予測数を超えていないため mandatory over-count full-tree rewrite trigger は発火していない。上限を超えないよう事前に問題追加を抑えてtriggerを回避したのではなく、rev211/rev212は既存H6-C2 typed residualのin-place replacement / branch deletionとして扱う。

rev211により arbitrary second-Johnson coordinate gauge / separate second-ground reconstruction branch、rev212によりprofile-determined candidateとS1 orbit-childの重複branchは削除可能になった。一方、non-profile-determined significant filter、profile no-split/higher-order relation、resource-gated candidate、corrected Split-or-Johnsonの残部、W1R-H6 parent、AGI rootは未解決のまま。

次の未解決末端は **H6-C2 / primitive non-giant / significant signed-ground profile filter / nonclosing restricted candidate**:

> rev177 が `verified_signed_ground_profile_partition_filter` とexact original-domain filter cosetを返すが、rev211 dispatcherをそのfilter内で1回実行してもexactに閉じない場合を扱う。canonical significant ground splitをstrict progressとして証明し、filter subgroup内のcandidate SIまたはsmaller-ground higher-order/local-certificate relationへ再帰的に接続し、exact resultをoriginal candidateへ戻す。same-domain self-loop、missing theorem gate、nonexact child、partition/recognition/resource overflowはfail closedとする。

兄弟の `undetermined_signed_ground_profile_no_split`、primitive/local-certificate、corrected Split-or-Johnson residualは、この末端の解決だけで削除しない。

## 世界に存在する解法の包含監査

Babai の quasipolynomial SI/GI framework と corrected Split-or-Johnson、Luks 型 orbit/block/coset recursionを親問題レベルまで再監査している。large primitive barrierをJohnson structureとlocal certificates / Design Lemma / Split-or-Johnson / exact group-coset recursionへ落とす共有解法を優先し、J側では既存lower-arity relation image、paired-action preimage、block quotient、candidate SI、proof-carrying recurrenceを再利用する。

rev211はcanonical pair relationをそのままaction-image stringとして解くことで、第二Johnson coordinate gaugeの分岐を上位H6-C2から削除した。rev212はrev177のsigned profile solverとrev208 literal giant terminalを共有境界へ持ち上げ、同一Jリポジトリの未統合PR #128を実装上の既存案として確認した上で、最新rev211 treeへfail-closedに再構成した。PR #128はmerged progressや達成証拠には数えていない。

次のfilter residualでも新しい独立solver treeを作らず、既存のcanonical partition、smaller-ground local relation、exact candidate coset intersection/preimage、recurrence accountingを統合する。世界に存在する解法の包含確認は細部だけでなくH6-C2、W1R-H6、AGI rootの各親層で継続し、親から不要になった分岐だけを削除する。

## 認定状態

AGI 状態は **NOT_AGI**。full W1R-H6 closure、corrected Split-or-Johnson recursion 全体、global quasipolynomial recurrence、一般性・性能・自律性・実用提供の独立した厳格な実証は未完了であり、認定しない。

スケジューラ制御はリポジトリ成果とは別の外部 control plane である。実行履歴の存在だけを根拠にスケジュールが有効だと捏造しない。各 invocation は監視だけで終わらせず、未解決末端または共有統合を必ず具体的に試行する。
