# rev286 — corrected SOJ Johnson terminal cost composition

## Scope

This revision handles only post-admission recurrence accounting for the explicit Johnson-embedding branch of corrected Split-or-Johnson. It does not modify active sibling branches, decide transition admission, execute the primitive-Johnson solver, or handle partial or larger-ground recursive Johnson embeddings.

## rev281 compatibility correction

The first rev286 test fixture included two synthetic fields that the real rev281 `CorrectedSOJTransitionCertificate` does not publish: `current_domain_size` and `proof_identity`. Although that first focused suite passed, it did not establish compatibility with the actual sibling certificate.

The corrected rev286 contract consumes only fields that rev281 publishes: transition status and kind, theorem gate, canonical/exact/progress flags, multiplicative actual/max cost, Johnson ground/subset/vertex counts, and reason. The pre-transition `current_domain_size` is now an explicit argument from the recurrence caller because it is accounting context rather than a rev281 certificate field. rev286 derives a deterministic transition snapshot identity locally from the fields it consumes.

## Main contracts

The implementation consumes only main-integrated `PrimitiveJohnsonGroundProof`, `RecurrenceAccountingNode`, and `validate_quasipoly_recurrence_tree`. It intentionally does not import the active rev281 module.

## Fail-closed checks

Composition requires the certified explicit-Johnson status/kind, theorem gate, canonicality, exactness, progress certification, a full `J(v,k)` domain, strict reduction from the caller-supplied current domain, root-envelope containment, a separately certified transition cost bound, and a separately certified terminal admission. The primitive terminal must be exact, canonical, childless, cost-certified, terminal-certified, structurally matched to the same Johnson parameters, and internally consistent with its recurrence leaf.

For certified transition maximum multiplicative cost `B >= 1` and primitive-terminal local charge `T`, the composed terminal leaf charges `log2(B) + T` at the pre-transition current-domain measure. The main recurrence validator is replayed over that leaf.

## Replay

The transition snapshot identity is a SHA-256 hash of canonical JSON over the actual rev281 fields consumed by rev286. The outer certificate additionally binds caller `current_domain_size`, terminal snapshot, both charges, the composed recurrence leaf, and the validator result. Replay recomputes the full certificate, so caller-measure drift and certificate drift are rejected.

## Tests

The focused suite now contains 20 cases. It includes a direct regression whose fixture matches the real rev281 field set and explicitly lacks both synthetic legacy fields. It also covers local snapshot identity, replay and caller-measure drift, full-domain and strict-shrink checks, external certification flags, cost bounds, terminal matching, accounting integrity, root-envelope validation, integer caller context, and quasipolynomial overrun.

The dedicated workflow installs the existing Johnson recognizer runtime dependency, runs the focused suite, and runs `py_compile` over rev286 plus the main terminal/accounting dependencies. No sibling workflow is changed, cancelled, or manually rerun.

## Coordination

The exact rev286 phase-admission evidence path remains reserved. The shared evidence generator is still fail-closed on the independently owned rev275 registry record, so rev286 does not fabricate evidence or edit sibling registry entries.
