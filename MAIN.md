# J main line

J の正本・主系列は **AGI-GI rev 系列** とする。ルート問題は、達成基準を下げず、研究試作で終わらせず、厳格な一般性・性能・自律性を実証し、実際に使える形で AGI を提供することである。問題解決機構そのものを AGI と同一視しない。

系列の実装・検証記録は `automation_runs/2026-08-19_0851_JST/`、実行開始履歴は append-only の `agi/run-history/STARTS.jsonl`、運用境界は `automation/CHATGPT_SCHEDULED_TASK_RUNBOOK.md` を正本とする。

## 現在の継続点

現在の統合済み継続点は **AGI-GI rev214**。rev206 までに corrected general UPCC Bipartite Split-or-Johnson の exact theorem-input / restriction provenance / Design witness cover / ambient transporter / actual coupled parent full-string intersection と complete branch-union reconstructionを統合し、rev207 で exact rev206 branch の実 candidate SI accounting を polynomial auxiliary-degree lift として original root の quasipolynomial envelopeへ機械的に戻した。

rev208 は active leaf **H6-C2** の literal natural-domain giant subleafを解決した。represented subgroup が degree `n>=5` で order `n!` または `n!/2` なら、その action 自体が literal `S_n` / `A_n` なので、色クラス間の exact transporter と target-color stabilizerから full String-Isomorphism right cosetを直接復元する。

rev209 は larger Johnson candidate を既存 rev184 logarithmic certificate / Design descentへ接続し、candidate全体が full stringをtransportする場合のexact acceptanceと、canonical relation filterからの継続を追加した。構造証拠だけのpathはexact SIと誤認せずfail closedのまま残した。

rev210 は explicit `canonical_imprimitive_family` subleafを解決した。複数の equally minimum invariant block systemから数値ラベルで1個を選ばず、family全体のquotient/preimage SIをpolynomial gate内で解き、全再構成結果が同一right cosetである場合だけ受理する。recurrence verifier v4はsame-domain quotient fiberについてexact terminalまたはstrict smaller kernel-orbit progressだけを許す。

rev211 は rev184 の second-Johnson structural residualを、第二groundの任意座標を選ばず解決した。既にcanonicalなcodegree pair relationそのものをinduced action上のstringとしてexactに解き、generator-paired Schreier preimageでoriginal Johnson domainへ戻し、full stringをexact filter内で解く。さらに `J(2m+1,m)` のcomplement pairがcanonical blockとなるためclassifierがimprimitiveを返す場合も、bridge自身のJohnson relation証明を必須として試行できるよう修復した。identity candidateには不要なtranslation wrapperを付けず証明status契約を保つ。

rev212 は既存rev177のcomplement-safe signed Johnson ground-profile SIを、transitive candidate境界とintransitive orbitのS1 child境界へ再接続した。profile invariant mismatchはexact empty、profile-determined relationはexact right cosetとして閉じ、rev208 literal giant terminalもS1 childで再利用する。significant partitionがfilterだけを与える場合、partition orbit cap、recognition failure、非profile-determined residualは未確認のexact解とせずfail closedを維持する。

rev213 はその significant-profile filter を nested orbit depth で実用化した。S1 v4がnewest exact terminalsを自己再帰でも保持し、bounded Johnson-ground terminalをprofile no-splitより先に再利用し、explicit/polylog auxiliary window内のtransitive imprimitive childを既存candidate block/family dispatcherへ戻す。さらにrev177のsource partition stabilizerをrepositoryのright-coset規約に必要なtarget stabilizerへ共役し、nonidentity transporterで隠れていたcoset completenessとodd-witness compositionを修復した。上限外のground/quotient、recognition・partition resource overflowはfail closedのままである。

rev213 proposed head `99e3fee47b50da06ddd1759042d14c3b9e9e753a` は AGI-GI rev validation run `32350556780`（independent `nauty-labelg` differential gateを含む）、rev213 smoke `32350556943`、rev212 smoke `32350556946`、rev211 smoke `32350556857`、rev210 smoke `32350556734`、rev209 smoke `32350556754`、rev208 smoke `32350556751` がすべて success。PR #141 をmergeし、main commit `be165ab362127e81a8272bc470191606948e5e3c` に統合済み。

rev214 は rev184 が nonconstant homogeneous pair relationへ到達した後の不要なJohnson-only gateを除いた。`C(v,2)<C(v,k)` のstrict pair imageをexact SIとして解き、generator-paired Schreier preimageでoriginal candidateへ戻してfull stringをproper filter内で解く。homogeneous/nonshrinking/resource-capped imageはfail closed、preimageがambient candidateと同一ならwhole-candidate exact terminal以外をsame-domain self-loopとして拒否する。`J(9,3)` 上のcyclic-triple regressionではbounded ground外、uniform point profile、non-Johnson pair relationからtarget stabilizer order 9のexact right cosetを復元し、既知nonidentity transporterとrecurrence v4を検証した。

rev214 tested head `2b1852c88f33a85aeaddaa2bc488353d7021a2fc` は AGI-GI rev validation run `32357682162`（independent `nauty-labelg` differential gateを含む）、rev214 smoke `32357682062`、rev213 smoke `32357682097`、rev212 smoke `32357682143`、rev211 smoke `32357682073`、rev210 smoke `32357682141`、rev209 smoke `32357682065`、rev208 smoke `32357682129` がすべて success。先行run `32355898849` は主検証成功後に20分上限でoracle導入中cancelとなり証拠に数えず、実測に基づき30分へ修正して全gateを再実行した。PR #142 をmergeし、main commit `e7b190ae5de9a2ceb4238145a337daa4b7b1f5a0` に統合済み。

## 問題木

新しい予測問題数は **576**、置換済み旧問題を除く有効問題数は **513**。旧予測/実数512/512の末端を直接試行し、解決したgeneric strict-pair subcaseと未解決5子問題へ分解した時点で実数は一時的に517となり、旧予測512を実際に超えた。この超過を事前抑制せず、mandatory full-tree rewrite triggerを発火させた。

置換済み旧問題を除く全層――primitive relation、H6-C2、W1R-H6 corrected Split-or-Johnson/Design branch、global proof-carrying recurrence/resource、AGI rootの一般性・性能・自律性・実用提供――を横断し、7本の狭いrelation/filter/cap branchを三つのsolution-shaped problemへ書き換えた。**CRX1 exact canonical relation quotient/preimage closure**、**CRX2 information/symmetry-defect relation selection**、**CRX3 replay-stable proof/resource substrate**であり、単なる重複名の統合ではなく上位親から共有できる解法境界である。結果は `517 - 7 + 3 = 513`、再予測576。rev214はCRX1のnonconstant strict-pair subcaseとCRX3のhomogeneous/self-loop guardsだけを解決した。

CRX1の`k<=2`、homogeneous/nonrestricting relation image、node/resource-capped image SI、CRX2のcanonical local-certificate/Design escalation、CRX3のproof identity replay/memoization、corrected Split-or-Johnson残部、W1R-H6 parent、AGI rootは未解決のままである。

次の未解決末端は **CRX3 / replay-stable proof and resource substrate / duplicated relation recognition and Johnson lift/descent across candidate dispatchers**:

> u7、S1、rev207 replayが繰り返すJohnson recognition、ground lift、log-codegree descent、paired-action preimageを、canonical inputとproof identityで共有するexact proof DAGへする。source/target orientation、generator pairing、strict progress、work chargeをreplay時に再検証し、heuristic result、resource-dependent unresolved、noncanonical coordinate、未証明cosetをcache hitでexact化しない。意味論を変えず、今回観測した重複計算を除けることをregressionとrecurrence accountingで実証する。

## 世界に存在する解法の包含監査

Babai の quasipolynomial SI/GI framework と corrected Split-or-Johnson、Luks 型 orbit/block/coset recursionを親問題レベルまで再監査している。large primitive barrierをJohnson structureとlocal certificates / Design Lemma / Split-or-Johnson / exact group-coset recursionへ落とす共有解法を優先し、J側では既存lower-arity relation image、paired-action preimage、block quotient、candidate SI、proof-carrying recurrenceを再利用する。

rev211はcanonical pair relationをそのままaction-image stringとして解くことで、第二Johnson coordinate gaugeの分岐を上位H6-C2から削除した。rev212はrev177のsigned profile solverとrev208 literal giant terminalを共有境界へ持ち上げ、同一Jリポジトリの未統合PR #128を実装上の既存案として確認した上で、最新rev211 treeへfail-closedに再構成した。PR #128はmerged progressや達成証拠には数えていない。rev213はLuks型orbit/block preimage、bounded auxiliary action、既存Johnson terminalをS1境界で再合成し、identity-only testが隠していたright-coset向きもnonidentity既知群次数で検証した。rev214は構造名をsolver分岐にする代わりに、informative relationのstrict action imageとexact preimageという共有解法へ持ち上げた。

CRX3では既存世界のcontent-addressed DAG/hash-consing、incremental computation、proof replayの考え方を、Babai/Luks型canonical certificateとSchreier generator pairingへ適用できるかを検討する。ただしbuild-cacheの一致を数学的証明と同一視せず、Jではproof identity、orientation、progress、resource chargeの機械的replayを必須にする。世界に存在する解法の包含確認は細部だけでなくH6-C2、W1R-H6、AGI rootの各親層で継続し、親から不要になった分岐だけを削除する。

## 認定状態

AGI 状態は **NOT_AGI**。full W1R-H6 closure、corrected Split-or-Johnson recursion 全体、global quasipolynomial recurrence、一般性・性能・自律性・実用提供の独立した厳格な実証は未完了であり、認定しない。

スケジューラ制御はリポジトリ成果とは別の外部 control plane である。実行履歴の存在だけを根拠にスケジュールが有効だと捏造しない。各 invocation は監視だけで終わらせず、未解決末端または共有統合を必ず具体的に試行する。
