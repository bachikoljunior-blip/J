# AGI-GI rev232: correlated t-WL original-root resource envelope

## Attempted leaf

CRX2 / correlated t-WL original-root charge.

## Observed gap

`stable_colored_subset_twl` counted tuple initialization and correlated
replacement work for an executed run.  The consumer did not reserve, before the
first source run, the complete source/target multiplicity over every ordered
individualization level, every `m^t` tuple state, and every possible
stabilization round.  Its engineering caps were therefore not an independent
original-root complexity certificate.

## rev232 closure

`correlated_twl_resource_envelope_v1.py` computes with arbitrary-precision
integers:

- `S = m^t` tuple states per run;
- `sum_{ell=0}^{t-1} P(m,ell)` possible runs on each side;
- at most `S` refinement rounds per run;
- `S*m*t` correlated replacement work per round;
- the complete source-plus-target upper bound.

It independently requires `m <= root_n` and
`t <= ceil(log2(root_n))`, then admits execution only if the complete bound fits
one finite original-root budget.  A rejection occurs before building the first
t-WL branch plan.  Runtime state/tuple/round/work caps remain separate
fail-closed engineering limits and are not inputs to the proof bound.

Successful or partial execution records source and target run counts and work
exactly once, while the preflight upper bound remains available for independent
replay.

## Claims not made

This solves the correlated t-WL resource subleaf only.  Design branch transport,
full-string SI multiplicity, their integration with the paired theorem relation,
global corrected Split-or-Johnson closure, and AGI criteria remain unresolved.

AGI state: `NOT_AGI`.
