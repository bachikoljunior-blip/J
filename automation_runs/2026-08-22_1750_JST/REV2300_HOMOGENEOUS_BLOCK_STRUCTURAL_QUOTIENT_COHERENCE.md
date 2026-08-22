# AGI-GI rev2300 — homogeneous-block structural/original-domain proof coherence

## Scope

This leaf is owned by `chatgpt-session-j-rev2300-homogeneous-block-structural-quotient-coherence-20260822T175000JST-5ee6ec94` and is restricted to `crx3/algorithmic-consumers/homogeneous-block-structural-original-domain-proof-coherence`.

It closes only a post-replay TOCTOU/coherence boundary between two independently owned public contracts:

- rev2000 / PR #271: structural homogeneous-block relation/action/kernel compatibility proof-DAG evidence, intentionally without semantic String-Isomorphism exactness;
- rev2100 / PR #272: exact original-domain semantic result obtained after independently checking the complete quotient relation-isomorphism set and lifting it back to the full named relation structure.

The initial rev2300 idea was narrower quotient-execution coherence. It was deliberately narrowed again after rev2100 became visible and showed that quotient semantic completeness and original-domain lifting were already owned there. rev2300 therefore does not duplicate that work.

## Contract

The adapter imports no rev2000 or rev2100 branch-only implementation. It consumes only their public runtime shapes and fails closed unless:

- rev2000 is certified, replay-stable structural evidence and still explicitly refuses semantic-SI promotion;
- rev2100 is certified, exact, complete, quotient-semantically complete, and parent-semantically exact;
- the rev2000 relation transcript independently replays from the supplied source/target named unary/binary relations and relation certificate;
- rev2100 freezes those same source/target structures and the same relation certificate;
- rev274 action-provenance and rev275 kernel-factorization digests agree across the two public proofs;
- source/target canonical partitions, block map, block count, block size, original-domain degree, quotient sizes, and original-root accounting context agree exactly;
- the rev2100 quotient snapshot is exact/complete and bound to those same provenance digests;
- exact-empty and nonempty parent outcomes remain distinct and carry the required absence/presence of parent coset data.

On success it emits a separate deterministic SHA-256 coherence identity over the shared structural/semantic tuple. Replay recomputes the complete certificate and rejects mutation.

## Strict boundary

This revision does not execute quotient String-Isomorphism, enumerate quotient groups, compute block-action preimages, lift a transporter, validate sibling proof-DAG internals, modify shared proof-DAG/recurrence code, or turn rev2000 structural evidence into semantic exactness by itself. Semantic parent exactness remains owned by rev2100 and is only cross-bound here after rev2100 has already certified it.

rev1800/#268, rev1200/#260, rev278/#222, corrected Split-or-Johnson work, `MAIN.md`, shared coordination code, sibling claims/branches/PRs/workflows, and their reserved paths are read-only and untouched.

## Focused verification

The standard-library suite covers both nonempty and exact-empty success/replay plus fail-closed drift in certification flags, semantic-promotion flags, relation transcript, source structure, action/kernel digest, partition, root accounting context, quotient/parent outcome, coset presence, exact-empty representative data, certificate replay, and relation-domain validity.

Passing rev2300 proves only cross-proof coherence for one already-certified homogeneous-block execution path. It does not close CRX3, Graph Isomorphism, practical AGI delivery, or AGI. `agi_state` remains `NOT_AGI`.
