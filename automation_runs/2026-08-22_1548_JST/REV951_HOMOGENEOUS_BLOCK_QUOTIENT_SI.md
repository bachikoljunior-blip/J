# AGI-GI rev951 — bounded homogeneous block quotient relation SI

## Scope

This revision closes only `crx1/homogeneous-block-reduction/bounded-quotient-relation-si-terminal`.

The main-integrated rev274 certificate supplies a fully replayed source/target block action and fixed block-coordinate bijection. The main-integrated rev275 factorization independently supplies the exact common quotient-image order and complete kernel/image factorization. Rev951 uses those two facts as a bounded algorithmic terminal: when the quotient-image order fits an explicit finite cap, it enumerates the complete quotient image group, reconstructs the homogeneous unary/binary quotient relations directly from the original relation structures, and computes the complete relation transporter set inside the exact action coset.

A nonempty answer is represented in the repository `RightCoset` convention by one actual source-to-target block representative and the complete target quotient-relation stabilizer. An empty answer is promoted to exact empty only after every element of the bounded exact quotient image has been checked.

## Fail-closed boundary

Rev951 rejects malformed or nonreplaying rev274/rev275 evidence, relation/domain mismatch, nonhomogeneous unary/binary fibres, relation-signature mismatch, quotient-image order above the declared enumeration cap, relation-transport work above the declared check cap, enumerated image-order drift, and any failure to reconstruct the full solution set as the expected target-stabilizer right coset.

The relation quotient is reconstructed independently from the source/target `RelationStructure` values and the certified block partitions; no caller-supplied relation block map is trusted. The fixed rev274 block bijection participates only as the coordinate bridge from the source quotient image group to the target quotient action.

## Parallel safety

The implementation is additive and restricted to the six paths reserved by durable claim `chatgpt-session-j-rev951-homogeneous-block-quotient-si-20260822T154800JST-d442901b`. It does not import or modify branch-only rev276/rev278 work, rev279 or other CRX3 proof-DAG consumers, corrected Split-or-Johnson rev400+ work, `MAIN.md`, shared proof-DAG/recurrence/coordination implementation, or any sibling claim/branch/PR/workflow.

## Strict remaining boundary

Rev951 does not lift the quotient transporter to the original domain, combine the quotient answer with rev275 kernels, certify whole-parent String Isomorphism, solve nonhomogeneous block fibres, remove the explicit bounded quotient-image enumeration gate, close CRX1/GI, or establish AGI. `agi_state` remains `NOT_AGI`.
