# rev204 large-relation-twin restriction audit

Run identity: `2026-08-20T09:24:53+09:00__rev201__43a16b622129`  
Execution start: `2026-08-20T09:24:53+09:00`  
Stacked base: rev203 candidate branch  
AGI-GI transition under test: `rev203 -> rev204`

## Scope and strict status

rev203 covers the branch where the canonical nonconstant right relation satisfies the exact symmetry-defect / Design theorem gate and can be sent into exact correlated-replacement k-WL. rev204 addresses the complementary structural signal: the exact symmetry-defect gate fails because the selected right relation contains a unique dominant transposition-twin class larger than the configured alpha fraction.

For alpha >= 1/2 such a dominant class is unique. Its class membership is defined solely by exact transposition preservation of every colored t-subset relation entry, so the class and its complement are canonical under relation isomorphism. rev204 uses that canonical ordered right partition as input to rev200's exact Exercise-5.5 restriction certificate on the original bipartite graph.

This is not a claim that Design-gate failure always solves the parent. The rev200 restriction still requires full-left twin-freeness and its exact theorem gate. Failure of those conditions remains an explicit unresolved residual.

`AGI = NOT_AGI`. Full W1R-H6, full corrected Split-or-Johnson, ambient transport, full-string integration, global recurrence closure, generality/performance/autonomy evidence and usable AGI delivery are unclaimed.

Problem count remains **predicted 512 / effective 512**. The active H6-R3c residual is refined in place.

## Existing-world object and cross-layer mapping

The construction reuses three existing theoretical/implemented layers rather than introducing a new theorem.

1. **Design-Lemma symmetry boundary.** The graph-isomorphism literature treats large symmetry/twin classes as the complementary regime to the symmetry-defect hypothesis used by the Design Lemma. rev185 already made that hypothesis exact for complete colored subset relations by testing transpositions entry-by-entry.
2. **Canonical quotient/partition viewpoint.** A unique dominant equivalence class is itself a label-invariant structural object. rev204 turns the large exact relation-twin class into the ordered partition `(dominant class, complement)` rather than stopping at a failed theorem gate.
3. **Bipartite restriction.** rev200 implements the Exercise-5.5 style step: for an ordered proper partition of the right side of a full-left-twin-free bipartite graph, at least one restriction must have bounded left twin classes; the implementation computes both sides exactly and selects the deterministic eligible side.
4. **Paired provenance.** Source and target first compare the complete relation color inventory, then exact relation twin-class size profiles, then rev200 status and selection invariants. Any proven mismatch is exact non-isomorphism evidence; otherwise an unverified implication fails closed.
5. **Recurrence boundary.** The selected restriction records whether it is an alpha shrink separately. rev204 does not turn a merely proper one-vertex restriction into post-branching constant-factor progress.

Primary theoretical context remains Babai's quasipolynomial GI framework and the corrected Helfgott-Bajpai-Dona Split-or-Johnson exposition; the repository-side exact objects are rev185 and rev200.

## Regression construction

A targeted `8 x 5` incidence structure makes the large-twin path observable without weakening any gate. Let right points `0..3` be ordinary and point `4` special. The eight left neighborhoods are the S4-orbits of types `(1,0)` and `(3,1)`:

- four singleton ordinary blocks `{i}`;
- four blocks `{4} union ({0,1,2,3} \ {i})`.

Consequences checked mechanically by the test:

- all five right vertices have degree four, so rev201 first-order degree signatures are homogeneous;
- every left neighborhood is distinct, so the full left side is twin-free;
- ordinary/ordinary pair codegree is two while ordinary/special pair codegree is three, so rev202 selects a nonconstant pair relation;
- the four ordinary right points form one exact relation-twin class and the special point is alone;
- with relation alpha `0.75`, the size-four class fails the Design symmetry gate and yields the canonical `4+1` right partition;
- rev200 selects the size-one complement and certifies a strict alpha shrink.

The paired regression applies independent left and right relabelings and requires the exact source/target structural invariants to agree.

## Problem-tree effect

H6-R3c is now decomposed as:

- **H6-R3c1 — Design-gate branch:** canonical relation -> exact k-WL/Design branch cover (rev203; dedicated smoke succeeded, broad regression pending at the time of this audit).
- **H6-R3c2 — large relation-twin branch:** canonical dominant relation-twin class -> paired rev200 right restriction (rev204; pending CI).
- **H6-R3c3 — full-left-twin residual:** when the canonical right partition exists but rev200 rejects because the original left side has nontrivial same-colored twins, construct the exact paired left-twin quotient/partition and show how it composes with the parent recurrence rather than treating the rejection as terminal.
- **H6-R4 — ambient paired transport.**
- **H6-R5 — full-string integration.**
- **H6-C1 — recurrence closure.**

No unmerged branch is counted as solved progress on main. rev204 becomes a solved child only after its repository validation is observed and the stacked ancestry is safely integrated.
