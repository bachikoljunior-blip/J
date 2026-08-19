# J main line

J の正本・主系列は **AGI-GI rev系列** とする。

この系列は `automation_runs/2026-08-19_0851_JST/AGI_GI_REV_SERIES.md` に定義された、rev91 から継続する graph alignment / symmetry / graph isomorphism / permutation-group / canonical-labeling 系である。

現在の継続点は **rev144**。rev139 で既存世界解の包含監査を行い、一般 nonregular primitive/coherent obstruction を Babai 型 recurrence と独立 differential-oracle 問題へ再編。rev140〜rev143 で candidate 実装に依存しない graph6 interchange、nauty `labelg` fail-closed adapter、no-skip differential suite、高対称 adversarial families、実 nauty CI gate を整備し、workflow run 32249609772 / run #17 の実行で oracle install・既存 master integration・labelg differential gate の全 step success を観測・永続化したため B1 は解決済み。

rev144 では次の B2 を直接試行した。既存 `primitive_orbital_relation_unresolved` は finer orbital/design structure が必要という fail-closed 状態を返すが、再帰 child の canonicality、strict measure decrease、branch bound、complexity charge を機械検証する契約を持たない。そこで B2 を B2.1〜B2.4 に分解し、B2.1 として `babai_recurrence_contract_v1.py` を実装。非 canonical step、非縮小 child、不正 partition、branch budget 超過をすべて fail-closed にし、正当な local recurrence step のみ progress verified とするテストを追加し、AGI-GI CI に組み込んだ。これは局所契約であり Babai の quasipolynomial theorem 実装を主張しない。

予測問題数は **512**。B2 を4子問題へ分解したため現在の有効問題数は **508** で予測超過なし。次の未解決末端は **B2.2: unresolved primitive/coherent branch から恣意的 orbital naming を使わず label-invariant local certificates を抽出し、その canonical partition を rev144 contract へ入力する**。B2.3 は canonical child recurrence、B2.4 は global quasipolynomial accounting と fail-closed certification。

AGI 状態は **NOT_AGI** のまま。

以後、J の主進捗・CURRENT_STATUS・次の未解決末端はこの系列を基準に更新する。別系統の AGI 評価基盤・custodian/federation 系は、明示的に再指定されない限り J の main line として扱わない。
