# rev216 shared logarithmic-relation descent proof

## Strict status

This revision factors one exact proof artifact inside the J AGI-GI String-
Isomorphism line.  It is not AGI and does not establish generality, performance,
autonomy, or usable delivery.  Root status remains **NOT_AGI**.

## Selected leaf and direct attempt

The selected unresolved CRX3 leaf was the shared logarithmic relation and
codegree-descent artifact.  The direct inspection found two production
computations of the same mathematical object after one certified Johnson lift:

- rev184 generated the complement-safe complete `t`-relation, checked the
  logarithmic/test-count gate, and descended its exact codegrees; and
- rev214 generated the same relation and descent again, then replayed the
  codegrees a third time solely to recover the terminal pair relation.

rev216 closes this leaf by introducing one frozen
`SignedJohnsonLogRelationArtifact`.  Its identity contains the complete frozen
Johnson lift (including source/target orientation), `root_n`, test-set cap,
recognition-node cap, Johnson-node cap, and `max_class_fraction`.  Its payload
contains the theorem gate, top relation, canonical descent, arity path, terminal
pair coordinates and values, conservative scan bound, and fail-closed reason.

The bounded 64-entry LRU changes only reuse.  An unhashable lift bypasses it;
different orientation or resource/theorem gates produce different identities;
and unresolved artifacts remain unresolved.  rev184 and rev214 now consume the
same entry point.  rev214 reads the exact pair relation carried by the descent,
so its duplicate production replay was removed.  An invariant mismatch remains
an exact empty terminal rather than being promoted to a positive solution.

The regression compares the new carried pair relation and arity path with a
test-only specification of the removed replay on a cyclic 3-relation, proves
cross-consumer object reuse, mutation rejection, resource/orientation misses,
and fail-closed cache bypass.  It also executes the actual rev184 then rev214
consumers and verifies that replay preserves the same recurrence object and
local work charge.

Observed local evidence before CI:

- rev216 direct regression: 3 passed in 3.89 seconds; and
- rev184/rev211/rev214/rev215/rev216 focused integration: 12 passed in 98.40
  seconds; and
- rev212--rev216 workflow-equivalent smoke including stable 2-WL: 19 passed in
  194.44 seconds; and
- all local Python modules except the separately gated external `nauty-labelg`
  differential file: 438 passed in 494.65 seconds.

These are observations on this environment, not a general performance claim.

## Broad-validation residual closed

An exploratory all-module run passed 437 tests and exposed two failures.  One was
the expected unavailable local `nauty-labelg` executable.  The other reproduced
unchanged on the rev215 baseline: `coherent_refine_pair_relation` reached its
round cap on a six-point weighted relation because it compared transient integer
color IDs instead of the partition induced by those colors.

This concrete CRX2 residual was attempted rather than hidden as a baseline
failure.  Standard Weisfeiler--Leman termination is defined by stabilization of
the induced color partition.  Since every new signature contains its old color,
the new partition refines the old one; equal rank therefore certifies unchanged
partition even if canonical integer compression permutes the IDs.  rev216 uses
that invariant and retains the explicit round resource cap for genuine strict
refinement sequences.

The previously unreachable test expectation was also inconsistent with the
input relation.  Independent enumeration of all `6!` permutations proves an
automorphism group of order two with orbits `{0}`, `{1,3}`, `{2}`, `{4}`, and
`{5}`.  Stable 2-WL returns exactly these cells, so the regression now verifies
the independent orbit partition and rank 26 instead of the stale `{2,4}` cell.

## Existing-world containment

Python's bounded `functools.lru_cache` provides only the eviction/memo substrate:
https://docs.python.org/3/library/functools.html#functools.lru_cache

Bazel's remote-cache design separates an action key from immutable
content-addressed results:
https://bazel.build/remote/caching

rev216 uses that systems pattern but does not treat a cache hit as mathematical
evidence.  The exact canonical relation/descent computation remains the proof;
the cache identity includes every caller-visible gate, and the same conservative
work bound is charged on a hit.  Babai/Luks-style canonical relation reduction,
not the cache, supplies the mathematical progress interface.

For the new coherent-refinement child, the existing-world method is the standard
WL stopping rule: stop when the color **partition** stabilizes, with finite
tuple-space rank bounding strict refinements.  See:
https://arxiv.org/abs/2005.08887

## Recursive problem count

The direct attempt solved CRX3 child 2 without adding a new child.  The four-way
decomposition introduced in rev215 is now:

1. replay-stable Johnson recognition/ground-lift identity — solved in rev215;
2. shared log relation/codegree descent artifact — solved here;
3. shared paired-action preimage/full-candidate filter artifact — unresolved;
4. proof-DAG accounting identity across rev207 replay and nested S1 — unresolved.

Broad validation then directly attempted the existing CRX2 local-certificate /
Design-escalation leaf and split it into (a) stable coherent-refinement
termination, solved here, and (b) the remaining Design escalation, still
unresolved.  Replacing one leaf by these two children increases the non-obsolete
effective count from 516 to **517**; the forecast remains **576**.  Since 517 does
not exceed 576, the mandatory over-count whole-tree rewrite does not fire in
rev216.  The new child received the existing-world WL containment check above.

The next selected leaf remains CRX3 child 3: share and replay-certify the exact
paired-action preimage and full-candidate filter without allowing a cached
nonrestricting or resource-capped result to become exact.
