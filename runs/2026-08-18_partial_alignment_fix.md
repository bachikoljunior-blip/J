# Fixed-root run: partial cross-environment alignment

Selected leaf: `C2.2b2b2b5b2c3` — align partial/missing intervention tensors with distractor entities/actions without false correspondence.

A full candidate regression run exposed one failure in the seed-131 missingness+distractor fixture. The local Hungarian assignment forced every source action to consume a real target action even when the true row was missing; one high-cost distractor therefore caused a false negative.

The implementation was changed to partial bipartite matching by adding one dummy unmatched column per source action at the declared compatibility cutoff. Genuine compatible rows beat the dummy; incompatible distractors do not. Existing coverage gates still reject extreme missingness.

Verification: focused partial-alignment suite 4/4 passed; full candidate suite 122/122 passed after the fix.

Leaf result: `solved_v0_1` for the bounded structured-table subproblem only. Raw perceptual anchor identity, distributed/nonlinear correspondence, continuous actions, and AGI certification remain unresolved.

Root certification status: `NOT_AGI`.
