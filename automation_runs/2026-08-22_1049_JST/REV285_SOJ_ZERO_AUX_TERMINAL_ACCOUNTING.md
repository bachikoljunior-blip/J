# AGI-GI rev285 — corrected SOJ zero-auxiliary terminal accounting

## Scope

Rev285 advances only `W1R-H6/corrected-split-or-johnson/zero-auxiliary-output-terminal-accounting`. The active rev281 / PR #226 sibling publishes a corrected-SOJ small-part transition contract that permits `small_size_after == 0`; rev283 / PR #228 deliberately refuses to normalize that value into its positive auxiliary-child recurrence type and leaves an explicit terminal mapping open. Rev284 separately owns explicit Johnson-embedding terminal admission. Rev285 does not modify or import any of those branch-only implementations.

Root state remains **NOT_AGI**. This revision does not construct corrected-SOJ transitions, does not solve the Johnson branch, does not integrate the production caller, and does not claim full Split-or-Johnson closure, GI, or AGI.

## Exact terminal boundary

`compose_corrected_soj_zero_aux_terminal_accounting` structurally revalidates the published small-part transition fields before doing any accounting. It accepts only:

- `status == certified_corrected_soj_small_part_reduction` and `transition_kind == small_part_reduction`;
- theorem-input, canonicality, exactness, and progress gates all certified;
- finite multiplicative cost and certified upper bound, both at least one, with observation no larger than the bound;
- `small_size_before > 0`, `small_size_after == 0`, and `small_size_before <= root_n`; and
- `alpha in [2/3,1)` with the declared strict shrink inequality mechanically true.

Zero output alone is **not** promoted to a terminal proof. The caller must separately provide `terminal_semantics_certified=True`, asserting that the exact zero auxiliary output is an exact terminal for the original recursive obligation. The caller must also separately provide `transition_cost_bound_certified=True`; rev285 never treats a numerical upper-bound field as its own proof.

## No fabricated positive child measure

The main-integrated recurrence validator requires every node measure to satisfy `1 <= m <= n`. Rev283 correctly rejected silently changing an exact `small_size_after == 0` into a synthetic `m == 1` child. Rev285 instead accounts the certified terminal transition as a **leaf at the pre-transition positive measure** `(root_n, small_size_before)`. It has no child, carries `terminal_certified=True`, and charges `log2(max_multiplicative_cost)` locally. Thus the zero output is represented by termination, not by inventing a positive successor measure.

The complete leaf is immediately replayed through the already-main-integrated `validate_quasipoly_recurrence_tree`. If the charged transition cost falls outside the configured quasipolynomial envelope, the composition fails closed.

## Replay and isolation

A deterministic SHA-256 digest binds the normalized transition snapshot, original root measure, explicit terminal/cost gates, terminal encoding, charged upper-bound cost, and recurrence parameters. Replay recomputes the terminal mapping and main validator result; transition or parameter drift is rejected.

The rev285 branch writes only its reserved module, tests, audit note, workflow, and (when canonical shared admission becomes possible) its exact phase-admission evidence path. It does not alter sibling claims, branches, PRs, workflows, shared implementation files, `MAIN.md`, CRX1/CRX2/CRX3, state-orbit, or proof-carrying-merge paths.

## Regression boundary

The focused suite covers successful exact terminal encoding, explicit terminal-semantics gating, external cost-certificate gating, nonzero-output rejection, published transition-contract revalidation, upper-bound charging, invalid measures and alpha, main recurrence envelope rejection, replay drift, and missing structural fields. The dedicated workflow also runs the inherited main recurrence-accounting regression file against the exact PR head.
