# rev203 exact relation-twin restriction audit

Run identity: `chatgpt-session-immediate-20260820T085307+0900-06aca83f`  
Execution start: `2026-08-20T08:53:07+09:00`  
Session starting main: `06aca83ffef7e644ae63421514cfab8c2fe0c2ea`  
AGI-GI transition: `rev202 -> rev203`

## Scope and strict status

rev202 constructs the exact symmetric containment-count relation on the right ground but does not implement the recursive large-twin-class case in Proposition 5.7. rev203 solves that local case and composes it with rev200.

This is not the no-large-twin Design/coherent branch, ambient transport, full string isomorphism, global recurrence closure, or AGI. `AGI = NOT_AGI`; the root remains unresolved.

Problem count remains **predicted 512 / effective 512**. The H6-R3b2 child replaces one active internal leaf; the count-overrun rewrite trigger is not active.

## Existing-world object and exact implementation

In the Proposition 5.7 proof of H. A. Helfgott, J. Bajpai, D. Dona, arXiv:1710.04574, the derived `d`-ary relation is used as follows: if a relation-twin class `S` has more than half of `V2`, Exercise 5.5 supplies one of `S` or `V2\S` as a recursively admissible restriction; if no class is larger than half, the proof continues to WL and the Design Lemma.

rev203 implements the first case across layers:

1. **Relation semantics:** a pair `x,y` is twin exactly when the transposition `(x y)` preserves every color of the symmetric distinct-tuple relation.
2. **Finite exact check:** for every `(d-1)`-subset `T` disjoint from `{x,y}`, compare the colors of `T∪{x}` and `T∪{y}`. Repeated tuples have the common gray color and add no condition.
3. **Partition safety:** verify the computed twin predicate is transitive and its classes maximal before using it.
4. **Canonical large class:** a class of size greater than half is unique, hence every relation isomorphism maps it to the target unique large class.
5. **rev200 composition:** use the ordered partition `(large class, complement)` and accept only an exact proper Exercise 5.5 restriction.
6. **Paired provenance:** source and target must agree on outcome status, all relation-twin class sizes, unique large-class size, and every rev200 selection invariant.
7. **Fail-closed boundary:** no-large-class outcomes proceed to Design/coherent work; non-relation outcomes, resource failures, or rev200 failures are not promoted.

## Solved child and remaining decomposition

Solved local child:

> For the exact nonconstant containment relation, compute transposition-twin classes and, when the unique over-half class exists, produce a complete paired proper restriction through rev200.

Remaining active internal leaves:

- **H6-R3c1 — no-large-twin WL provenance:** feed the exact derived relation into the existing exact WL/Design machinery with parent provenance, not a caller boolean.
- **H6-R3c2 — Design outcome pairing:** pair all canonical Design witnesses across source and target without choosing a label-dependent representative.
- **H6-R4 — ambient relation/restriction transport:** construct exact transporter cosets under the parent group.
- **H6-R5 — full-string integration:** intersect all branches with the complete incidence strings and reconstruct exact empty/coset output.
- **H6-C1 — recurrence closure:** certify cost-free proper descent and post-branching constant-factor progress separately.

The next unresolved leaf is **H6-R3c1, mechanical parent-provenance wiring into exact WL/Design descent for the no-large-twin relation**.

## Verification

Command:

```text
python -m pytest -q test_relation_twin_restriction_provenance_rev203.py
```

Result: `7 passed`.

Coverage includes a unique 4-of-7 relation-twin class, paired left/right relabelings, a no-large-class cycle relation, exact twin-inventory mismatch, a synthetic transposition-class oracle, all 64 binary colorings of the unordered pairs on four points checked against direct transposition action, and non-relation fail-closed behavior.
