# rev286 — corrected SOJ Johnson terminal cost composition

## Scope

This revision closes only the post-admission accounting boundary for the explicit Johnson-embedding branch of the corrected Split-or-Johnson transition.

It deliberately does **not**:

- import or depend on the active rev281 / PR #226 implementation module,
- import or depend on the active rev284 terminal-admission module,
- decide whether a Johnson transition is semantically admissible,
- execute the primitive-Johnson terminal,
- treat a Johnson structural transition as an `aux_shrink` recurrence edge,
- handle partial Johnson embeddings or larger-ground recursive Johnson cases,
- modify sibling claims, branches, PRs, workflows, or `MAIN.md`.

The caller must supply both an externally/mechanically certified transition-cost bound and a separately certified terminal-admission decision.

## Main-integrated contracts consumed

The implementation consumes only contracts already present on `main`:

1. `primitive_johnson_ground_terminal_v1.PrimitiveJohnsonGroundProof`, including its exact terminal statuses and leaf accounting contract.
2. `quasipoly_recurrence_accounting_v1.RecurrenceAccountingNode` and `validate_quasipoly_recurrence_tree`.

The corrected-SOJ transition is accepted structurally through a snapshot rather than by importing an active sibling branch. The expected published shape is the explicit Johnson-embedding status/kind together with theorem-gate, canonical, exact, progress, Johnson-parameter, multiplicative-cost, and proof-identity fields.

## Fail-closed admission to this composer

The composer rejects unless all of the following hold:

- transition status is `certified_corrected_soj_explicit_johnson_embedding`,
- transition kind is `johnson_embedding`,
- theorem-input gate, canonicality, exactness, and progress are all certified,
- Johnson parameters satisfy `v >= 4` and `2 <= k <= v-2`,
- `johnson_vertex_count == C(v,k)`, so the embedding covers the full Johnson domain expected by the exact primitive terminal,
- the Johnson domain is strictly smaller than the pre-transition current domain,
- the current domain remains inside the caller's root envelope,
- transition multiplicative cost is finite/nonnegative and no larger than its certified maximum,
- the certified maximum is finite and at least one,
- a separate external transition-cost-bound certificate is asserted,
- a separate external terminal-admission certificate is asserted,
- the supplied terminal object is a `PrimitiveJohnsonGroundProof`,
- its status is one of the exact primitive-Johnson terminal statuses,
- it is canonical, exact, local-cost-certified, terminal-certified, and childless,
- its root envelope, domain size, Johnson ground, and Johnson subset match the transition exactly,
- exact-empty carries no coset and exact-coset carries a coset,
- the embedded primitive accounting leaf agrees exactly with the proof's operation, measures, terminal/cost flags, and local log2 charge,
- the primitive accounting leaf independently validates under the main quasipolynomial validator.

## Accounting composition

For a certified transition maximum multiplicative cost `B >= 1`, the transition charge is

`log2(B)`.

For an already exact primitive-Johnson terminal with certified local charge `T`, the composed local charge is

`log2(B) + T`.

The result is one terminal recurrence leaf at the **pre-transition** current-domain measure. This is intentional: the structural Johnson embedding and the exact primitive terminal jointly terminate the admitted branch, while no unsupported recursive progress kind is invented. The main recurrence validator is replayed over the combined leaf and the composer fails closed if the root quasipolynomial envelope is exceeded.

## Replay identity

The certificate identity hashes a canonical JSON payload containing:

- the transition snapshot,
- the terminal accounting snapshot,
- the transition and terminal charges,
- the composed recurrence leaf,
- the main-validator result.

Replay recomputes the full certificate and requires dataclass equality. Any snapshot, charge, accounting, validation, or identity drift is therefore rejected.

## Tests

`test_corrected_soj_johnson_terminal_cost_rev286.py` covers sixteen cases:

- successful full-domain composition,
- successful replay,
- tampered-certificate replay rejection,
- partial Johnson-domain rejection,
- nonshrinking Johnson transition rejection,
- missing transition-cost certification,
- missing terminal-admission certification,
- actual transition cost exceeding its certified bound,
- wrong transition status,
- terminal Johnson-ground mismatch,
- terminal domain mismatch,
- nonexact terminal rejection,
- exact-empty-with-coset rejection,
- primitive proof/accounting mismatch,
- parent measure outside the root envelope,
- combined charge exceeding the quasipolynomial envelope.

The dedicated workflow also runs `py_compile` over the new module/test and the two main-integrated dependency modules. No workflow is manually rerun or cancelled by this revision.

## Coordination / phase admission

The canonical phase-admission registry remains fail-closed because of the independently owned noncanonical rev275 registry record already observed by this session. The exact rev286 `attempt-solution` evidence path is reserved but is not fabricated. No sibling registry entry is edited or normalized.

AGI state remains `NOT_AGI`.
