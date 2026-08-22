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
