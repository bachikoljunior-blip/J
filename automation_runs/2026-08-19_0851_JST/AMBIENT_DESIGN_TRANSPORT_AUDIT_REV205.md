# rev205 ambient Design witness transport audit

## Active parent and count

The current main parent is AGI-GI rev204 (`6faeca0956346f61c323a5f63dc5f4738c662102`). The predicted and effective problem counts remain 512, so this work replaces the active W1R-H6-R3c2 internal leaf in place rather than creating a new global branch.

rev204 mechanically re-derives the controlled-arity right-ground relation from the original bipartite inputs and obtains a complete first-successful exact k-WL / Design witness cover. Its explicit remaining boundary is that these witnesses are canonical under arbitrary right-ground relabeling but have not yet been intersected with the actual allowed parent/right permutation group.

## Existing-world mechanism checked

The relevant classical mechanism is not a new combinatorial theorem: it is the permutation-group transporter / color-automorphism layer used in Luks-style String Isomorphism. Given generators for an allowed permutation group, one restricts the isomorphism search to a coset carrying a source structural marker to its target marker, with a stabilizer subgroup as the recursive group. Schreier-Sims orbit/stabilizer machinery is the standard implementation substrate.

This is also consistent with Babai's quasipolynomial GI/SI framework: Design-Lemma / Split-or-Johnson structures are symmetry-breaking objects inside a group-action recurrence, not licenses to leave the ambient group. The repository already contains exact Schreier chains, pointwise stabilizers, RightCoset, and canonical partition transporter primitives, so rev205 reuses those rather than introducing a second group engine.

References checked during this run:
- E. M. Luks, *Isomorphism of graphs of bounded valence can be tested in polynomial time*, JCSS 25(1), 1982, DOI 10.1016/0022-0000(82)90009-5. The color-automorphism problem is explicitly formulated relative to a supplied permutation group.
- L. Babai, *Graph Isomorphism in Quasipolynomial Time*, arXiv:1512.03547. The SI/coset framework and canonical combinatorial partitioning are combined inside the ambient group recurrence.

## rev205 exact boundary

`ambient_design_tuple_transport_v1.py` handles the first ambient-action child.

For every ordered individualized tuple pair in rev204's complete Cartesian witness cover, `ordered_tuple_transporter` computes exactly

`{ g in G : g(source_tuple[i]) = target_tuple[i] for every i }`.

It constructs a representative coordinate by coordinate from Schreier orbit transversals and returns the pointwise stabilizer of the target tuple as the subgroup. Unreachable pairs are deleted. Because rev204 exhausts the entire first successful witness level, every true isomorphism in the supplied ambient group must lie in one surviving tuple coset. If none survives, the ambient instance is exact empty.

The unary relation case has no individualized-tuple layer. There rev205 sends the ordered unary color partition directly through the existing exact `canonical_partition_transporter` over singleton right-ground blocks.

## Deliberate non-claim / next child

The returned cosets are exact ambient child domains, but rev205 does **not** yet claim that the original full string has been intersected with each coset, nor that the alpha-split / imprimitive / UPCC structural output has been recursively closed. The next unresolved child is therefore:

**W1R-H6-R3c2b: for every rev205 ambient Design witness coset, run exact full-string SI/coset intersection and connect the resulting nonempty children to the existing split/block/UPCC recurrence machinery with proof-carrying shrink and quasipolynomial accounting.**

AGI remains `NOT_AGI`. No full Split-or-Johnson, global quasipolynomial recurrence, generality/performance/autonomy proof, or practical AGI delivery is claimed.
