# AGI-GI rev222 growing-beard local-certificate relation boundary

## Selected leaf, direct attempt, and decomposition

The selected unresolved leaf was CRX2's theorem-scale local-certificate
comparison/aggregation.  The direct code audit found a concrete substitution
boundary: `aggregate_fullness_relation` computed the global exact string
stabilizer first and only then colored every test set, while
`local_certificate_beard` already executed an exact growing-beard proof for one
test set without that global enumeration.

The theorem-scale parent is not solved by this revision.  Its prior leaf is
replaced by the parent and three integrating children:

1. produce each Boolean t-subset entry from its own exact growing-beard
   fullness/non-fullness proof and feed the complete relation to one shared
   canonical incidence refiner;
2. execute every required test set inside the theorem parameter window with a
   complete quasipolynomial scheduling and recurrence envelope;
3. compare and aggregate the source/target local-certificate evidence
   canonically, preserving proof identity and resource charge.

rev222 solves child 1 on bounded exact inputs.  Children 2 and 3 remain
unresolved, as does rev221's separately counted consumer-to-original-root proof
integration child.  Replacing one leaf with its parent and three children changes
the effective count from `522 - 1 + 4 = 525`; forecast remains **576**.  The
actual count remains below the forecast, so the over-count traversal does not
fire and no child was suppressed.

## Implemented boundary

`aggregate_beard_local_certificate_relation` never calls the global string
stabilizer.  It checks the complete test-set count and, in strict mode, Babai's
`max(8,2+log2 n) < t <= m/10` parameter window before local execution.  It then
requires one actual frozen `LocalCertificateBeard` for every lexicographically
ordered t-subset.  Any unknown Boolean, missing theorem-scale recurrence evidence,
or resource limit withholds the complete relation.

The Boolean incidence refinement was factored out of the bounded global oracle
without changing its behavior.  Both producers now use exactly the same complete
canonical-order check and deterministic point/test-set refinement, while their
correctness and complexity claims remain separate.

Bounded regressions mechanically verify:

- an S9 stable beard yields one exact `True` relation entry;
- an S5 broken string yields one exact `False` relation entry;
- the compact S5 stable case remains unknown and withholds the relation;
- the theorem window and `max_test_sets` caps reject before certificate work;
- monkeypatching the global exact string stabilizer to raise does not affect the
  growing-beard path.

The expanded direct regression run passed **10 tests**, and the changed modules
passed `py_compile`.  Clean repository pytest remains the authoritative gate.

## Existing-world inclusion audit

- The CRX2 parent and children 1--3 use Babai's local-certificates/growing-beard
  construction rather than global automorphism enumeration
  (<https://arxiv.org/abs/1512.03547>).
- Child 2 must preserve the Extended Design Lemma's complete colored k-ary
  relation and theorem parameter boundary; bounded exact output is not promoted
  to that theorem claim (<https://arxiv.org/html/1909.10260v1>).
- The shared canonical incidence refinement contains standard color-refinement
  partition stabilization, but it is only aggregation and is not called the AGI,
  the local-certificates theorem, or Split-or-Johnson closure.
- At the W1R-H6 and AGI-root levels, local proof generation, global scheduling,
  original-domain SI, generality, performance, autonomy, and practical delivery
  remain distinct unresolved evidence obligations.

No upper-parent branch can yet be deleted: there is no theorem-window complete
all-T run or execution-linked source/target comparison evidence.

## Claim boundary

rev222 removes the global-stabilizer dependency from a bounded exact relation
producer and makes every unknown certificate fail closed.  It does not establish
the theorem-scale all-test aggregation, source/target comparison, global
quasipolynomial SI, practical delivery, or AGI.  State: `NOT_AGI`.
