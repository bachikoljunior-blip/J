# rev215 replay-stable Johnson-lift proof memo

## Strict status

This revision is a systems/correctness optimization inside the J AGI-GI String-
Isomorphism line.  It is not AGI and does not establish generality, performance,
autonomy, or usable delivery.  Root status remains **NOT_AGI**.

## Selected leaf and direct attempt

The selected CRX3 leaf was duplicated relation recognition and Johnson
lift/descent across candidate dispatchers.  Inspection found a concrete duplicate:
rev209 computes `lift_primitive_johnson_to_ground_relation` while attempting its
log-certificate/Design branch, then rev214 recomputes the identical lift after the
older dispatcher returns the homogeneous-pair residual.  The signed profile
terminal can request the same artifact again.

rev215 closes the Johnson-lift portion.  The complete frozen stabilizer chain,
exact source string, exact target string, recognition-node cap, and robust-orbital
degree cap form the proof identity.  A bounded 64-entry LRU stores the immutable
`JohnsonGroundRelationalLift`.  Unhashable inputs bypass the optimization.  Every
resource gate is part of the key; unresolved results remain unresolved; cache hits
retain the original recognition-node count as a conservative work charge.

The regression proves that rev209 and rev214 import one entry point, equal list/
tuple inputs normalize to one identity, the second dispatcher obtains a real hit,
changed strings or resource gates miss, and the frozen proof cannot be mutated.
An unhashable-color regression proves the optimization is bypassed with zero
cache entries while the two independently computed exact results remain equal.

Observed local evidence:

- rev215 direct regression: 2 passed in 0.19 seconds;
- rev175/rev184/rev215 focused compatibility: 8 passed in 14.05 seconds;
- rev215 plus the real rev214 `J(9,3)` path: 2 passed in 90.19 seconds;
- rev210--rev215 integrated smoke: 16 passed in 186.50 seconds; and
- broad workflow-derived recurrence/Design validation: 202 passed in 422.20
  seconds.

These are observations on this environment, not a general performance claim.

## Existing-world containment

Python's standard bounded `functools.lru_cache` supplies the eviction and
thread-safe memo substrate:
https://docs.python.org/3/library/functools.html#functools.lru_cache

Bazel's remote-cache model separates an action hash from immutable content in a
content-addressable store:
https://bazel.build/remote/caching

rev215 borrows only the systems pattern.  A build-cache hit is not treated as a
mathematical proof: J keys every theorem/resource input, stores a frozen proof
object, and preserves fail-closed status and conservative proof accounting.

## Recursive decomposition and count

The attempted CRX3 terminal decomposes into four children:

1. replay-stable Johnson recognition/ground-lift proof identity — solved here;
2. shared log relation/codegree descent artifact — unresolved;
3. shared paired-action preimage/full-candidate filter artifact — unresolved;
4. proof-DAG accounting identity across rev207 replay and nested S1 — unresolved.

Replacing one leaf by these four children moves the non-obsolete effective count
from 513 to **516**.  This remains below forecast 576, so the mandatory over-count
whole-tree rewrite does not fire in rev215.  The next leaf is child 2: factor the
canonical test relation and arity-path proof into one immutable replay artifact,
without caching heuristic or resource-dependent results as exact.
