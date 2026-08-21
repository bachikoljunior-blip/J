# AGI-GI rev260: generic paired-action preimage differential verifier

## Scope

This revision adds a bounded, independent differential oracle for the generic
generator-paired action/preimage substrate already present on `main`. It does
not implement another production image intersection or original-domain
preimage solver, and it does not modify rev258, rev259, or rev261 work.

The oracle consumes:

- a Schreier-certified domain group;
- one image generator for each stored domain generator;
- either a complete target image `RightCoset` or an exact-empty marker;
- an independent `image_of(g)` evaluator; and
- an independent semantic predicate `direct_accepts(g, image_of(g))`.

No unmerged rev258 implementation is imported. The relation-image consumers can
supply their own direct feature-transport predicate when they integrate later.

## Complete bounded replay

Only after `|G| <= max_group_order` does the oracle enumerate the full domain
group by a deterministic generator/inverse BFS. It then verifies:

1. the evaluator maps identity to identity;
2. stored domain generators map to the supplied image generators;
3. every Cayley generator edge satisfies the homomorphism law;
4. the complete image fibers have the certified
   `|G| = |kernel| * |image|` cardinality;
5. direct semantics and target image-coset membership agree
   element-for-element;
6. the generic paired Schreier preimage is exact; and
7. direct semantics, image membership, preimage membership, and all subgroup
   cardinalities agree.

The verifier also supports nonfaithful actions. A trivial image of `S3`, for
example, must replay one image element with a six-element kernel and a
six-element original-domain preimage.

When the certified domain order exceeds the cap, neither callback is evaluated
and no enumeration or preimage reconstruction begins. Incomplete image results
remain unresolved. An exact-empty image result is accepted only after every
bounded domain element independently fails the direct predicate.

## Fail-closed statuses

Typed outcomes distinguish:

- incomplete or contradictory image results;
- order-cap rejection before callbacks;
- image evaluator escaping the generated image;
- identity, generator-pairing, or homomorphism mismatch;
- kernel/image fiber-cardinality mismatch;
- direct semantics versus image-coset mismatch;
- paired-preimage reconstruction failure; and
- paired-preimage set or order mismatch.

A forged image coset with the same cardinality as the direct solution is still
rejected because the complete membership bit-vectors differ.

## Verification

The focused suite covers:

- a unique nonidentity `S3` transporter;
- the full `S3` right coset;
- a nonfaithful trivial action with kernel order six;
- exact-empty replay;
- pre-enumeration order-cap rejection with callbacks asserted unused;
- an equal-cardinality forged coset;
- a bad generator pairing;
- incomplete/contradictory image-result handling; and
- strict callback and limit validation.

The path-scoped workflow also runs the inherited
`test_paired_action_coset_preimage_rev179.py` suite and emits a replayable
`attempt_solution` phase-admission payload for the exact PR head.

## Parallel boundary

The implementation, regression, audit, dedicated smoke, and phase-evidence
paths are owned by
`chatgpt-session-j-rev260-preimage-differential-20260822T065800JST-6c697d7f`.
The branch is based directly on `main`, so parent PR #200 files are not part of
this change. It does not edit any production preimage implementation, another
claim, `MAIN.md`, or a shared workflow.

## Remaining boundary

This is bounded independent validation evidence. It does not certify the
unbounded/original-root resource envelope and does not close the implicit
relation-image parent, CRX1, GI, or AGI. State remains `NOT_AGI`.
