# rev205 lossless paired left-twin quotient audit

Run identity: `2026-08-20T09:24:53+09:00__rev201__43a16b622129`  
Execution start: `2026-08-20T09:24:53+09:00`  
Stacked base: rev204 candidate branch  
AGI-GI transition under test: `rev204 -> rev205`

## Scope and strict status

rev204 deliberately fails closed when its canonical right partition reaches rev200 but the original left side has nontrivial same-colored twins. rev205 treats that state as a reducible exact quotient rather than a terminal error.

The quotient equivalence is elementary and exact: two left vertices are identified iff their input colors and complete neighborhoods in the right part are identical. Every color-preserving bipartite isomorphism maps each such twin class to another class of equal original color and equal multiplicity. Conversely, once a quotient isomorphism matches weighted twin classes and the right side, any bijection inside each matched class lifts to a full original isomorphism because all members have identical neighborhoods and colors.

Accordingly, each quotient left vertex is colored by `(original typed left color, twin-class multiplicity)`. The right side is unchanged. If any twin class is nontrivial, the left degree strictly decreases. Class numeric ids are only local labels of the smaller isomorphism instance; correctness does not depend on choosing a label-invariant order for those ids.

`AGI = NOT_AGI`. The quotient reduction does not solve the quotient isomorphism problem itself, ambient transport, full parent string integration, recurrence closure, or AGI.

Problem count remains **predicted 512 / effective 512**. The H6-R3c3 residual is replaced in place by a smaller exact instance plus a lift obligation.

## Cross-layer relation to existing objects

1. **Symmetry / modular reduction.** Exact twins are the strongest possible modules in a bipartite incidence structure: same-colored vertices with identical external adjacency. Collapsing them is lossless when multiplicity is carried as vertex data.
2. **Permutation-group layer.** A twin class contributes a full symmetric internal factor. The quotient isolates the external action; any quotient isomorphism lifts through an arbitrary bijection in each equal-size matched class.
3. **Canonical-structure layer.** The equivalence relation itself is functorial under every color-preserving isomorphism. No arbitrary representative is used as semantic structure; a representative is used only to materialize the quotient adjacency because all class members have the same neighborhood.
4. **Recurrence layer.** Nontrivial twins give a strict decrease in left degree before any expensive branching. The reduction is therefore a natural cost-free proper descent candidate. The global recurrence certificate must still charge the quotient solve and lift explicitly.
5. **Parent H6 composition.** This closes the specific reason rev204 can fail at rev200's full-left-twin-free precondition: first quotient the left twins, then resume the bipartite structural recursion on the strictly smaller weighted instance.

## Mechanical checks

The implementation records exact class members, weighted quotient colors, quotient incidence, right colors, and descriptor inventories. Source/target mismatch of right color inventory or `(left color, twin multiplicity)` inventory is exact empty evidence. A twin-free pair returns no progress rather than pretending to reduce.

A separate lift validator checks a proposed quotient-left permutation and right permutation against weighted colors and every quotient edge, then constructs one concrete full left lift by pairing sorted members of each matched twin class. The regression verifies that the lifted map preserves every original edge and input color under independent left/right relabeling.

## Problem-tree effect

Subject to repository CI, H6-R3c3 is reduced to a strict smaller-instance recursion. The remaining structural chain becomes:

- **H6-R3c1:** Design-gate relation -> exact k-WL/Design branch cover (rev203).
- **H6-R3c2:** failed Design gate -> dominant relation-twin right restriction when rev200 applies (rev204).
- **H6-R3c3:** nontrivial full-left twins -> exact weighted left-twin quotient + lift (rev205).
- **H6-R4:** compute exact ambient paired transport for whichever structural branch/quotient path fires.
- **H6-R5:** intersect the structural candidate with the complete parent incidence/string state.
- **H6-C1:** certify the global quasipolynomial recurrence across all branch/descent edges.

The current revision does not claim these later leaves solved and does not count an unmerged branch as main-line progress.
