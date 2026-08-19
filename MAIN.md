# J main line

J の正本・主系列は **AGI-GI rev系列** とする。

この系列は `automation_runs/2026-08-19_0851_JST/AGI_GI_REV_SERIES.md` に定義された、rev91 から継続する graph alignment / symmetry / graph isomorphism / permutation-group / canonical-labeling 系である。

現在の継続点は **rev146**。rev140〜rev143 で独立 `labelg` differential oracle を実 CI まで検証して B1 を解決。rev144 で B2 を B2.1〜B2.4 に分解し、canonicality・strict measure decrease・branch bound・complexity charge を fail-closed に検査する局所 recurrence contract を実装した。rev145 では rev115-116 の exact local fullness relation / canonical incidence refinement を再利用し、significant canonical split のみを recurrence contract に接続して B2.2 を構造的に解決した。

rev146 では B2.3 を直接試行したが、rev145 は partition の縮小量だけを持ち、元 ambient group からその partition を保存・移送する exact subgroup/coset を構成していなかった。このまま child recursion を行うと isomorphism を失う/捏造する危険があるため、B2.3 を B2.3a〜B2.3d に分解した。B2.3a として `canonical_partition_transporter_v1.py` を実装し、ordered canonical quotient partition の orbit を ambient group で厳密に探索しながら full-domain transporter を記録し、Schreier generators により各 source cell を setwise に保存する exact preimage stabilizer を返す。shape mismatch・target unreachable・state budget 超過は fail-closed。PR #19 の workflow run 32251164264 / run #33 で S4 stabilizer/transporter、block renumbering invariance、resource-limit failure を含むテストと既存 gates がすべて success となった。

予測問題数は **512**。B2.3 を4子問題へ分解したため現在の有効問題数は **512** で予測値と一致し、超過なし。B2.3a は解決済み。次の未解決末端は **B2.3b: source/target の canonical local-certificate partitions を二つの strings から構成し、それらを対応させる exact G-coset を導出する**。B2.3c は reduced cells/cosets 上の recursion 実行、B2.3d は child coset/result の合成と end-to-end relabeling invariance。B2.4 は global quasipolynomial accounting と fail-closed certification。

rev115-116 の local relation と rev146 の partition-orbit search は exact だが指数的になり得る。したがって Babai の quasipolynomial complexity を達成済みとは扱わず、その証明・実装は B2.4 に残す。

AGI 状態は **NOT_AGI** のまま。

以後、J の主進捗・CURRENT_STATUS・次の未解決末端はこの系列を基準に更新する。別系統の AGI 評価基盤・custodian/federation 系は、明示的に再指定されない限り J の main line として扱わない。
