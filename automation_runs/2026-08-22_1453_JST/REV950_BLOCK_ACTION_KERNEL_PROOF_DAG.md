# rev950 — block-action kernel factorization proof-DAG admission

## Scope

This revision is a file-disjoint CRX3 algorithmic consumer for the main-integrated rev275 homogeneous block-action kernel factorization. It does not modify rev274/rev275, shared recurrence accounting, shared proof-DAG code, corrected Split-or-Johnson work, `MAIN.md`, or any sibling claim/branch/PR/workflow.

## Contract

The consumer admits only a rev275 `BlockActionKernelFactorization` that replays exactly against its rev274 `BlockActionProvenance`. The proof identity freezes:

- rev274 provenance digest and rev275 factorization digest;
- original-domain degree, block count, generator count, and original root;
- rev275 work cap, mechanically estimated complete Schreier work, and source/target sift levels;
- source/target group orders, common quotient-image order, and both kernel orders;
- complete original-domain source/target kernel generator transcripts.

Before proof-DAG admission it rechecks both factorization identities `|G| = |ker| |im|`, validates the kernel transcripts as original-domain permutations, and requires the recorded work to remain inside the frozen rev275 cap.

## Accounting

The exact factorization is represented as a certified terminal recurrence leaf. Its local charge is a conservative logarithmic lift of rev275's mechanically preflighted Schreier work plus polynomial transcript overhead. An independent rev275 replay is charged externally as well; replay is not treated as free. The unchanged shared `proof_dag_accounting_v1` remains authoritative for final occurrence charging and quasipolynomial-envelope validation.

## Fail-closed boundary

Malformed digests, nonexact or incomplete factorization evidence, provenance mismatch, replay failure, invalid root/resource/order/kernel fields, accounting drift, nonfinite envelope inputs, or an exceeded proof-DAG envelope are rejected. This revision does not solve quotient String Isomorphism, construct a quotient transporter, lift a transporter through the kernel, close corrected Split-or-Johnson, prove GI, or establish AGI.

State remains `NOT_AGI`.
