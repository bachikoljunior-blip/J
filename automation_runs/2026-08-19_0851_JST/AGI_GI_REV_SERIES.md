# AGI-GI rev系列

この系列名は **AGI-GI rev系列** とする。

対象は、rev91 から継続された graph alignment / symmetry / graph isomorphism / permutation-group / canonical-labeling 系の問題木と成果物である。別系統の AGI 評価基盤・外部 custodian/federation 問題はこの系列の進捗として混同しない。

## 継続基準点

- rev92: total disagreement assignment lower bound。古典的な Hungarian/Munkres 系の線形割当を独立 oracle 候補として包含する。
- rev93–rev102: anchorless / symmetry / Weisfeiler–Leman / orbit / IR / tree canonical paths。
- rev104–rev107: Schreier/permutation-group and state-orbit transporter foundations。GAP 等の Schreier–Sims 系を独立検証先として包含する。
- rev108: product-action right-coset intersection。
- rev140: fail-closed external canonical-label oracle adapter。graph6 境界、外部 oracle 応答、canonical result 生成を fail closed にした。
- rev141–rev143: executable `labelg` differential audit を導入し、実 nauty `labelg` backend を用いた adversarial/relabeling differential test と CI を通して B1 を解決した。rev140 時点で未達だった実 backend 検証はここで満たされた。
- rev144–rev168: canonical local-certificate partition、exact transporter/coset、quotient/kernel、affected/unaffected、growing-beard、fail-closed quasipolynomial accounting を proof-carrying SI substrate へ統合した。
- rev169–rev177: candidate-fiber recursion、imprimitive closure、Johnson small-ground / relational lift / signed-ground terminals、point-profile partition orbit を追加した。
- rev178–rev183: W1R Johnson hard branch。actual colored k-subset relation から complement-safe lower-arity relationを構成し、smaller relation image SI、exact image-to-original preimage、adaptive arity selection、複数 relation の joint image closureを実装した。
- rev184: W1R-H5 logarithmic certificate Design-Lemma descent。認識済み Johnson ground 上で logarithmic complement-safe relation、incidence refinement、lower-codegree descent、significant split、candidate-coset continuationを proof-carrying に接続した。lower-codegree homogeneous design は未解決として残した。
- rev185: exact colored-subset symmetry-defect gate。complete colored t-subset relation の全 transposition を直接検査して twin classes / maximal symmetric subset certificate を得る exact gate を追加した。full individualization/WL Design Lemma および full W1R closure は未認定。

## 現在の継続点

現在の確定継続点は **rev185**。

予測問題数は **512**、有効問題数も **512**。上限に達しているため rev184・rev185 を別 active child として追加せず、W1R-H5 の共有 substrate として内部化し、active leaf を in-place で **W1R-H6** に置換する。

次の未解決末端は **W1R-H6**: rev184 が返す lower-codegree homogeneous logarithmic relationへ rev185 の exact symmetry-defect certificateを proof-carrying に接続する。defect gateが成立する場合、canonical logarithmic individualization/test family と bounded WL/local-certificate refinementを実行し、label-invariant significant split、certified Johnson descent、または exact candidate cosetへ落とす。theorem hypotheses、source/target comparability、exactness、strict progress、quasipolynomial recurrence accountingを満たせない経路は fail closed とする。

canonical-labeling の独立 differential oracle として nauty/Traces `labelg` を実検証済み経路に含め、bliss 等の独立実装も追加 oracle 候補として扱う。一般 GI/SI/Coset Intersection の残る最悪時経路は、Babai-style local certificates / canonical partitioning / Design-Lemma descent と整合する形へ寄せるが、未実装の theorem boundary を実装済み・解決済みとは扱わない。

AGI の状態は厳格に **NOT_AGI** のままとする。この系列の個別アルゴリズム成果を AGI 達成証拠として扱わない。AGI 達成、一般性、性能、自律性、実用提供、または full Babai-style quasipolynomial closure は未認定である。
