# AGI-GI rev209 audit — reuse validated Johnson profile closure inside candidate SI

## Problem-tree accounting

The strict AGI root remains `NOT_AGI`. Predicted and effective non-replaced problem counts remain **512 / 512**. This change replaces a subcase of existing **W1R-H6-C2b** in place; it does not create a new active branch, so the mandatory over-count rewrite is not triggered.

## Cross-tree / existing-world audit

The current H6-C2b `primitive_non_giant` candidate path already recognizes Johnson actions but, before this rev, dispatched only to `primitive_johnson_ground_string_isomorphism_terminal`. That terminal intentionally fails closed when the certified Johnson ground is above its explicit/polylog brute-force window.

The repository already contains a stronger solution for a large and useful subset of exactly that child: rev177's `signed_johnson_ground_profile_partition_si`. It transports the actual colored k-subset string to the certified Johnson ground, forms complement-safe star/anti-star point profiles, finds an exact bounded partition transporter in the represented ambient action, and returns an exact original-domain SI coset whenever the full relation is determined by the cell-count profile. Its J(9,2) regression closes a group of order 9! without enumerating that group.

At the external-theory layer this reuse is consistent with the standard Johnson-action strategy in permutation-group GI: expose structure on the smaller underlying set instead of enumerating the huge action on k-subsets. No new theorem claim is needed here because the exactness boundary is already mechanically implemented and CI-tested in rev175/rev177.

A second audit found that rev176's signed-ground **small-order** terminal would be redundant in this particular candidate dispatcher: the candidate path has already run `exact_small_order_candidate_string_isomorphism` on the same subgroup under the same order gate. Repeating the signed small-order enumeration cannot add coverage. rev209 therefore removes that duplicate proposed branch rather than growing the problem tree.

## Executable integration

`u2_candidate_coset_string_iso_v2.py` now, after an unresolved small-ground Johnson terminal in a `primitive_non_giant` candidate, invokes the validated complement-safe profile-partition terminal on the subgroup-shifted source and target. Exact results are translated back through the fixed candidate representative with the existing exact coset-coordinate helper. An explicit `max_partition_states` argument defaults to 4096 and is additionally bounded by `root_n**2`; exhaustion remains fail-closed.

Focused regression demonstrates:

- J(9,2) with represented group order 9! where the old small-ground terminal returns `undetermined_johnson_ground_cap`, but the integrated candidate solver returns an exact profile-partition SI coset;
- a profile invariant mismatch becomes exact empty;
- an intentionally tiny partition-state cap remains unresolved rather than being misreported as exact.

## Remaining H6-C2b leaf

After this integration, unresolved primitive-non-giant candidate cases are those whose Johnson relation is not profile-determined (or exceeds the bounded partition orbit) and therefore require the already-built higher-order lower-arity-image / logarithmic-certificate / Design-Lemma machinery to be integrated at this candidate boundary. Non-Johnson primitive states and giant quotients with nontrivial kernels also remain explicit unresolved children.

No AGI, full Split-or-Johnson, or global quasipolynomial recurrence closure is claimed.
