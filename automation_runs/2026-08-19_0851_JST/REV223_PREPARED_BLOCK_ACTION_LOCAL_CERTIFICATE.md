# AGI-GI rev223 prepared block-action local-certificate boundary

## Selected leaf, direct attempt, and decomposition

The selected unresolved leaf was CRX2 child 2.2: theorem-window complete
all-test-set local-certificate scheduling and recurrence.  A direct one-test-set
attempt used 90 singleton blocks, `t=9`, a degree-92 domain action, an `S9`
constituent on the test set, and one independent transposition.  This satisfies
the implemented strict parameter gate
`max(8, 2+log2(n)) < t <= m/10`, but one growing-beard execution did not finish
within 60 seconds.  The run was terminated and is evidence of an unresolved
execution boundary, not evidence of impossibility or theorem completion.

Code inspection then found repeated exact work inside that one test set:
`_test_alternating_preimage` rebuilt the same block-action image stabilizer
chain, paired Schreier chain, and kernel separately for every standard
generator of `A(T)`.  rev223 replaces child 2.2 with an integrating parent and
three children:

1. construct one exact prepared block-action homomorphism per test set and lift
   every `A(T)` generator through that immutable shared artifact;
2. give one theorem-window growing-beard execution a complete terminating
   primitive resource envelope, including all stabilizer-chain work;
3. schedule every required test set and charge multiplicity and all local work
   to the original-root quasipolynomial recurrence.

rev223 solves child 1.  Children 2 and 3 remain unresolved, as do CRX2 child
2.3 and the separately counted execution-linked consumers.  Replacing one leaf
with its parent and three children changes the effective count from
`525 - 1 + 4 = 528`; forecast remains **576**.  The actual count remains below
the forecast, so the over-count traversal does not fire and no child was
suppressed.

## Implemented exact reuse boundary

`prepare_block_action_preimage` now validates the ordered block family and
constructs the exact quotient image, paired quotient Schreier levels, and exact
kernel once.  The frozen `PreparedBlockActionPreimage` retains those objects.
`lift_prepared_block_action_preimage` sifts any target quotient permutation
through the prepared paired levels and returns the same exact preimage right
coset contract as the former one-shot API.  The public one-shot function now
delegates to prepare plus lift, preserving existing callers.

`local_certificate_beard` prepares once per `_test_alternating_preimage` call
and reuses that artifact for all standard alternating generators.  It does not
cache across test sets, promote an unknown local Boolean, or infer a theorem
runtime bound from artifact reuse.

The regressions mechanically verify:

- prepared lifts equal the one-shot representative, kernel, and preimage-coset
  orders for every standard `A9` test generator;
- monkeypatch instrumentation observes exactly one paired-chain construction
  for a full beard despite multiple alternating generators;
- quotient targets outside a cyclic quotient image fail exactly as before;
- the previous preimage, beard, and rev222 relation tests remain unchanged.

The direct affected/integration gate passed **15 tests**, changed modules passed
`py_compile`, and the clean repository gate excluding only the separately
installed `nauty-labelg` differential file passed **465 tests**.  GitHub CI
remains the authoritative publication gate.

## Existing-world inclusion audit

- GAP's official group-action documentation represents an action by a group
  homomorphism and uses stabilizer chains/strong generators as reusable group
  algorithm infrastructure, rather than reconstructing the action for every
  image element (<https://gap-system.github.io/gap/doc/ref/chap43_mj.html>).
- GAP's homomorphism documentation records generator images together with the
  source stabilizer chain and computes kernels/preimages from that shared map;
  this is the existing-world mechanism contained by rev223's prepared paired
  Schreier artifact
  (<https://www.math.rwth-aachen.de/~GAP/WWW2/Gap3/Manual3/C021S023.htm>).
- Babai's local-certificates/growing-beard construction remains the algorithmic
  parent.  Prepared quotient lifting removes duplicate infrastructure but does
  not replace its theorem recurrence (<https://arxiv.org/abs/1512.03547>).
- The Extended Design Lemma's complete colored relation and parameter boundary
  remain downstream obligations; bounded execution is not promoted to that
  claim (<https://arxiv.org/html/1909.10260v1>).

The same prepared-action idea can serve upper quotient consumers, but no upper
branch is deleted yet because theorem-window single-test execution and complete
all-test scheduling are still missing.

## Claim boundary

rev223 proves exact within-test-set reuse of the block-action homomorphism and
removes a measured duplicate-construction path.  It does not establish a
theorem-window runtime, complete all-test aggregation, source/target comparison,
global quasipolynomial SI, practical delivery, or AGI.  State: `NOT_AGI`.
