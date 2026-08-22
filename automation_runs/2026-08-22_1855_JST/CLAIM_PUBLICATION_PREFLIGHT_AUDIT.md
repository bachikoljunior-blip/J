# Claim publication preflight collision guard

## Scope

This coordination leaf adds a file-disjoint, fail-closed pre-publication check for J's durable parallel-claim registry. It reuses the already-main-integrated conflict semantics in `automation/parallel_claims.py`; it does not modify that shared module, `MAIN.md`, solver/proof-DAG implementations, sibling claims, or sibling workflows.

The dedicated claim is `chatgpt-session-j-claim-publication-preflight-20260822T185534JST-2d97221e`, with `target_revision: null` so this coordination work does not consume a mathematical revision number.

## Why this leaf exists

During the 2026-08-22 continuation window, independent workers repeatedly reached the same coordination or revision target before later phase admission exposed the collision. This session itself initially reserved a stale `MAIN.md` rev1600 declaration-sync leaf, then discovered a later independently owned live rev1600 main-sync claim reserving `MAIN.md`. It immediately relinquished only its own claim and did not touch the sibling claim or `MAIN.md`.

Canonical main subsequently recorded separate rev2400 and rev2500 collision retreats. Those events show that the existing phase-admission guard is correctly fail-closed, but it runs after a claim can already have been published and work can already have started.

## Contract

`claim_publication_preflight_v1.py` provides three read-only decision modes:

- `prepublish`: parse a proposed schema-v2 claim with the canonical registry parser, require it to be fresh and unpublished, and compare its scope, non-null target revision, and reserved paths with every fresh registry owner before publication;
- `published-audit`: require exactly one fresh canonical published owner matching the candidate and then report any fresh sibling collision without changing either owner;
- `registry-audit`: deterministically report every fresh pairwise collision already present in the registry.

Malformed candidate or registry data fails closed. Stale and completed owners do not block a new claim. `target_revision: null` does not collide merely because another coordination claim also has a null target; scope and path reservations remain authoritative.

Outputs include a deterministic fresh-registry snapshot and digest, normalized candidate snapshot, conflict owners, and machine-readable reasons. The tool never writes, closes, rewrites, or chooses a winner among claims.

## TOCTOU boundary

A pre-publication read cannot itself provide a distributed atomic compare-and-swap across independent workers. Two processes can both observe a clean snapshot and race to publish. Therefore callers must rerun the preflight immediately before claim publication, and canonical post-publication collision audit plus repository phase admission remain authoritative. This leaf reduces avoidable races; it does not replace the durable registry or phase-admission protocol.

## Validation boundary

The focused standard-library regression suite covers clean admission, scope/revision/path collisions, path-prefix collision, stale/completed owners, stale/closed candidates, malformed candidate/registry data, duplicate claim IDs, published-owner audit, deterministic registry audit, disjoint claims, and null-target coordination claims. A dedicated workflow additionally performs canonical `attempt_solution` and `publish` admission previews for this exact reserved diff, runs the tests and `py_compile`, and enforces the reserved-path boundary.

## Non-interference and AGI boundary

No sibling branch, PR, claim, workflow, solver, proof-DAG implementation, `MAIN.md`, or shared coordination implementation is modified by this branch. Existing workflows are not cancelled or manually rerun, and sibling branches are not rebased or force-pushed. This is coordination hardening only. Repository state remains `NOT_AGI`.
