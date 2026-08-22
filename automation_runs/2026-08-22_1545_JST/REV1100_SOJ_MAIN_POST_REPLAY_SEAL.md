# rev1100 — corrected-SOJ recursive production main/post-replay seal

Scope: `w1r-h6/corrected-split-or-johnson/larger-ground-recursive-production-main-post-replay-seal`.

This revision adds one file-disjoint downstream compatibility seal between two independently owned public contracts:

1. a replay-verified rev700 recursive-production provenance join, which already carries the rev600 main-provenance anchor and the rev500 caller replay identity; and
2. a replay-verified rev1000 post-replay cost/coherence envelope, which already joins the production-cost provenance and provenance/total-cost views.

The seal does not import either sibling branch implementation. It independently replays the compact rev700 production-provenance identity, requires explicit upstream replay gates for noncompact semantics, validates the strict rev1000 public shape, preserves exact-empty versus nonempty outcomes, rechecks strict recursive shrink and the exact power-of-two/log2 cost relation, and requires one shared reduction identity plus one shared `production_provenance_identity`.

The output carries the rev700 `main_commit_sha`, `main_provenance_identity`, caller-binding/replay identities, the rev1000 reduction/cost tuple, and the rev1000 envelope identity into a new deterministic SHA-256 seal identity.

Strict boundary: this is not a Git reachability verifier, recursive String-Isomorphism executor, Johnson reduction constructor, recurrence proof, production caller, merge-state oracle, or AGI/GI completion claim. The rev700 and rev1000 owners remain responsible for their own replay routines before setting the explicit replay gates. Identity agreement certifies only the declared cross-certificate compatibility tuple.

Parallel boundary: rev1000, rev900, rev800, rev720, rev700, rev650, rev600, rev500, rev400, CRX work, shared proof-DAG/recurrence/coordination code, sibling branches, PRs, claims, and workflows remain read-only and untouched. The later rev1200/rev1300/rev1400 corrected-SOJ scopes and the independent homogeneous-block quotient/proof-DAG lanes explicitly exclude rev1100 reserved paths.

Canonical-main hardening reconciliation:

- PR #259 merged the canonical-main-source hardening after the original rev1100 evidence was generated.
- The original attempt/publish evidence used branch commit `544ad9b5dc06236f29eff2ab4e2154c7a1aa656d` as `registry_source_sha`; that commit is not on canonical main ancestry after the hardening and therefore must not be reused for publication.
- This replacement branch starts directly from hardened main `4bb4d3799d702115eb652db8484c4317f8cf2d75` and deliberately carries no pre-hardening phase evidence.
- The dedicated workflow must generate fresh `attempt_solution` and `publish` evidence using the hardened merge-base rule before repository-wide admission can be treated as green.
- The mathematical implementation and 15 focused fail-closed regressions are unchanged from the previously green rev1100 code; only the coordination base/evidence lifecycle is being repaired.

Integration boundary: rev700 / PR #251 and rev1000 / PR #256 are still independently owned, draft, and unmerged. Even after fresh hardened phase evidence is green, rev1100 remains draft until those producer contracts stabilize on main.
