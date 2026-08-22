# rev281 corrected bipartite Split-or-Johnson transition certificate

## Scope

This revision advances only the persisted W1R-H6 corrected general UPCC Split-or-Johnson residual identified by the rev198 audit. It does not claim the full Split-or-Johnson recursion, GI, or AGI.

The pre-existing `bipartite_split_or_johnson_gate_v1.py` certifies theorem input hypotheses but explicitly leaves the recursive conclusion as a separate proof obligation. rev281 adds a standalone fail-closed certificate for one recursive edge without modifying that shared gate or the concurrently occupied CRX1/CRX3 paths.

## Accepted progress forms

A transition is admitted only after the theorem input gate has fired and only if canonicality, exactness, and a finite multiplicative-cost bound are supplied mechanically. Two conclusion forms are recognized:

1. **constant-factor auxiliary-part reduction**: the small/auxiliary part must strictly shrink and satisfy `after < alpha * before` for `alpha in [2/3,1)`; phase names or same-size transitions do not count;
2. **explicit Johnson embedding**: every structural vertex is mapped injectively to a nontrivial `k`-subset of an explicit ground, every unordered embedded pair is covered, and the supplied relation distance must equal `k - |A intersect B|` exactly.

The second condition deliberately rejects a bare `Johnson` recognition label. It provides a concrete relation-level witness that a later caller can compose with exact action/preimage machinery.

## Validation boundary

The accompanying regression suite covers successful reduction and Johnson witnesses plus failure for missing theorem gates, insufficient shrinkage, incorrect Johnson relations, noncanonical transitions, and cost/certificate failures. The dedicated pull-request workflow runs those tests under Python 3.12.

Further work is still required to construct these certificates from the actual corrected recursive UPCC descent and to compose admitted transitions into rev196-style recurrence accounting. Root status remains `NOT_AGI`.
