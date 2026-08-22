# AGI-GI rev279 — implicit relation parent-outcome proof-DAG attachment

## Scope

rev279 consumes only two already main-integrated substrates:

1. rev266 `ParentExactOutcomeContract`, which normalizes one independently verified exact nonempty rev261 parent promotion or one independently verified rev263 exact-empty parent promotion; and
2. the shared rev220 execution proof-DAG accounting validator.

It adds no new String-Isomorphism solver, does not reconstruct the rev261 right coset, and does not repeat image-action, image-value, paired-preimage, or exact-empty semantic verification.

## Contract

The consumer independently replays the canonical rev266 transcript digest from its immutable scalar fields before creating any proof-DAG identity. Accepted evidence must be exact and complete, use the expected rev261/rev263 status family, carry canonical lowercase SHA-256 digests, have positive parent domain degree, and fit under the supplied original root.

The resulting `ParentOutcomeProofIdentity` freezes the outcome kind/status, source evidence revision/status, parent and auxiliary degrees, source/target relation digests, upstream artifact digest, transcript digest, original root, and versioned solver identity. The identity is immutable, hashable, and explicitly replay-stable.

## Semantic boundary

The attached `ProofCarryingCoset` is intentionally **evidence-only**:

- `coset` is always `None`;
- `exact` is always `False`;
- `semantic_exactness_certified` is always `False`;
- any attempt to set the proof exact bit or inject a coset is rejected by the independent identity validator.

This prevents a digest-only rev266 contract from being misread as a reconstructed SI solution. The upstream rev266 outcome itself remains exact/complete evidence; rev279 certifies only replay identity and conservative accounting of checking that already materialized contract.

## Cost boundary

rev279 charges only canonical transcript serialization, digest verification, fixed-field validation, and proof-DAG bookkeeping. It does not charge or claim construction of any upstream SI object. The deliberately loose local log2 bound is polynomial in the materialized parent/auxiliary degrees and is checked by the shared execution proof-DAG validator inside the caller's original-root quasipolynomial envelope.

## Fail-closed cases

The consumer rejects malformed runtime types, nonexact/incomplete outcomes, zero parent degree, an undersized original root, malformed or tampered digests, outcome/status mismatches, wrong source evidence revision/status, identity tampering, proof/accounting payload mismatch, forbidden semantic promotion, and a failed global proof-DAG envelope.

## Parallel safety

The revision owns only the rev279 additive files recorded in `chatgpt-session-j-rev279-parent-outcome-proof-dag-20260822T094800JST-15932427`. It does not write any rev275–rev278 path, rev273/rev271/rev264/state-orbit proof-DAG path, CRX1/CRX2 implementation, shared solver, sibling claim, sibling workflow, or `MAIN.md`.

AGI state remains `NOT_AGI`.
