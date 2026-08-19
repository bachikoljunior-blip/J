# rev108 independent validation — AGI-GI rev系列

AGI status: **NOT_AGI**. This validates one permutation-group primitive only.

## Target
`product_action_coset_intersection.py`: reduce right-coset intersection `aH ∩ bK` to a transporter problem for the `H×K` product action on ordered pairs, representing a nonempty exact intersection as one right coset of `H∩K`.

## Independent oracle checks executed

1. Reconstructed the committed rev108 implementation and its rev104–rev107 dependencies from J.
2. Ran 180 deterministic random cases for degrees 1–5. For each case, independently enumerated the generated subgroups, explicitly constructed both right-coset element sets, intersected them, and compared status, intersection order, and membership against the rev108 result. All 180 matched.
3. Added a stronger exhaustive audit for degrees 1–3. All distinct generated subgroups obtainable from one/two generators were deduplicated by explicit closure, then every subgroup-pair and every pair of right-coset representatives was checked against explicit set intersection. Results:
   - degree 1: 1 subgroup, 1 case
   - degree 2: 2 subgroups, 16 cases
   - degree 3: 6 subgroups, 1,296 cases
   - total exhaustive small-degree cases: 1,313
   All cases matched exactly.
4. The existing fail-closed design remains: if the product state orbit exceeds `max_images`, the routine returns `undetermined_image_orbit_limit` with no coset certificate instead of guessing.

## Result
rev108 product-action right-coset intersection is accepted as **solved_v0_1 for its bounded/exact primitive contract**. This does not establish worst-case scalable general canonical labeling or AGI.

## Next unresolved leaf
The remaining general-GI path still needs a scalable set/string stabilizer and coset-intersection layer whose complexity is controlled beyond explicit state-image orbit enumeration, and then integration into canonical partitioning/labeling with end-to-end oracle-backed graph-isomorphism tests.
