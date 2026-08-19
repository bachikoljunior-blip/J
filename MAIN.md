# J main line

J の正本・主系列は **AGI-GI rev系列** とする。

この系列は `automation_runs/2026-08-19_0851_JST/AGI_GI_REV_SERIES.md` に定義された、rev91 から継続する graph alignment / symmetry / graph isomorphism / permutation-group / canonical-labeling 系である。

現在の継続点は **rev143**。rev139 で既存世界解の包含監査を行い、一般 nonregular primitive/coherent obstruction を Babai 型 recurrence と独立 differential-oracle 問題へ再編。rev140〜rev142 で candidate 実装に依存しない graph6 interchange、nauty `labelg` fail-closed adapter、実在 adapter API へ接続した no-skip differential suite、Ubuntu の `nauty-labelg` 名対応、complete bipartite / paired cliques / hypercube を含む高対称 adversarial families、実 nauty を導入する CI gate を整備した。

rev143 では PR #17 の pull-request validation を実際に観測し、workflow run 32249609772 / run #17 の `validate-rev-series` job が success。`Install independent canonical oracle`、既存 master integration、`Run labelg-backed differential gate` の全 step が success だったことを永続化した。これにより B1a.3 と親 B1（独立 executable canonical-label differential oracle integration）は現行 audit boundary について解決済み。これは個別アルゴリズム基盤の検証であり AGI 証拠ではない。

予測問題数は **512**、現在の有効問題数は **504** で予測超過なし。次の未解決末端は **B2: 残る nonregular primitive/coherent branch に対して、Babai 型 local-certificate / canonical-partition recurrence の明示的 contract を実装し、各再帰で progress と complexity を fail-closed に証明可能にする**。

AGI 状態は **NOT_AGI** のまま。

以後、J の主進捗・CURRENT_STATUS・次の未解決末端はこの系列を基準に更新する。別系統の AGI 評価基盤・custodian/federation 系は、明示的に再指定されない限り J の main line として扱わない。
