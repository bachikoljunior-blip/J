# rev106 — bounded exact string transporters and coset intersection

Root remains **NOT_AGI**.

A direct attempt at the remaining set/string/coset layer first produced a correctness baseline that is exact but deliberately not claimed scalable for large groups.

Given a rev104 stabilizer chain, the implementation refuses explicit enumeration when the certified group order exceeds `max_elements`; otherwise it enumerates the group and computes exact string transporters. A transporter is represented as `representative * H_target`, where `H_target` is the target-string stabilizer under the repository's left-to-right permutation composition/action convention. During implementation, an initial source-stabilizer formulation was identified as wrong for this right-coset convention and corrected before validation.

It also computes intersection of two explicitly bounded right cosets and reconstructs the nonempty intersection as a new exact right coset by translating all intersection elements back to a subgroup.

In-session exhaustive validation:

- **250 random string-transporter cases** on generated permutation groups of degree 1–6 matched the exact transporter element set; represented coset membership matched sampled arbitrary permutations.
- **200 random right-coset intersection cases** matched explicit set intersections and reconstructed exact intersection cosets.
- A generated `S8` case (order 40,320) with `max_elements=1,000` correctly abstains before enumeration.

Because this is a bounded baseline, the parent `...c3c3c2c` remains unresolved and is decomposed into:

- `...c3c3c2c1`: bounded exhaustive transporter and right-coset-intersection correctness baseline — `solved_v0_1`;
- `...c3c3c2c2`: non-enumerative set/string stabilizer and transporter via Schreier action on state orbits — unresolved;
- `...c3c3c2c3`: non-enumerative subgroup/coset intersection and divide-and-conquer restrictions for large image orbits — unresolved.

Estimated active-node count after decomposition: **494**, below prediction **512**.
