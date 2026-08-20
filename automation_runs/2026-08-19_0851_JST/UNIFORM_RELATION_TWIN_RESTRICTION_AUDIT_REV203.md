# rev203 exact uniform-relation twin restriction audit

Run identity: `2026-08-20T09:24:53+09:00__rev201__43a16b622129`  
Execution start: `2026-08-20T09:24:53+09:00`  
Implementation base main: `904d8c57507a585398b4ae3fb32a9528817b51ce` (AGI-GI rev202)  
AGI-GI transition under test: `rev202 -> rev203`

## Scope and strict status

Main advanced during this execution to rev202, whose next unresolved leaf is H6-R3b2: exact relation-twin partition and paired proper restriction. This revision follows that new main line rather than treating an earlier unmerged alternative branch as progress.

rev202 requires a twin-free nontrivial common-degree left cell and derives either explicit Johnson coordinates or a nonconstant theorem-arity containment-count relation on the right ground. rev203 handles the nonconstant-relation branch.

It reconstructs the complete colored right `d`-subset relation from rev202's exact relation classes, runs rev185's exact transposition-twin certificate, and separates two complementary cases:

- **symmetry-defect gate holds:** do not force a right restriction; continue to the exact WL/Design/coherent child;
- **symmetry-defect gate fails:** for `alpha >= 1/2`, the relation has a unique dominant twin class larger than `alpha |V2|`. This class and its complement are a canonical ordered proper partition, which is fed to rev200's exact Exercise-5.5 restriction on the original bipartite incidence instance.

Because the rev202 relation branch already certified pairwise-distinct full left neighborhoods, rev200's full-left-twin-free precondition is inherited mechanically. Any unexpected rev200 failure is therefore an invariant violation and remains fail-closed.

`AGI = NOT_AGI`. The result is not the WL/Design branch, Johnson ground transporter, ambient parent-group transporter, full string-isomorphism set, global recurrence closure, or AGI.

Problem count remains **predicted 512 / effective 512**. H6-R3b2 replaces the active leaf in place.

## Existing-world and cross-layer mapping

1. **Uniform-neighborhood theorem object (rev202).** The right relation is exactly the containment-count relation from the corrected Bipartite Split-or-Johnson construction, including complement normalization and theorem arity.
2. **Symmetry layer (rev185).** Two right points are relation twins exactly when their transposition preserves every colored relation entry. The resulting classes are canonical under every relation isomorphism.
3. **Design boundary.** The exact twin certificate is used as a branch gate, not a heuristic. If every class is alpha-bounded, the Design/WL path is the appropriate next child. If the gate fails, the unique dominant symmetric class itself is usable structure.
4. **Bipartite recursion (rev200).** Dominant class versus complement gives a proper ordered right partition. rev200 computes exact left twins under both restrictions, applies the integral Exercise-5.5 bound, and records separately whether the selected child is a constant-factor alpha shrink or merely a proper descent.
5. **Paired exactness.** Source/target must agree on rev202 outcome, relation inventory, exact relation-twin size profile, symmetry-gate result, rev200 status, and every deterministic restriction invariant. Proven mismatch is exact non-isomorphism evidence.

## Regression family

The main regression uses six left vertices equal to all 2-subsets of four ordinary points on a five-point right ground; the fifth point is special and occurs in no hyperedge.

- all six left neighborhoods are distinct and have common degree two, satisfying rev202;
- the exact pair containment relation colors ordinary/ordinary pairs by `1` and ordinary/special pairs by `0`;
- the four ordinary points form one transposition-twin class and the special point is singleton;
- at relation alpha `0.75`, the `4+1` profile fails the symmetry-defect gate and gives a unique canonical dominant class;
- rev200 applied to `(ordinary four, special singleton)` selects the ordinary side because the singleton restriction collapses all six left vertices into one twin class;
- with restriction alpha `0.8`, the size-four selected child is an alpha shrink; with `0.75`, the same theorem-faithful child is only a one-vertex proper descent, and the test explicitly checks that no constant-factor progress is fabricated.

The test runs this path under all `5! = 120` right-ground relabelings plus an independent left relabeling. Additional regressions cover the Design-gate redirect, explicit Johnson redirect, and exact rev202 outcome mismatch.

## Problem-tree effect

Subject to repository CI, H6-R3b2 is locally solved for the exact large-relation-twin branch. The next unresolved structural leaves are:

- **H6-R3c — Design/coherent provenance:** when rev203 reports `relation_design_gate_available`, run the exact k-WL/Design machinery on rev202's actual containment relation and tie its output back to the parent incidence state.
- **H6-R4 — ambient paired transport:** handle explicit Johnson coordinates and surviving relation/partition branches inside the parent group action.
- **H6-R5 — exact full-string integration.**
- **H6-C1 — recurrence closure,** including the distinction between cost-free proper descent and post-branching alpha progress.

No unmerged alternative branch is counted as main-line progress.
