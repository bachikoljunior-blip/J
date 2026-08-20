# AGI-GI rev219 nested S1 proof identity

## Selected leaf

The selected unresolved leaf was CRX3 child 4.2: freeze the complete mathematical
and resource identity of every nested S1 proof node before a shared proof DAG may
reuse it.

rev219 adds `S1ProofIdentity` and attaches one to every result of
`s1_string_isomorphism_v4`, including each recursive invariant-orbit child.  The
identity snapshots:

- the complete deterministic Schreier chain, not only group order or degree;
- the oriented local source and target strings after the caller's right-coset
  coordinate shift;
- original root, current domain and recursion depth;
- S1 v4 / candidate u7 dispatcher versions;
- every exposed resource gate and every fixed downstream Johnson/family default
  that affects the proof execution.

The public S1 wrapper materializes one-shot inputs once, builds the identity, runs
the unchanged exact dispatcher, and attaches the artifact to the returned frozen
`ProofCarryingCoset`.  Recursive calls pass through that same wrapper, so a root
identity cannot stand in for a different induced orbit action.

## Fail-closed boundaries

Identity validation rejects missing, wrong-type, mismatched, or measure-inconsistent
artifacts.  Ordinary nested list/dict/set values are snapshotted immutably.  An
arbitrary opaque object is recorded for diagnostics but marked non-replay-stable;
its process-dependent representation cannot certify DAG reuse.  This revision
does not cache S1 results and does not equate identity equality with SI exactness.

Regressions use a ten-point group with two independent five-cycles.  The root
decomposes canonically into two exact nested S1 children.  Tests verify depth/root
propagation, complete group snapshots, orientation/root/resource misses, mutation
isolation, frozen artifacts, and opaque fail-closed behavior.

## Existing-world containment and problem count

The design contains the action-key/input snapshot principle used by incremental
and content-addressed build DAGs (for example Bazel remote caching,
<https://bazel.build/remote/caching>) while retaining proof-carrying computation's
separate validation boundary.  A content key can identify work; it cannot certify
String Isomorphism exactness, canonical progress, or a complexity envelope.

rev218 replaced one old leaf with three children, giving effective count 519.
rev219 solves already-counted child 2, so effective count remains **519** and the
forecast remains **576**.  The actual count is below the forecast, so the mandatory
over-count rewrite does not fire.

The next leaf is CRX3 child 4.3: build the shared proof-DAG verifier that rejects
identity collisions/cycles, distinguishes proof storage reuse from actually
executed work, preserves conservative cache-hit charge, and translates rev207 and
nested S1 costs to the original root.

## Claim boundary

Nested proof identity is implemented; the shared DAG cost verifier is not.  Full
corrected Split-or-Johnson, W1R-H6, global quasipolynomial recurrence, practical
AGI delivery, and AGI remain unproved.  State: `NOT_AGI`.

