# J main line

J の正本・主系列は **AGI-GI rev 系列** とする。ルート問題は、達成基準を下げず、研究試作で終わらせず、厳格な一般性・性能・自律性を実証し、実際に使える形で AGI を提供することである。問題解決機構そのものを AGI と同一視しない。

系列の実装・検証記録は `automation_runs/2026-08-19_0851_JST/`、実行開始履歴は append-only の `agi/run-history/STARTS.jsonl`、運用境界は `automation/CHATGPT_SCHEDULED_TASK_RUNBOOK.md` を正本とする。

## 現在の継続点

現在の統合済み継続点は **AGI-GI rev218**。rev206 までに corrected general UPCC Bipartite Split-or-Johnson の exact theorem-input / restriction provenance / Design witness cover / ambient transporter / actual coupled parent full-string intersection と complete branch-union reconstructionを統合し、rev207 で exact rev206 branch の実 candidate SI accounting を polynomial auxiliary-degree lift として original root の quasipolynomial envelopeへ機械的に戻した。

rev208 は active leaf **H6-C2** の literal natural-domain giant subleafを解決した。represented subgroup が degree `n>=5` で order `n!` または `n!/2` なら、その action 自体が literal `S_n` / `A_n` なので、色クラス間の exact transporter と target-color stabilizerから full String-Isomorphism right cosetを直接復元する。

rev209 は larger Johnson candidate を既存 rev184 logarithmic certificate / Design descentへ接続し、candidate全体が full stringをtransportする場合のexact acceptanceと、canonical relation filterからの継続を追加した。構造証拠だけのpathはexact SIと誤認せずfail closedのまま残した。

rev210 は explicit `canonical_imprimitive_family` subleafを解決した。複数の equally minimum invariant block systemから数値ラベルで1個を選ばず、family全体のquotient/preimage SIをpolynomial gate内で解き、全再構成結果が同一right cosetである場合だけ受理する。recurrence verifier v4はsame-domain quotient fiberについてexact terminalまたはstrict smaller kernel-orbit progressだけを許す。

rev211 は rev184 の second-Johnson structural residualを、第二groundの任意座標を選ばず解決した。既にcanonicalなcodegree pair relationそのものをinduced action上のstringとしてexactに解き、generator-paired Schreier preimageでoriginal Johnson domainへ戻し、full stringをexact filter内で解く。さらに `J(2m+1,m)` のcomplement pairがcanonical blockとなるためclassifierがimprimitiveを返す場合も、bridge自身のJohnson relation証明を必須として試行できるよう修復した。identity candidateには不要なtranslation wrapperを付けず証明status契約を保つ。

rev212 は既存rev177のcomplement-safe signed Johnson ground-profile SIを、transitive candidate境界とintransitive orbitのS1 child境界へ再接続した。profile invariant mismatchはexact empty、profile-determined relationはexact right cosetとして閉じ、rev208 literal giant terminalもS1 childで再利用する。significant partitionがfilterだけを与える場合、partition orbit cap、recognition failure、非profile-determined residualは未確認のexact解とせずfail closedを維持する。

rev213 はその significant-profile filter を nested orbit depth で実用化した。S1 v4がnewest exact terminalsを自己再帰でも保持し、bounded Johnson-ground terminalをprofile no-splitより先に再利用し、explicit/polylog auxiliary window内のtransitive imprimitive childを既存candidate block/family dispatcherへ戻す。さらにrev177のsource partition stabilizerをrepositoryのright-coset規約に必要なtarget stabilizerへ共役し、nonidentity transporterで隠れていたcoset completenessとodd-witness compositionを修復した。上限外のground/quotient、recognition・partition resource overflowはfail closedのままである。

rev213 proposed head `99e3fee47b50da06ddd1759042d14c3b9e9e753a` は AGI-GI rev validation run `32350556780`（independent `nauty-labelg` differential gateを含む）、rev213 smoke `32350556943`、rev212 smoke `32350556946`、rev211 smoke `32350556857`、rev210 smoke `32350556734`、rev209 smoke `32350556754`、rev208 smoke `32350556751` がすべて success。PR #141 をmergeし、main commit `be165ab362127e81a8272bc470191606948e5e3c` に統合済み。

rev214 は rev184 が nonconstant homogeneous pair relationへ到達した後の不要なJohnson-only gateを除いた。`C(v,2)<C(v,k)` のstrict pair imageをexact SIとして解き、generator-paired Schreier preimageでoriginal candidateへ戻してfull stringをproper filter内で解く。homogeneous/nonshrinking/resource-capped imageはfail closed、preimageがambient candidateと同一ならwhole-candidate exact terminal以外をsame-domain self-loopとして拒否する。`J(9,3)` 上のcyclic-triple regressionではbounded ground外、uniform point profile、non-Johnson pair relationからtarget stabilizer order 9のexact right cosetを復元し、既知nonidentity transporterとrecurrence v4を検証した。

rev214 tested head `2b1852c88f33a85aeaddaa2bc488353d7021a2fc` は AGI-GI rev validation run `32357682162`（independent `nauty-labelg` differential gateを含む）、rev214 smoke `32357682062`、rev213 smoke `32357682097`、rev212 smoke `32357682143`、rev211 smoke `32357682073`、rev210 smoke `32357682141`、rev209 smoke `32357682065`、rev208 smoke `32357682129` がすべて success。先行run `32355898849` は主検証成功後に20分上限でoracle導入中cancelとなり証拠に数えず、実測に基づき30分へ修正して全gateを再実行した。PR #142 をmergeし、main commit `e7b190ae5de9a2ceb4238145a337daa4b7b1f5a0` に統合済み。

rev215 は rev209、rev214、signed profile terminalが重複実行するJohnson recognition/ground liftを、replay-stableなimmutable proof artifactとして共有した。完全なfrozen stabilizer chain、exact source/target string、全recognition resource gateをidentityとする64-entry bounded LRUであり、可変・非hashable colorはbypassする。resource gate違いは別identity、fail-closed resultはfail-closedのまま、cache hitでもrecognition-node chargeを保守的に保持する。content cacheを数学証明と同一視せず、proof inputと不変性を回帰で検証する。

rev215 tested head `f1d5a43b89b8ff4ce2d092fd6f2abde5c3bffacb` は AGI-GI rev validation run `32361083236`（independent `nauty-labelg` differential gateを含む）、rev215 smoke `32361083278`、rev214 smoke `32361083374`、rev213 smoke `32361083234`、rev212 smoke `32361083247` がすべて success。rev215 smokeはrev211--rev215の統合経路を含む。PR #143 をmergeし、main commit `f04f465cc14a353d12df446b72fff7c05ab79bee` に統合済み。

rev216 は certified Johnson lift から logarithmic arity/test gate、complement-safe relation、canonical codegree descent、terminal pair relationまでを一つのimmutable proof artifactへ因数分解し、rev184とrev214で共有した。完全なliftとsource/target orientation、root/test/recognition/Johnson resource gate、`max_class_fraction`をidentityに含む64-entry bounded LRUであり、unhashable inputはbypassし、cache hitでも同じ保守的work chargeとfail-closed statusを保つ。rev214の重複relation replayは削除した。

全Python module検証でrev215 baselineにも再現するcoherent 2-WL round-limit residualを発見し、transient integer color IDではなく誘導partitionのrank安定で終了を判定するよう修復した。各signatureが旧colorを含むためrefinementは単調で、同rankならpartition安定である。6点weighted relationは全`6!`置換の独立列挙でautomorphism orbits `{0}`, `{1,3}`, `{2}`, `{4}`, `{5}`、group order 2を確認し、stable 2-WLの出力と一致させた。

rev216 tested head `dc802bcd6449e56880ab87ae16479491ae8d0270` は AGI-GI rev validation run `32366109009`（independent `nauty-labelg` differential gateを含む）、rev216 smoke `32366109051`、rev215 smoke `32366109019`、rev214 smoke `32366109092`、rev213 smoke `32366109034`、rev212 smoke `32366109032`、rev211 smoke `32366108991` がすべて success。local all-module gateは外部labelg専用fileを除き438 tests success。PR #144 をexact tested head固定でmergeし、main commit `61762692ee32e34b05bac9e9174fc19f0f14c0a8` に統合済み。

rev217 は CRX3 子3の paired-action preimage / full-candidate filterを、一つのimmutable replay artifactへ統合した。exact image right cosetとgenerator-paired actionからkernelを含むfull preimageを構成し、128-entry preimage cacheと64-entry full-artifact cacheで共有する。proof identityはfrozen domain group、順序付きimage generators、向き付きimage right coset、full source/target string、root、dispatcher identity、正規化した全resource引数を含む。unhashable inputはcacheをbypassし、mutable inputはartifact生成時のsnapshotから切り離す。

ambient-equal/nonrestricting preimageとsame-domain self-loopは、whole-candidate exact terminalでfull stringを解ける場合を除いて拒否する。resource-capped/unresolved childをexact化せず、relation-image、joint-relation、lower-arity relation、log-codegreeの各consumerが同じbuilderを使用する。log-codegree内の重複preimage/candidate/accounting blockは削除し、recurrence verifier v4をartifact境界で検証する。

rev217 tested head `26bc3d0c92e77638756eb9e75f068c0050dd26ed` は AGI-GI rev validation run `32369585203`（independent `nauty-labelg` differential gateを含む）、rev217 smoke `32369585064`、rev216 smoke `32369585018`、rev215 smoke `32369584974`、rev214 smoke `32369584952`、rev213 smoke `32369584975`、rev212 smoke `32369585172`、rev211 smoke `32369584935` がすべて success。local all-module gateは外部labelg専用fileを除き442 tests success。PR #145 をexact tested head固定でmergeし、main commit `ea52522f3e979c8a86844aa32426bf01a2436983` に統合済み。

rev218 は rev206 branch executionとrev207 polynomial-lift accountingの対応を実行連結にした。従来はrev206がcandidate SIを実行した後、rev207の`_trace_exact_image_proof`が同じsolverを再実行してproof treeを回収し、実work二回に対して一回分のchild chargeだけを合成していた。各`BipartiteParentActionCosetIntersection`が実際に返されたfrozen `ProofCarryingCoset`を保持し、rev207は同じobject identityを直接検証する。proof欠落・nonexact・status不一致は再構築せずfail closedとし、重複solver pathを削除した。

rev218 tested head `fddc8b99d4906aee73798451edde9a2e836be4df` は AGI-GI rev validation run `32372522074`（independent `nauty-labelg` differential gateを含む）、rev218 smoke `32372522346`、rev217 `32372522011`、rev216 `32372521926`、rev215 `32372522421`、rev214 `32372521954`、rev213 `32372522230`、rev212 `32372521978`、rev211 `32372521985`、rev210 `32372522309`、rev209 `32372521944`、rev208 `32372522157`、rev207 `32372522510`、rev206 `32372522181` がすべて success。local all-module gateは外部labelg専用fileを除き445 tests success。PR #146 をexact tested head固定でmergeし、main commit `2638c9df046931aec55de7e900a2abee2522f21c` に統合済み。

## 問題木

予測問題数は **576**、置換済み旧問題を除く有効問題数は **517**。旧予測/実数512/512の末端を直接試行し、解決したgeneric strict-pair subcaseと未解決5子問題へ分解した時点で実数は一時的に517となり、旧予測512を実際に超えた。この超過を事前抑制せず、mandatory full-tree rewrite triggerを発火させた。

置換済み旧問題を除く全層――primitive relation、H6-C2、W1R-H6 corrected Split-or-Johnson/Design branch、global proof-carrying recurrence/resource、AGI rootの一般性・性能・自律性・実用提供――を横断し、7本の狭いrelation/filter/cap branchを三つのsolution-shaped problemへ書き換えた。**CRX1 exact canonical relation quotient/preimage closure**、**CRX2 information/symmetry-defect relation selection**、**CRX3 replay-stable proof/resource substrate**であり、単なる重複名の統合ではなく上位親から共有できる解法境界である。結果は `517 - 7 + 3 = 513`、再予測576。rev214はCRX1のnonconstant strict-pair subcaseとCRX3のhomogeneous/self-loop guardsだけを解決した。

rev215の直接試行でCRX3末端を四子へ分解した: (1) replay-stable Johnson recognition/ground-lift identity、(2) shared log relation/codegree descent artifact、(3) shared paired-action preimage/full-candidate filter artifact、(4) rev207/nested S1を跨ぐproof-DAG accounting identity。1を解決し、旧1末端を解決済み1子と未解決3子に置換したため有効数は `513 - 1 + 4 = 516`。516は予測576以下なので新しいover-count rewrite triggerは発火していない。

rev216はCRX3子2を解決した。さらに既存CRX2 local-certificate/Design-escalation末端を、(a) stable coherent-refinement terminationと(b)残るDesign escalationへ分解し、(a)を解決した。1末端を2子へ置換したため有効数は `516 - 1 + 2 = 517`。517は予測576以下なので新しいover-count rewrite triggerは発火していない。

rev217はCRX3子3を解決した。既に数えていた末端の状態を未解決から解決済みへ更新したため、有効問題数は517、予測問題数は576のままである。実数517は予測576以下なので、このrunでも新しいover-count rewrite triggerは発火していない。

rev218の直接試行でCRX3子4に、rev207が実行済みcandidate SIを再実行して費用対応を失う具体的境界を発見した。子4を、(4.1) execution-linked rev206/rev207 proof capture、(4.2) nested S1 mathematical identity、(4.3) shared proof-DAG conservative cost verifierの三子へ分解し、4.1を解決した。1末端を3子へ置換したため有効数は `517 - 1 + 3 = 519`。519は予測576以下なので新しいover-count rewrite triggerは発火しておらず、子を抑制していない。

CRX1の`k<=2`、homogeneous/nonrestricting relation image、node/resource-capped image SI、CRX2の残るcanonical local-certificate/Design escalation、CRX3の残る子4.2・子4.3、corrected Split-or-Johnson残部、W1R-H6 parent、AGI rootは未解決のままである。

次の未解決末端は **CRX3 / proof-DAG accounting / nested S1 mathematical identity**:

> S1 v4とcandidate u7を跨ぐ各再帰結果に、完全なSchreier chain、right-coset coordinate shift後の向き付きlocal source/target、original root/current domain/depth、dispatcher version、明示・固定defaultを含む全resource gateのimmutable identityを付ける。root identityをinduced orbit childへ流用せず、one-shot/mutable inputをsnapshotし、opaqueでprocess-stable identityを作れない値はDAG reuseをfail closedにする。identity一致をSI exactnessやcost証明とは同一視せず、次子の独立DAG verifierへ渡せるexecution-linked artifactとして検証する。

## 世界に存在する解法の包含監査

Babai の quasipolynomial SI/GI framework と corrected Split-or-Johnson、Luks 型 orbit/block/coset recursionを親問題レベルまで再監査している。large primitive barrierをJohnson structureとlocal certificates / Design Lemma / Split-or-Johnson / exact group-coset recursionへ落とす共有解法を優先し、J側では既存lower-arity relation image、paired-action preimage、block quotient、candidate SI、proof-carrying recurrenceを再利用する。

rev211はcanonical pair relationをそのままaction-image stringとして解くことで、第二Johnson coordinate gaugeの分岐を上位H6-C2から削除した。rev212はrev177のsigned profile solverとrev208 literal giant terminalを共有境界へ持ち上げ、同一Jリポジトリの未統合PR #128を実装上の既存案として確認した上で、最新rev211 treeへfail-closedに再構成した。PR #128はmerged progressや達成証拠には数えていない。rev213はLuks型orbit/block preimage、bounded auxiliary action、既存Johnson terminalをS1境界で再合成し、identity-only testが隠していたright-coset向きもnonidentity既知群次数で検証した。rev214は構造名をsolver分岐にする代わりに、informative relationのstrict action imageとexact preimageという共有解法へ持ち上げた。

CRX3では既存世界のcontent-addressed DAG/hash-consing、incremental computation、proof replayの考え方を、Babai/Luks型canonical certificateとSchreier generator pairingへ適用する。rev215--rev216はPythonのbounded LRUとBazel型action-hash/content-addressed分離を参考にしたが、build-cacheの一致を数学的証明と同一視せず、Jでは完全なproof identity、不変artifact、orientation、progress、resource chargeの機械的replayを必須にした。coherent refinementにはstandard WLのpartition-stability終了則を適用した。rev217では、GAPのgroup-homomorphismがkernelとsubgroup/cosetのcomplete preimageを扱う既存方式を、Jのgenerator-paired Schreier proofとして共有し、四つのcandidate consumerへ接続した。rev218はincremental buildのaction-key/result separationをexecution/accounting境界へ適用し、実行時proof objectを直接捕捉してdeterministic replayによる実work二重化を削除した。次のproof-DAG accounting子では、content-addressed DAG/hash-consing、incremental buildのaction identity、amortized/potential accountingを包含候補として使う。ただし同一cache keyを数学的同一性や計算量証明と同一視せず、完全なproof identity、original-rootへのlift、worst-case chargeを独立にreplayする。同じ境界をH6-C2、W1R-H6、AGI rootの各親層まで継続し、親から不要になった分岐だけを削除する。

## 認定状態

AGI 状態は **NOT_AGI**。full W1R-H6 closure、corrected Split-or-Johnson recursion 全体、global quasipolynomial recurrence、一般性・性能・自律性・実用提供の独立した厳格な実証は未完了であり、認定しない。

スケジューラ制御はリポジトリ成果とは別の外部 control plane である。実行履歴の存在だけを根拠にスケジュールが有効だと捏造しない。各 invocation は監視だけで終わらせず、未解決末端または共有統合を必ず具体的に試行する。
