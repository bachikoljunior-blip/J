# AGI-GI rev225: giant-action structural resource envelope

## Status

This revision candidate solves only CRX2 child 2.2.2.2a: fail-before-execution
resource accounting for every raw Schreier/orbit primitive in a giant block-action
structural audit. It does not solve affected-segment quotient/kernel child SI,
the complete single-T sum, all-T multiplicity, or the AGI root. State remains
`NOT_AGI`.

## Exact execution boundary

`giant_action_resource_envelope_v1.py` conservatively bounds, before execution:

- the quotient image chain;
- paired kernel recursion and the exact kernel chain;
- domain and kernel orbit exploration;
- every orbit-representative point stabilizer and its quotient image;
- the theorem-side pointwise unaffected stabilizer and quotient image.

The bound saturates at `cap + 1`. The local-certificate executor charges every
actual before/after audit against one remaining single-T budget and returns
unknown before the next audit if the budget is insufficient.

The giant-action certificate now retains the already materialized theorem-side
unaffected stabilizer and its exact image order. The stable-beard reduction reuses
that proof artifact instead of recomputing the full giant audit, pointwise
stabilizer, and quotient image.

## Evidence and limits

The new regression gate checks fail-before-audit behavior, cumulative admitted
audits, exact bounded output, saturation, and absence of the former stable-layer
recomputation. The theorem relation threads a finite cap only in theorem mode;
bounded regression mode remains explicitly non-theorem-scale.

Still unresolved: primitive accounting inside quotient branching, singleton
preimage/kernel-child SI, exact coset reassembly, and their composition with the
rev224 preimage envelope into a complete single-T execution sum.
