# J main line

J の正本・主系列は **AGI-GI rev系列** とする。

この系列は `automation_runs/2026-08-19_0851_JST/AGI_GI_REV_SERIES.md` に定義された、rev91 から継続する graph alignment / symmetry / graph isomorphism / permutation-group / canonical-labeling 系である。

現在の継続点は **rev145**。rev139 で既存世界解の包含監査を行い、一般 nonregular primitive/coherent obstruction を Babai 型 recurrence と独立 differential-oracle 問題へ再編。rev140〜rev143 で独立 `labelg` differential oracle を実 CI まで検証して B1 を解決し、rev144 で B2 を B2.1〜B2.4 に分解して、canonicality・strict measure decrease・branch bound・complexity charge を fail-closed に検査する局所 recurrence contract を実装した。

rev145 では B2.2 を直接進めた。Babai 原論文の既存世界解は、負の local certificates を canonical な k-ary relation に集約し Design Lemma / Split-or-Johnson へ渡す構成である。J の同じ AGI-GI rev 系列には rev115-116 の exact fullness/non-fullness relation と canonical incidence refinement が既に存在するため、それを再利用して `local_certificate_recurrence_adapter_v1.py` を実装した。certified significant split の場合だけ partition cell-size multiset を rev144 contract に接続し、no-split・resource-limit は fail-closed のまま残す。PR #18 の workflow run 32250857762 / run #27 で既存 master integration、rev144 contract＋rev145 adapter tests、実 labelg gate の全 step success を観測した。B2.2 は構造的 recurrence plumbing として解決済み。ただし rev115-116 は exact global string stabilizer を使うため、Babai の quasipolynomial local-certificates complexity を実装済みとは扱わず、これは B2.4 に残す。

予測問題数は **512**、現在の有効問題数は **508** で予測超過なし。次の未解決末端は **B2.3: verified canonical partition から、isomorphism を失ったり捏造したりしない正しい subgroup/coset transport を伴う child recurrence を構成する**。B2.4 は global quasipolynomial accounting と fail-closed certification。

AGI 状態は **NOT_AGI** のまま。

以後、J の主進捗・CURRENT_STATUS・次の未解決末端はこの系列を基準に更新する。別系統の AGI 評価基盤・custodian/federation 系は、明示的に再指定されない限り J の main line として扱わない。
