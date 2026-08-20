# AGI-GI rev224 preimage Schreier resource envelope

## Selected leaf and bounded decomposition

The selected unresolved leaf was CRX2 child 2.2.2, a complete resource
envelope for one theorem-window growing-beard execution.  rev223's direct
degree-92, 90-singleton, `t=9` fixture stalled before one test-set certificate
completed.  The first independently isolatable phase is construction of the
embedded `A(T)` preimage: quotient image chain, paired quotient chain, exact
kernel chain, all prepared lifts, and the final generated preimage chain.

The direct attempt did not solve the entire single-test-set leaf.  It is
replaced by an integrating parent and three children:

1. a fail-before-execution finite primitive-work envelope for the complete
   embedded-`A(T)` preimage phase;
2. corresponding envelopes for every affected-segment layer and the final
   unaffected-stabilizer materialization;
3. one execution-linked sum proving the complete single-test-set theorem
   recurrence evidence before it is multiplied by all test sets.

rev224 solves child 1.  Children 2 and 3 remain unresolved.  Replacing one leaf
with its parent and three children changes the effective count from
`528 - 1 + 4 = 531`; forecast remains **576**.  The actual count remains below
forecast, so the over-count traversal does not fire and no child was hidden.

## Implemented resource boundary

`preimage_schreier_resource_envelope` computes a conservative finite upper
bound before any preimage chain is executed.  For every base level it bounds
both orbit-transversal and Schreier-generator visits by the quotient/domain
degree times the current deduplicated generator family.  The next family is
bounded simultaneously by `degree * current` and the finite source-group order.
Fixed permutation scans and compositions are charged by coordinate degree.

The sum covers:

- the quotient image stabilizer chain;
- the paired quotient Schreier chain retaining domain words;
- the exact kernel stabilizer chain;
- every standard alternating-generator prepared sift;
- the final embedded-`A(T)` preimage stabilizer chain.

Arithmetic saturates at `cap + 1`, so even an enormous mathematical upper bound
cannot consume unbounded integer memory merely to reject the execution.  If the
bound exceeds the explicit cap, `local_certificate_beard` returns
`undetermined_preimage_schreier_work_cap` before `_test_alternating_preimage` is
called.  If admitted, the same exact implementation runs and the frozen
envelope is retained in the certificate.  The strict theorem relation path now
passes an explicit finite preimage cap; bounded regression mode remains
separate and does not manufacture theorem evidence.

Regressions verify rejection before a monkeypatched-forbidden preimage call,
exact S9 fullness preservation under an admitted bound, and saturating monotone
cap behavior.  The affected/rev223/rev222 integration gate passed **15 tests**
and changed modules passed `py_compile`.

## Existing-world inclusion audit

- GAP's official permutation-group algorithms use stabilizer chains and strong
  generators as the resource-relevant representation for membership,
  stabilizers, and homomorphism actions
  (<https://gap-system.github.io/gap/doc/ref/chap43_mj.html>).
- GAP homomorphisms retain source generator images and stabilizer-chain data for
  kernel and preimage calculations; rev224 bounds the equivalent paired-chain
  work rather than repeatedly enumerating quotient elements
  (<https://www.math.rwth-aachen.de/~GAP/WWW2/Gap3/Manual3/C021S023.htm>).
- Babai's local-certificates theorem remains the algorithmic parent.  A finite
  cap and exact rejection state are required execution evidence, but they do
  not by themselves prove the theorem's quasipolynomial recurrence
  (<https://arxiv.org/abs/1512.03547>).

No upper branch is deleted: affected-layer work, complete one-T accounting,
all-T multiplicity, source/target comparison, and original-root integration
remain separate obligations.

## Claim boundary

rev224 makes the previously observed preimage-phase stall fail closed under a
complete conservative primitive-work cap.  It does not establish complete
single-T execution, theorem-scale all-T aggregation, global quasipolynomial SI,
practical delivery, or AGI.  State: `NOT_AGI`.
