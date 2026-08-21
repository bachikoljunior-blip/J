# AGI-GI rev261: implicit relation-image parent promotion gate

This revision occupies a distinct continuation leaf after rev257 merged and the
durable registry showed fresh rev258 resource-envelope/image-coset work, rev259
original-domain paired-preimage work, and an exclusive rev260 differential-audit
claim. An earlier draft under rev260 was stopped and closed without merge as soon
as that main-visible target-revision collision appeared; rev261 was then claimed
directly on main before further implementation writes. This revision therefore
does not duplicate rev258, rev259, or rev260 scope. Instead it adds the final
**nonempty parent promotion verifier** that an eventual caller can apply to an
already-certified `PairedActionCosetPreimage` before exposing that right coset as
an exact original-domain transporter for a complete named unary/binary relation
image.

The gate consumes a concrete paired-preimage artifact rather than free-standing
status/order integers. It independently verifies all of the following before
promotion:

- the upstream status is exactly `exact_paired_action_coset_preimage` and carries
  a subgroup, representative, and `RightCoset`;
- domain, kernel, preimage subgroup, and representative degrees agree, while the
  image degree equals the faithful neutral-point plus unary/binary auxiliary
  degree determined from the relation signature;
- the artifact's stored subgroup and representative agree with its returned
  `RightCoset`;
- `|G| = |ker| |im|`, the image target-subgroup order divides the image order,
  `|preimage subgroup| = |ker| |image target subgroup|`, and the stored subgroup
  order agrees with the actual Schreier chain;
- the representative and every returned subgroup generator sift into the
  certified original-domain group;
- the representative transports every tuple of every named relation from source
  to target; and
- every returned subgroup generator stabilizes the complete target relation
  image, which suffices for the whole generated target subgroup.

Membership-sift and relation-action checks are conservatively counted and capped
before either class of semantic verification starts. Cap excess is
`undetermined`, never an exact answer. Corrupted or inconsistent evidence fails
closed.

The focused regression constructs an actual generic `paired_action_coset_preimage`
artifact from the integrated faithful unary/binary induced-action substrate,
then verifies positive promotion and fail-closed corruption cases (wrong status,
order evidence, representative, subgroup, signature, auxiliary degree, and
resource caps).

## Strict boundary

This revision does **not** compute the implicit image/value-coset intersection,
does **not** construct the paired preimage, and does **not** discharge the
original-root quasipolynomial resource envelope. Exact-empty image intersections
remain an upstream case and are intentionally outside this nonempty promotion
gate. It also does not wire the still-active rev258/rev259/rev260 branches into a
production parent. CRX1, graph isomorphism, and AGI remain unresolved;
`AGI = NOT_AGI`.
