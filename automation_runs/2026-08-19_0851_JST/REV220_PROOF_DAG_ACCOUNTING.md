# AGI-GI rev220 execution proof-DAG accounting

## Selected leaf and result

The selected unresolved leaf was CRX3 child 4.3: validate shared proof storage
without allowing sharing to erase the work of any executed recurrence occurrence.

rev220 adds a fail-closed `ProofDAGArtifact` and an independent execution-charge
validator.  Stable nested S1 identities from rev219 and a new complete candidate-SI
identity name stored proof nodes.  The candidate identity freezes the full
Schreier chain and candidate representative, oriented strings, original root,
versioned dispatcher and every effective resource gate.  Instrumentation may wrap
the callable, so the algorithm version is an explicit stable label rather than a
Python function object's incidental identity.

The builder deduplicates storage only.  It rejects missing or opaque root identity,
unhashable identity, active-path cycles, proof/accounting child disagreement and
one identity naming different payloads or edges.  Nodes without an attached
mathematical identity remain path-scoped and therefore cannot be shared.

## Conservative occurrence charge

The validator first applies recurrence verifier v4 to the ordinary proof tree,
then independently unfolds every DAG edge without memoizing cost.  Every positive
edge multiplicity charges the complete child subtree that many times; weighted
execution-occurrence metrics include multiplicities inherited from all ancestors.
The resulting work must equal the independently validated tree bound.

For rev207, a larger auxiliary root is accepted only when it equals the recorded
execution degree and satisfies `M <= n + n^2`.  The translated branch is then
composed with actual structural branch multiplicity, Design cost, lift wrapper and
union bookkeeping under the original-root envelope.  The proof remains the exact
object captured during rev206 execution; no candidate solver replay is restored.

Regressions prove that two edges may share one stored child while both are charged,
that multiplicity three yields three represented executions and repeats all
descendant charge, and that payload collision, missing identity and an invalid
polynomial lift fail closed.  The rev218 object-identity regression caught and
prevented post-return identity attachment: u2/u7 now attach the candidate identity
before returning the observed execution object.

Local validation passed the dedicated rev207--rev220 integration gate (**16
tests**) and every AGI-GI Python module except the separately gated external
`nauty-labelg` differential file (**453 tests in 480.85 seconds**).

## Existing-world containment and problem tree

This design contains the content-addressed action/result separation used by Bazel
remote caching (<https://bazel.build/remote/caching>) and bounded memoization's
keyed reuse model (<https://docs.python.org/3/library/functools.html#functools.lru_cache>),
but deliberately does not infer mathematical equality, exact SI, or lower
worst-case work from a cache hit.  Identity controls storage; recurrence evidence
and weighted unfolding independently certify execution cost.  This shared
solution applies at the nested S1, rev207 polynomial-lift and higher W1R-H6 proof
boundaries rather than merging duplicate leaf names only.

Child 4.3 was already counted, so the effective problem count remains **519** and
the forecast remains **576**.  The actual count is below the forecast; the
mandatory over-count traversal does not fire, and no child was suppressed.  With
children 4.1--4.3 solved, CRX3 child 4 is integrated; together with rev215--rev217,
the four counted CRX3 substrate children are solved.  This does not solve their
algorithmic consumers.  The next selected unresolved leaf is the remaining CRX2
canonical local-certificate / Design-escalation boundary.

## Claim boundary

The reusable proof/resource substrate is implemented and mechanically tested.
Corrected Split-or-Johnson, complete W1R-H6, global quasipolynomial SI, independent
generality/performance/autonomy evidence, practical product delivery and AGI are
not established.  State: `NOT_AGI`.
