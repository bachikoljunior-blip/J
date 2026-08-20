# AGI-GI rev208 problem-tree audit

## Parent leaf and prediction

rev207 narrows the active image-SI boundary to **H6-C2**: exact proof-carrying candidate SI is still missing for some typed large structural children reached inside the rev206 coupled parent action.  The predicted total remains **512** and the effective non-replaced count remains **512**; the over-count rewrite trigger therefore does not fire.

A direct attempt at H6-C2 found that one existing child was overgeneralized:

- **H6-C2a:** represented primitive giant (`A_m`/`S_m`) candidate or invariant-orbit image;
- **H6-C2b:** primitive non-giant / higher-arity Johnson / genuinely unresolved Split-or-Johnson structure.

rev208 resolves C2a and keeps C2b fail-closed.

## World-solution inclusion and higher-level simplification

The previous tree routed every `primitive_giant_local_certificates` classification toward Babai's general local-certificates/growing-beard machinery.  That theorem is needed when an arbitrary parent group only has a giant **quotient** and a nontrivial kernel must be controlled.  At the specific S1/U2 leaf classified using singleton blocks, however, the exact Schreier order certificate proves that the represented action itself is literally `A_m` or `S_m`.

For that stronger special case, classical permutation-group structure solves String Isomorphism directly:

1. under `S_m`, two colored strings are isomorphic iff color multiplicities agree;
2. the solution set is one coset of the product of symmetric groups on target color classes;
3. under `A_m`, intersect that color stabilizer with even permutations;
4. if any color class has size at least two, a color-preserving transposition toggles witness parity, so an even witness always exists once multiplicities agree;
5. if all classes are singletons, the color-compatible permutation is unique and existence is exactly its parity.

Thus a general local-certificate recursion is unnecessary at this exact leaf.  This is a higher-level branch deletion, not merely duplicate-code merging.

## rev208 implementation

`primitive_giant_color_terminal_v1.py` reconstructs the full exact SI coset without enumerating the giant group.  It mechanically checks the represented order is exactly `m!` or `m!/2`, constructs one color-compatible witness, handles the alternating parity obstruction, and builds the exact target-color stabilizer inside `S_m` or `A_m`.  Generator orders are independently Schreier-certified.

`s1_string_isomorphism_v2.py` now uses that terminal whenever its exact structural classifier returns `primitive_giant_local_certificates`.  This automatically closes primitive giant **orbit-image** children already reached by the existing intransitive U2 recursion.

`u2_candidate_coset_string_iso_v3.py` additionally closes the top-level candidate case `H*r` by shifting the source to subgroup coordinates, invoking the same exact giant terminal in `H`, then using the existing exact right-coset translation.

The focused tests include exhaustive A5/S5 comparison against exact group enumeration, the alternating unique-odd obstruction, large S9/A9 dispatch beyond the enumeration cap, top-level right-coset translation, and a direct product of two S9 orbit images to exercise the existing U2 intransitive preimage path.

## Resulting next leaf after validation

**H6-C2b:** close the remaining primitive non-giant / higher-arity Johnson and typed Split-or-Johnson candidate-image states with exact proof-carrying recursion.  Reuse rev207's polynomial auxiliary lift; do not reintroduce the deleted literal-A/S local-certificate branch.  Missing theorem parameters, unresolved relational ground recognition, and resource overflow remain fail closed.

This does not establish full W1R-H6 closure or AGI.  AGI remains **NOT_AGI**.
