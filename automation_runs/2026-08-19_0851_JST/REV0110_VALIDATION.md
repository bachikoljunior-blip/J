# rev110 validation — recursive stabilizer-chain right-coset intersection

AGI status: **NOT_AGI**. This is a graph-isomorphism/permutation-group subproblem result only.

## Goal

Replace rev109's complete compressed-relation orbit traversal with an exact fail-closed route that branches on point images and recursively passes to point stabilizers. This controls cases where a full H×K relation/double-coset orbit is large even though the stabilizer structure is simple.

## Independent oracle checks executed in the run

A clean local copy of the relevant rev107–rev109 primitives plus the new rev110 module was executed with `python -m pytest -q`.

Result: **4 tests passed**.

The checks were:

1. **Complete degree 1–3 audit:** all distinct subgroups of S1, S2 and S3 were constructed by explicit closure; every subgroup pair and every pair of right-coset representatives was tested. Total: **1,313 coset intersections**. Empty/non-empty status, exact intersection order and membership of every permutation agreed with the explicit set-intersection oracle.
2. **Random degree 1–6 audit:** **500 deterministic random cases** with 1–3 random generators per subgroup. Every result agreed with explicit subgroup closure and explicit right-coset set intersection.
3. **Large-orbit structural case:** H and K were the two different one-point stabilizers in S8. Each has order 5,040 and H∩K has order 720, so the equivalent complete relation orbit has `5040*5040/720 = 35,280` images. rev110 returned the exact order-720 intersection in **3 recursive search nodes**, without enumerating that relation orbit.
4. **Fail-closed bound:** the same S8 case with `max_nodes=1` returned `undetermined_node_limit` and no coset certificate.

## What is established

For the tested cases, exact right-coset intersection can be represented as one right coset of H∩K while avoiding complete relation-orbit enumeration. The implementation constructs H∩K recursively from point stabilizers and exact transporter witnesses.

## What is not established

This is **not** a polynomial/quasipolynomial worst-case bound for arbitrary permutation-group coset intersection and is not yet an end-to-end canonical-labeling or GI solver proof. Worst-case recursive point-image branching can still grow rapidly. The next leaf therefore remains integration with canonical partitioning/labeling plus adversarial GI oracle tests, followed by stronger worst-case structural decomposition where required.
