# rev217 shared paired-action full-candidate proof

## Strict status

This revision factors one exact String-Isomorphism proof substrate inside the J
AGI-GI line.  It is not AGI and does not establish strict generality,
performance, autonomy, or usable delivery.  Root status remains **NOT_AGI**.

## Selected leaf and direct attempt

The selected unresolved CRX3 leaf was the shared paired-action preimage and
full-candidate filter artifact.  The existing relation-image, joint-relation and
log-codegree paths all performed the same mathematical composition in separate
production code:

1. reconstruct the complete original-domain preimage of an oriented image right
   coset from generator-paired actions;
2. reject an ambient-equal preimage as a same-domain recursion loop unless the
   whole-candidate terminal already solves the full string;
3. run the full-string candidate dispatcher only inside a proper preimage; and
4. replay the exact child's recurrence certificate before promotion.

rev217 implements that composition once as the frozen
`PairedActionFullCandidateArtifact`.  Its identity contains the complete frozen
domain stabilizer chain, the ordered image generator pairing, the oriented image
right coset, both full strings, `root_n`, the dispatcher identity, and every
dispatcher resource parameter.  A 128-entry exact-preimage cache and a 64-entry
full-artifact cache change reuse only.  Unhashable strings bypass full-artifact
memoization; cached unresolved results remain unresolved; and every successful
full-string child must pass recurrence-v4 replay.

The complement-safe lower-arity relation and joint-relation filters now retain
their generator pairing and image coset as proof identity.  Their candidate
wrappers and the log-codegree bridge call the same shared builder.  Filter-only
and candidate consumers receive the same memoized complete preimage rather than
reconstructing it independently.  The log-codegree path's former local
preimage/loop/candidate/accounting block was removed.  A replayed preimage is
asserted equal to the relation filter before composition.

## Existing-world containment

GAP's mapping interface states that preimages under a group homomorphism are
empty or a coset of the kernel, and its group-homomorphism interface supports
generator images, kernels and preimage representatives:

- https://docs.gap-system.org/doc/ref/chap32.html
- https://docs.gap-system.org/doc/ref/chap40.html

That existing system supplies the right algebraic abstraction, not J's proof by
itself.  J retains its own paired Schreier certificate, verifies
`|G| = |kernel| * |image|`, lifts the target subgroup and representative, and
checks the full preimage order.  Python's bounded LRU and Bazel-style action-key
separation remain only systems analogues for bounded reuse; no cache hit is
treated as mathematical evidence.

The same image/preimage/candidate substrate is applicable above the Johnson
leaves to Luks-style block/orbit recursion and the H6 coupled-parent action.  It
therefore replaces three local replay branches with one solution-shaped proof
boundary rather than merely merging duplicate names.  The remaining higher
parents are not marked solved.

## Mechanical evidence

The rev217 regression verifies:

- exact nontrivial `S4 x C2 -> S4` coset preimage and full-string closure;
- object reuse under parameter-order normalization and misses for changed root,
  resource gate, right-coset orientation, or full strings;
- immutable output and unhashable-input cache bypass;
- fail-closed ambient-equal and resource-capped children; and
- one shared builder object in the lower-arity, joint-relation and log-codegree
  consumers, including an actual relation-filter-to-candidate preimage cache hit.

Before CI, the new direct regression passed 4 tests in 2.05 seconds, the focused
rev179/rev180/rev181/rev183/rev211/rev216 compatibility set passed 15 tests in
33.50 seconds, the proposed workflow set passed 17 tests in 121.62 seconds, and
all local Python modules except the separately gated external `nauty-labelg`
differential file passed 442 tests in 479.15 seconds.  These are observations on
this environment, not general performance claims.

## Recursive problem count

CRX3 child 3 is solved by this direct attempt without creating a new child.  The
four children introduced in rev215 are now:

1. replay-stable Johnson recognition/ground-lift identity — solved in rev215;
2. shared log relation/codegree descent artifact — solved in rev216;
3. shared paired-action preimage/full-candidate filter artifact — solved here;
4. proof-DAG accounting identity across rev207 replay and nested S1 — unresolved.

The non-obsolete effective count remains **517** and the forecast remains
**576**.  Since 517 does not exceed 576, the mandatory over-count whole-tree
rewrite does not fire.  The next selected leaf is CRX3 child 4: deduplicate and
replay-certify proof-DAG accounting across rev207 polynomial lifts and nested S1
without undercharging shared or repeated work.
