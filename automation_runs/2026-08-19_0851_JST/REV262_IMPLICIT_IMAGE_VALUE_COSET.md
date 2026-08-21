# AGI-GI rev262: implicit image/value right-coset intersection

## Existing-solution audit

The unresolved rev257 child asks for the complete value-preserving right coset
inside the implicitly generated faithful auxiliary image group.  PR #200 already
contained a focused implementation, but its old rev258 claim was superseded and
the stacked PR was never integrated.  This revision ports that mathematical
construction to current main under a fresh, non-colliding rev262 claim and adds
an exhaustive bounded differential check against all elements of the S3 image.

## Solved child

Equal auxiliary feature values define an ordered partition.  The implementation
reuses the repository's exact canonical partition transporter over the implicit
Schreier chain, without enumerating the image group.  A successful transporter
is combined with the conjugated target-feature stabilizer to reconstruct the
complete result in the repository `RightCoset` convention.

Feature-inventory mismatch and absence of a transporter are exact-empty.
Partition-state resource exhaustion is nonexact and fails closed.

## Strict boundary

This solves only rev257 child (2).  It does not lift the image coset through the
paired action to the original domain and does not integrate the aggregate
original-root resource envelope.  CRX1, GI, and AGI remain unresolved; state is
`NOT_AGI`.
