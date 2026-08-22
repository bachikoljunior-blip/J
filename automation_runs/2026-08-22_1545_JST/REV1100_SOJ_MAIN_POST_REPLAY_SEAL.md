# rev1100 — corrected-SOJ recursive production main/post-replay seal

Scope: `w1r-h6/corrected-split-or-johnson/larger-ground-recursive-production-main-post-replay-seal`.

This revision adds one file-disjoint downstream compatibility seal between two independently owned public contracts:

1. a replay-verified rev700 recursive-production provenance join, which already carries the rev600 main-provenance anchor and the rev500 caller replay identity; and
2. a replay-verified rev1000 post-replay cost/coherence envelope, which already joins the production-cost provenance and provenance/total-cost views.

The seal does not import either sibling branch implementation. It independently replays the compact rev700 production-provenance identity, requires explicit upstream replay gates for noncompact semantics, validates the strict rev1000 public shape, preserves exact-empty versus nonempty outcomes, rechecks strict recursive shrink and the exact power-of-two/log2 cost relation, and requires one shared reduction identity plus one shared `production_provenance_identity`.

The output carries the rev700 `main_commit_sha`, `main_provenance_identity`, caller-binding/replay identities, the rev1000 reduction/cost tuple, and the rev1000 envelope identity into a new deterministic SHA-256 seal identity.

Strict boundary: this is not a Git reachability verifier, recursive String-Isomorphism executor, Johnson reduction constructor, recurrence proof, production caller, merge-state oracle, or AGI/GI completion claim. The rev700 and rev1000 owners remain responsible for their own replay routines before setting the explicit replay gates. Identity agreement certifies only the declared cross-certificate compatibility tuple.

Parallel boundary: rev950 `MAIN.md` synchronization, rev1000, rev900, rev800, rev720, rev700, rev650, rev600, rev500, rev400, CRX work, shared proof-DAG/recurrence/coordination code, sibling branches, PRs, claims, and workflows remain read-only and untouched.
