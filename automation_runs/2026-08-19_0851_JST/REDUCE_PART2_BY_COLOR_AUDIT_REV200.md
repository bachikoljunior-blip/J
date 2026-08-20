# rev200 exact Reduce-Part2-by-Color audit

Run identity: `chatgpt-session-immediate-20260820T085307+0900-06aca83f`  
Execution start: `2026-08-20T08:53:07+09:00`  
Starting main: `06aca83ffef7e644ae63421514cfab8c2fe0c2ea`  
Starting AGI-GI revision: `rev199`

## Scope and strict status

This revision advances one internal child of W1R-H6. It does **not** implement the full corrected Bipartite Split-or-Johnson procedure, close the graph/string-isomorphism recurrence, or establish AGI. The strict state remains `NOT_AGI` and the root problem remains unresolved.

The retained problem-count policy is **predicted 512 / effective 512**. The selected child replaces an unresolved internal W1R-H6 leaf, so no new active top-level branch is added and the count-overrun rewrite trigger is not activated.

## Existing-world solution audit across layers

The active leaf was checked against the primary exposition:

- H. A. Helfgott, J. Bajpai, D. Dona, *Graph isomorphisms in quasi-polynomial time*, arXiv:1710.04574, Exercise 5.5 and Proposition 5.7: https://arxiv.org/abs/1710.04574
- L. Babai, *Graph Isomorphism in Quasipolynomial Time*, arXiv:1512.03547, Split-or-Johnson: https://arxiv.org/abs/1512.03547

The relevant existing mathematical object is Exercise 5.5: for a full bipartite graph that is twin-free on `V1` and a two-part cover `V2=C0 dot-union C1`, at least one restriction has no left twin class of size `>= |V1|/2 + 1`. For integral class sizes, the exact check is

```text
largest_restricted_twin_class <= ceil(|V1|/2).
```

The implementation applies that object at multiple layers instead of substituting a weaker phase label:

1. **Combinatorial layer:** construct both restricted twin equivalence relations exactly.
2. **Canonical-choice layer:** among eligible restrictions choose minimum part size, then the supplied ordered canonical color index; no vertex-label representative is selected.
3. **Proof-carrying software layer:** return the full twin classes, exact largest-class sizes, exact gate booleans, selected restriction, and reason.
4. **Recurrence layer:** record `selected_alpha_shrink` separately. Exercise 5.5 can give only a proper one-vertex decrease, so a caller that already paid a quasipolynomial branching cost may not silently call it constant-factor progress.
5. **Safety/achievement layer:** invalid partitions, non-twin-free inputs, and impossible theorem states fail closed; no local certificate is promoted to AGI evidence.

## Failed first attempt and counterexample

A candidate implementation checked only

```text
relative_symmetry_defect >= 1 - alpha.
```

For `alpha=3/4`, this accepts a restricted largest twin class of size `3|V1|/4`, which is weaker than Exercise 5.5. It also accepted an empty color part, allowing a successful result with no right-part reduction.

The regression `test_selects_side_with_exact_exercise55_bound` fixes a concrete `6 x 4` counterexample: `C0` has restricted left twin classes of sizes `4` and `2`, so its defect `1/3` passes the old `1/4` threshold but violates the exact Exercise 5.5 bound `3`; the corrected implementation selects `C1`.

## Implemented child

`bipartite_reduce_part2_by_color_v1.py` now certifies all of the following before returning success:

- declared endpoints and left-color lengths are valid;
- `C0,C1` are a disjoint, nonempty, complete ordered cover of `V2`;
- the full same-colored left twin relation is discrete;
- at least one restriction meets the exact integral Exercise 5.5 bound;
- the selected side is a proper restriction;
- constant-factor `alpha` shrink is reported, not assumed.

The selected unresolved parent remains the corrected general UPCC Bipartite Split-or-Johnson recursion. This local child is solved, but the parent is not.

## Recursive decomposition after the attempt

The unresolved parent is retained in place and decomposed into the following active internal children:

- **H6-R3 — parent provenance/canonicity:** mechanically derive the ordered right coloring from the parent coherent/Design state and prove equivariance across source and target.
- **H6-R4 — paired recursive composition:** construct a complete source/target family of eligible restricted children without choosing incompatible local sides.
- **H6-R5 — progress/cost discipline:** distinguish cost-free proper descent from post-branching constant-factor descent on every recursive edge.
- **H6-J1 — Johnson alternative:** construct the uniform-neighborhood hypergraph, recognize a complete uniform family, and emit an explicit Johnson embedding.
- **H6-D1 — non-Johnson alternative:** derive a nonconstant controlled-arity relation on the right part and connect it to exact Design/coherent descent.
- **H6-SI1 — exact-set integration:** lift every structural branch through the ambient action, intersect with the full parent strings, and reconstruct the exact isomorphism coset/empty set.
- **H6-C1 — recurrence closure:** attach canonicality, exactness, multiplicative-cost, and strict progress certificates to every recursive edge before global accounting accepts it.

The next unresolved leaf is **H6-R3 parent provenance/canonicity**. None of the unmerged repository branches are counted as solved state.

## Verification

Local command:

```text
python -m pytest -q test_bipartite_reduce_part2_by_color_rev200.py
```

Result: `6 passed`.

The suite includes all `2^(4*3)=4096` uncolored `4 x 3` bipartite graphs and every proper ordered two-part cover of the right side. For every full-left-twin-free case, it verifies that at least one exact Exercise 5.5 gate fires and that the selected child is a proper restriction.
