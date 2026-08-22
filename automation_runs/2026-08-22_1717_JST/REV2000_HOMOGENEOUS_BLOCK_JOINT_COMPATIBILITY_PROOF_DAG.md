# AGI-GI rev2000 — homogeneous block joint compatibility proof-DAG

## Scope

This revision is a conservative structural consumer. It independently replays the main-integrated rev273 homogeneous unary/binary relation provenance, rev274 block-action equivariance, and rev275 block-action kernel factorization, then requires all three artifacts to describe one identical canonical source/target block reduction and block map.

It does **not** compute quotient String-Isomorphism, does not lift a quotient transporter to the original domain, does not import the sibling rev276 joint-compatibility implementation, and does not claim semantic SI exactness or AGI.

## Contract

The consumer accepts only when all of the following replay from their public main-integrated inputs:

- rev273 relation provenance re-certifies exactly from the explicit source/target relation structures, partitions, and block map;
- rev274 action provenance replays exactly, including paired generator-by-generator quotient intertwining;
- rev275 kernel factorization replays exactly against that same rev274 provenance;
- rev273 source/target partitions are literally the canonical rev274 block families and its block map is literally the rev274 block bijection;
- quotient block counts and uniform block sizes agree;
- rev275 is bound to the rev274 provenance digest, has the same domain/block/generator dimensions, and independently satisfies both `|G| = |ker| |image|` identities.

The immutable proof identity binds a fresh SHA-256 transcript of the rev273 relation structures/certificate to the canonical rev274 and rev275 digests plus the common partition/map and factorization orders. Any drift fails closed.

## Accounting boundary

The terminal proof carries no coset and sets `exact=False`. Its conservative local charge includes explicit rev273 relation replay work, rev274 compatibility checks, and the already-certified rev275 Schreier work bound. The shared `validate_execution_proof_dag` verifier is then applied under the original-root quasipolynomial envelope; storage identity reuse never erases execution charge.

## Parallel safety

Only the rev2000 reserved paths are modified. `MAIN.md`, shared proof-DAG/recurrence/coordination code, rev1800 quotient-SI work, rev278 original-domain preimage work, rev276's branch-only joint certificate, and every sibling claim/branch/PR/workflow remain untouched.

## Admission and validation progress

The branch-push smoke on implementation head `e4edebf754ddf9179c999829a9c0c81f4c9b76d3` completed successfully as run `32562618988`. Because the canonical attempt-solution evidence is persisted only after the functional regressions, compilation, and dependency-boundary gate succeed, the subsequent bot commit `ccd50fae49305ea544a05a23570d28cbcb8ff8e5` is execution-linked evidence that those preceding gates were green.

The persisted `attempt_solution` record reports `admitted=true`, `conflicts=[]`, target revision `2000`, and this exact dedicated scope. The repository-wide admission run on the pre-evidence implementation head (`32562619060`) failed closed as expected because the evidence file was not yet part of that head; no run was cancelled or manually rerun. GitHub does not recursively execute normal PR workflows for the evidence commit authored with the workflow token, so this connector-authored reserved-document heartbeat follows the bot evidence commit to let ordinary PR checks evaluate an evidence-bearing head naturally.

Publication and merge admission remain unclaimed. The PR stays draft until the evidence-bearing exact-head checks settle.
