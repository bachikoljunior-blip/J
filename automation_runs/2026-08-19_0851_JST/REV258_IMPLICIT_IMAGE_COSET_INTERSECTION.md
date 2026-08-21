# AGI-GI rev258: implicit image value-coset intersection

## Solved child

Starting from rev257's faithful unary/binary auxiliary action for a permutation group supplied by generators, intersect the exact implicit image group with the complete source-to-target value-preserving right coset without enumerating that image group.

The implementation reuses the repository's proof-carrying U2 candidate-coset String Isomorphism solver on the auxiliary feature string. Exact results are therefore complete relative to rev257's certified image group; unresolved structural recursion remains fail-closed.

## Reused mechanisms

- rev257 paired Schreier construction and exact image group;
- `RightCoset` as the complete ambient image-group candidate;
- `candidate_coset_string_isomorphism_u2` for exact/fail-closed string-coset intersection;
- existing multiplicity, small-order, orbit, imprimitive, and primitive-Johnson proof paths inside U2.

## Strict boundary

This closes only the image-space value-coset intersection child. It does **not** yet lift the exact auxiliary coset back through the paired action to an original-domain right coset, and it does not certify that auxiliary work against the original root's quasipolynomial envelope. Those are subsequent children. CRX1, GI, and AGI remain unresolved; state remains `NOT_AGI`.
