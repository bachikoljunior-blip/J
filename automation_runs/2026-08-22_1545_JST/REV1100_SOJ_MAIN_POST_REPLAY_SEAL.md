# rev1100 — corrected-SOJ recursive production main/post-replay seal

Scope: `w1r-h6/corrected-split-or-johnson/larger-ground-recursive-production-main-post-replay-seal`.

This revision adds one file-disjoint downstream compatibility seal between two independently owned public contracts:

1. a replay-verified rev700 recursive-production provenance join, which already carries the rev600 main-provenance anchor and the rev500 caller replay identity; and
2. a replay-verified rev1000 post-replay cost/coherence envelope, which already joins the production-cost provenance and provenance/total-cost views.

The seal does not import either sibling branch implementation. It independently replays the compact rev700 production-provenance identity, requires explicit upstream replay gates for noncompact semantics, validates the strict rev1000 public shape, preserves exact-empty versus nonempty outcomes, rechecks strict recursive shrink and the exact power-of-two/log2 cost relation, and requires one shared reduction identity plus one shared `production_provenance_identity`.

The output carries the rev700 `main_commit_sha`, `main_provenance_identity`, caller-binding/replay identities, the rev1000 reduction/cost tuple, and the rev1000 envelope identity into a new deterministic SHA-256 seal identity.

Strict boundary: this is not a Git reachability verifier, recursive String-Isomorphism executor, Johnson reduction constructor, recurrence proof, production caller, merge-state oracle, or AGI/GI completion claim. The rev700 and rev1000 owners remain responsible for their own replay routines before setting the explicit replay gates. Identity agreement certifies only the declared cross-certificate compatibility tuple.

Parallel boundary: rev1000, rev900, rev800, rev720, rev700, rev650, rev600, rev500, rev400, CRX work, shared proof-DAG/recurrence/coordination code, sibling branches, PRs, claims, and workflows remain read-only and untouched. The rev950 `MAIN.md` synchronization completed independently. The later rev1200 lineage-closure claim explicitly excludes rev1100 and all rev1100 reserved paths, so the two scopes remain file-disjoint.

Validation record:

- The first PR smoke exposed only a Python 3.12 dynamic-import harness defect: the test module did not register its dynamically loaded dataclass module in `sys.modules`. The correction is confined to this rev1100 reserved test path.
- Exact code/workflow head `544ad9b5dc06236f29eff2ab4e2154c7a1aa656d` passed dedicated smoke run `32557892517`: Python compilation, all 15 focused fail-closed regressions, sibling-import rejection, canonical `attempt_solution` preview, and reserved-path enforcement all succeeded.
- The branch-push smoke then generated canonical `attempt_solution` evidence in commit `6d02797e6a2df740631cbc146d5bfe0bd01cae3b`, with `admitted=true`, `mode=exclusive`, and `conflicts=[]`.
- The workflow was extended within its reserved path to preview and materialize canonical `publish` evidence as well. A natural branch push generated that evidence in commit `ef688c584fa33c4a3bee51544e2aa3955ee00f5d`.
- Bot-authored evidence commits can leave PR workflows in GitHub's `action_required` state. This connector-authored documentation heartbeat intentionally changes no semantics; it lets ordinary PR checks evaluate a head that already contains both canonical phase-evidence files without manually rerunning any workflow.
