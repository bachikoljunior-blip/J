# J main line

J の正本・主系列は **AGI-GI rev系列** とする。

この系列は `automation_runs/2026-08-19_0851_JST/AGI_GI_REV_SERIES.md` に定義された、rev91 から継続する graph alignment / symmetry / graph isomorphism / permutation-group / canonical-labeling 系である。

現在の継続点は **rev178**。rev140〜143 で独立 `labelg` differential oracle を実 CI まで検証して B1 を解決。rev144〜162 で canonical local-certificate partition、exact transporter/coset、quotient/kernel、affected/unaffected、growing-beard、fail-closed quasipolynomial accounting を proof-carrying SI substrate へ統合した。rev163〜168 では small/polylog terminal・intransitive recursion・imprimitive quotient/kernel の重複を横断整理し、予測問題数 512 を超えない形で **V1 [resolved substrate] + V2 [remaining transitive closure]** へ再編した。

rev169〜174 では Schreier-certified image/order を基準に exact generator-BFS terminal、candidate-fiber recursion、unique-canonical-imprimitive closure、primitive Johnson small-ground terminals を追加。rev175 は J(v,k) domain から strictly smaller な Johnson ground relation へ進む exact interface を追加し、ambient generator を ground permutation + v=2k complement bit へ decode / re-induce して fail-closed に検証した。rev176 は bounded signed-ground group を完全列挙する exact SI terminal、rev177 は represented group 自体を列挙せず point star/anti-star profile partition orbit だけを Schreier 探索する exact/filter terminalを追加した。

rev178 は **W1R: higher-order signed-ground relational closure** を直接試行した。actual colored k-subset relation から各 unordered ground pair について、intersection size 0/1/2 ごとの exact color histogram を作る。v=2k complement が signed image に存在する場合は 0/2 histogram を unordered に保持するため complement parity に不変である。この canonical pair relation を coherent refinement に掛け、significant diagonal split が得られれば original-domain generator を保持した signed partition orbit から exact candidate transporter coset を再構成する。K3 ⊔ C5 on J(8,2) では全 ground point の first-order star profile が同一でも second-order relation が 3/5 ground split を復元した。C9 on J(9,2) のように diagonal fiber が homogeneous のままでも、nontrivial pair relation 自体を original Johnson domain 36 より小さい 9-point ground 上の明示 recurrence target として保持する。

さらに rev178 では represented signed group elements ではなく **distinct canonical pair-relation images** の orbit を bounded Schreier 探索する proof-carrying terminal を追加した。k=2 かつ complement なしでは pair signature の intersection-2 成分が各 2-subset の実 color を保持するため、pair relation equality が元 string equality を決定する。full S9 acting on J(9,2) の represented order 362880 に対して C9 relation orbit は 20160 states、復元 stabilizer order は18となり、group enumeration より小さい relational orbit だけで exact SI right coset を閉じた。state cap 100 の regression は exact/cost claim を行わず fail closed になる。PR #51 の workflow run 32282814320 / run #313 で rev178 fast tests **5 passed**、integrated recurrence/master suite **116 passed**、real `nauty-labelg` differential gate **2 passed** を確認して main へ統合した。

予測問題数はすでに **512**、rev177 時点の有効問題数も **512** だった。rev178 の pair split / relation recurrence / bounded relation-orbit terminal / residual higher-order caseを別 child として追加すれば予測超過するため、これらの解決済み経路は W1R の内部 fast path として吸収し、active leaf 自体を **W1R-H** へ in-place 置換した。再予測は **512 / 512** のまま。次の未解決末端は **W1R-H: k>=3 など pair relation が full k-subset string を決めない場合、または relation orbit が cap を超える場合に、smaller Johnson ground 上で logarithmic-size local certificates / higher-arity canonical relation を集約して significant split または structural recurrence を作り、その proof-carrying image SI coset を signed-ground homomorphismの exact preimageとして元 J(v,k) domainへ戻す**。

AGI 状態は **NOT_AGI** のまま。AGI 達成、一般性、性能、自律性、実用提供、または full Babai-style quasipolynomial closure は未認定であり、未確認の成果を達成済みとは扱わない。

以後、J の主進捗・CURRENT_STATUS・次の未解決末端はこの系列を基準に更新する。別系統の AGI 評価基盤・custodian/federation 系は、明示的に再指定されない限り J の main line として扱わない。
