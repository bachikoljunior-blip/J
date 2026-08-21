# Rev271 — implicit image value-coset proof-DAG consumer

Scope: `crx3/algorithmic-consumers/implicit-image-value-coset-exact-terminal-proof-dag`.

Rev271 consumes only the now-main-integrated rev262 value-coset phase and the stable rev220 execution proof-DAG. It does not import any active sibling branch module and does not modify rev262, rev269, rev270, primitive-Johnson, state-orbit, small-order, or shared proof-DAG implementation paths.

The consumer freezes the exact rev257 image group, complete auxiliary feature strings, original root, auxiliary polynomial lift, solver version, and `max_partition_states` before running rev262. Opaque feature identities are rejected before execution. Only rev262's complete exact nonempty, feature-inventory-empty, and image-transporter-empty statuses receive an immutable proof identity.

The local accounting node charges only the rev262 ordered-partition phase. Its conservative bound is the observed partition-state count times the supplied image-generator count and a deliberately loose auxiliary-domain polynomial factor. Construction of the supplied rev257 action is outside this leaf; callers may include an independently certified prefix through the shared proof-DAG external-cost parameter.

Because the common proof-DAG currently admits an auxiliary execution root only through the explicit `n+n^2` polynomial-lift rule, rev271 fails closed when the complete named unary/binary auxiliary degree exceeds that bound. This intentionally leaves multi-relation larger lifts unresolved rather than weakening rev220's invariant.

Focused regressions cover a certified nonempty S3 image coset, certified exact-empty trivial-image obstruction, partition-cap failure, identity tampering, opaque feature rejection before execution, `n+n^2` lift rejection, and root-envelope rejection.

Strict boundary: this is one CRX3 execution/accounting consumer. It does not construct the rev257 action, lift rev262 results to the original domain, promote parent semantics, discharge rev265/rev270 whole-path resource accounting, close CRX1/GI, or claim AGI. State remains `NOT_AGI`.
