# rev112 — exact automorphism-orbit-pruned canonical labeling

Root remains **NOT_AGI**.

The second child from rev111 is now implemented. `group_pruned_canonical_label.py` computes an exact automorphism group first, then runs invariant individualization/refinement canonical search. At each node it takes the pointwise stabilizer of all already individualized vertices and branches only once per **exact stabilizer orbit** inside the selected refined color cell. This pruning is safe because branches in the same automorphism-stabilizer orbit are equivalent under a verified automorphism. Every leaf emits a concrete original→canonical permutation and a canonical byte code; the minimum explored leaf is returned. Resource exhaustion fails closed.

Independent local execution validation before marking this child solved:

- 120 deterministic random attributed graphs with n=1..8; each was independently relabeled 5 times. All 600 relabeled instances produced exactly the same canonical code as the source graph.
- For every case, applying the emitted canonical permutation produced identical adjacency and attribute arrays across relabelings.
- Maximum canonical-search states in that random suite was 3 because refinement and exact orbit pruning resolved most cases quickly.
- Complete graphs K6/K9/K12 collapsed to one verified leaf with at most n search states despite automorphism orders up to 12! = 479,001,600.
- Cycles C5/C8/C12 likewise reached one verified canonical leaf under exact dihedral orbit pruning.

This solves exact canonical labeling at the current resource-bounded group-pruned layer. It does not yet prove the required quasipolynomial worst-case ceiling for arbitrary graphs; that child remains open.