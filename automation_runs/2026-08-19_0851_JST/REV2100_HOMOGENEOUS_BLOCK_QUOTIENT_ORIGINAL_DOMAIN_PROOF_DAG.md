# AGI-GI rev2100 — homogeneous-block quotient result → original-domain proof DAG

## Scope

This revision is owned by `chatgpt-session-j-rev2100-homogeneous-block-original-domain-result-proof-dag-20260822T174500JST-9fe789cd` and is restricted to `crx3/algorithmic-consumers/homogeneous-block-quotient-result-original-domain-lift-proof-dag`.

It consumes only main-integrated rev273/rev274 primitives plus the **public shape** of the independently owned rev1800 quotient-result proof. It imports neither rev1800 nor rev278 branch-only implementation.

## Exactness boundary

A quotient feature-string isomorphism is not automatically a quotient relation isomorphism. rev2100 therefore independently enumerates the certified source quotient image under an explicit `max_quotient_enumeration` cap and computes the complete quotient relation-isomorphism set from rev273's homogeneous quotient structures. Parent promotion is allowed only when that semantic set is exactly equal to the public rev1800 quotient right coset.

The main-integrated rev273 canonical point lift must also conjugate the paired rev274 source group onto the target group. rev2100 reconstructs the source witness and target stabilizer preimages using the already-main-integrated generic block-action preimage primitive, checks the resulting original-domain representative against every named source/target relation, checks every target subgroup generator against the full target relation structure, and verifies the expected kernel × quotient-stabilizer subgroup order.

Only after all of those gates does the exact original-domain right coset become a cost-certified terminal proof submitted to the common execution proof-DAG validator.

## Fail-closed cases

- rev1800 feature coset is a strict subset/superset of the semantic quotient relation SI set;
- exact-empty feature result while a rev273 quotient relation transport still exists;
- malformed/tampered rev273 or rev274 evidence;
- quotient enumeration exceeds the explicit cap;
- rev273 point lift fails to conjugate the paired candidate groups;
- quotient witness or target stabilizer preimage is incomplete;
- original-domain representative or target subgroup fails the full relation checks;
- proof-DAG/accounting envelope rejects the terminal.

## Canonical phase admission and validation handoff

The dedicated branch has persisted canonical `attempt_solution` and `publish` phase evidence at commit `1af5c3f1763756d2b50477f4c4e3082753bc17da`. Both snapshots report `admitted=true` with `conflicts=[]` and assert that this run modifies no other worker's claimed paths.

The implementation itself already passes all 9 focused success/fail-closed regressions and `py_compile`. The first dedicated PR check failed only in its own reserved diff guard because a shallow checkout had no merge base; the workflow was corrected on this branch to use complete history. No failed sibling workflow was cancelled or rerun.

A subsequent active-registry recheck found no scope/path collision. In particular, the independently owned rev2300 structural-coherence claim explicitly excludes rev2100 / PR #272 and every rev2100 reserved path. This ordinary documentation commit follows the evidence-only bot commit so GitHub receives a fresh PR synchronize event naturally; it is not a manual rerun of any existing workflow.

PR #272 remains draft and unmerged. rev1800 / PR #268 and rev278 / PR #222 remain independently owned upstream contracts; rev2100 consumes only their public-shaped contract and does not modify, merge, close, rebase, or force-push either branch.

## Parallel boundary

rev2000 / PR #271, rev1800 / PR #268, rev1200 / PR #260, rev278 / PR #222, all corrected Split-or-Johnson work, `MAIN.md`, shared proof-DAG/recurrence/S1/coordination code, sibling claims, branches, PRs, and workflows are read-only. No sibling workflow is cancelled or manually rerun.

This is one CRX3 consumer leaf. It does not close other CRX3 consumers, Graph Isomorphism, practical AGI delivery, or AGI. State remains `NOT_AGI`.
