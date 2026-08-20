# AGI-GI rev227: affected-segment parent-coset reassembly envelope

## Status

This revision candidate solves only CRX2 child 2.2.2.2c. It bounds and records
the full-domain parent-coset subgroup rebuilds performed after quotient children
return. Complete multi-layer single-T aggregation, all-T multiplicity, and the
AGI root remain unresolved. State remains `NOT_AGI`.

## Existing-world inclusion audit

The implementation includes the orbit-stabilizer/coset-union reconstruction used
in Luks-style recursion and the stabilizer-chain membership mechanisms available
in computational group systems such as GAP. It does not infer a cost from the
existence of those abstractions: J's actual generator inputs and containment
sifts are counted and checked against a preflight bound.

## Preflight envelope

From rev226's exact quotient-derived leaf and node upper bounds, the number of
internal nodes is at most `nodes - leaves`. At any internal node at most `t`
successful children contribute:

- every child-subgroup generator;
- one representative difference;
- one full-domain Schreier chain over their union;
- one representative containment sift and every child-generator containment
  sift after reconstruction.

Using the ambient group order as a conservative bound on every intermediate
generator family gives finite upper bounds on internal nodes, generator inputs,
containment sifts, and raw work. Cap failure returns unknown before quotient
homomorphism preparation or recursion begins.

## Execution-linked evidence

The exact executor records actual internal rebuilds, generator inputs, and
containment sifts in `AffectedSegmentReassemblyExecutionCharge`. Exact and exact-
empty results retain the charge and both rev226/rev227 envelopes. An assertion
rejects any execution whose actual counts exceed its preflight artifact.

Local tests cover fail-before-execution, cap-plus-one saturation, formula
multiplicity, exact `S_5` execution, nonzero actual charges, and actual-versus-
envelope verification. The next child must sum rev224--rev227 envelopes across
every growing-beard layer into one complete single-T execution artifact.
