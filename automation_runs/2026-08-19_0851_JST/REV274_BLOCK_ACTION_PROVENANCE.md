# AGI-GI rev274 — supplied block-action provenance certificate

## Scope

Durable claim: `chatgpt-session-j-rev274-block-action-provenance-20260822T091200JST-bbffdce6`.

Exclusive scope: `crx1/homogeneous-block-reduction/group-block-action-equivariance-certificate`.

This revision closes one narrow provenance boundary that is disjoint from rev273. Rev273 owns relation homogeneity and quotient-relation transport for a supplied homogeneous block reduction. Rev274 instead verifies the permutation-group side of a supplied reduction: whether the supplied source and target partitions are genuine block systems for the supplied paired generators, what quotient permutations those generators induce, and whether the supplied block bijection intertwines the paired quotient actions.

## Exact contract

`certify_group_block_action_equivariance` is exact relative to the supplied paired generator lists. It:

1. validates that source and target partitions are disjoint uniform full-domain partitions of the same degree, block count, and block size;
2. validates the supplied block bijection and canonicalizes block ordering without choosing a new block system;
3. validates every supplied source/target generator as a complete permutation and requires the generator lists to be paired one-to-one;
4. proves each generator maps every supplied block onto one whole block, deriving its induced quotient permutation exactly;
5. verifies `B(q_source(i)) = q_target(B(i))` for every supplied generator pair and every source block;
6. freezes the exact canonical partitions, block map, original paired generators, and induced quotient generators into a deterministic SHA-256 transcript; and
7. independently replays the certificate from its frozen inputs before accepting it as replay-stable evidence.

Any malformed partition, overlap, nonuniform fibre, invalid permutation, block-breaking generator, generator-pair count mismatch, nonbijective block map, or quotient-equivariance mismatch fails closed and emits no exact certificate.

## Strict boundary

This revision does **not** discover a block system, canonically select one member of a block-system family, prove that unary/binary relations are constant on block fibres, construct quotient relations, solve the implicit relation image, infer a generator pairing, establish original-root quasipolynomial accounting, or wire a production parent. Those are independent obligations, including the concurrently owned rev273 relation-provenance scope.

The certificate therefore proves only the supplied group-action equivariance premise. It does not close CRX1, Graph Isomorphism, or AGI. State remains `NOT_AGI`.

## Parallel safety

The implementation is additive and limited to the six paths reserved by the rev274 claim. It does not modify `MAIN.md`, rev273, rev272, rev271, rev270, rev269, rev268, rev267, rev265, rev264, CRX3 proof-DAG work, rev252, rev247, or any sibling claim/branch/PR/workflow. No sibling run is cancelled or rerun; no sibling branch is rebased, force-pushed, overwritten, closed, or merged.

## Focused validation

Local focused validation on the exact implementation content:

- `python automation_runs/2026-08-19_0851_JST/test_homogeneous_block_action_provenance_rev274.py -v`: 12/12 success;
- `python -m py_compile automation_runs/2026-08-19_0851_JST/homogeneous_block_action_provenance_v1.py automation_runs/2026-08-19_0851_JST/test_homogeneous_block_action_provenance_rev274.py`: success.

Coverage includes exact nontrivial quotient action, canonical block-order replay, overlapping/nonuniform partitions, source/target block-breaking generators, invalid block bijection, paired quotient-action mismatch, generator pairing mismatch, invalid permutations, the trivial generated group, and digest tampering.
