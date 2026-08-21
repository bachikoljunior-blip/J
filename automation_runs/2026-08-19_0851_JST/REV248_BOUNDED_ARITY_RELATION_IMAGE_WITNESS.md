# AGI-GI rev248: exact bounded-arity relation-image witness

## Scope

This revision isolates the unresolved CRX1 sibling for finite relation images of arity at most two. It adds a standalone exact witness oracle for named unary and binary relational structures. The module does not modify the active rev245 Design integration, rev246 primitive-Johnson operator, or rev247 S1 imprimitive production-admission paths.

## Executable contract

`bounded_arity_relation_image_solver.py` accepts two finite structures with unique hashable domain elements and uniquely named relations. Every relation must have arity one or two, and every tuple must lie in the declared domain.

`find_bounded_arity_relation_image_isomorphism` returns either:

- a `BoundedArityRelationImageWitness` containing a checked source-to-target bijection, deterministic relative to the supplied domain orders; or
- `None`, after an exhaustive color-respecting search proves that no named-relation isomorphism exists.

The independent verifier transports every source relation through the candidate map and compares it exactly with the same named target relation.

## Search design and exactness boundary

The solver first applies joint color refinement using unary memberships, binary loops, directed degrees, and incoming/outgoing neighbor-color multisets. Refinement is only an isomorphism-invariant rejection and pruning mechanism. It is never used by itself to accept an instance.

Unresolved color cells are searched by deterministic backtracking. Each partial map checks all already exposed unary and binary incidences and compares the remaining neighbor-color counts. A complete candidate is accepted only after full relation transport verification. Consequently the result is exact for the represented finite structures, while highly symmetric instances may still require exponential search.

## Regression evidence

The focused regression covers:

- a relabelled unary-block and directed-binary instance with a concrete verified witness;
- a 6-cycle versus two disjoint triangles, which has the same elementary degree profile but is exactly rejected;
- deterministic witness selection on a symmetric 4-cycle;
- empty structures, signature mismatch, and malformed-input fail-closed behavior.

Run from this directory:

```bash
python -m unittest -v test_bounded_arity_relation_image_solver.py
python -m py_compile bounded_arity_relation_image_solver.py test_bounded_arity_relation_image_solver.py
```

## Remaining boundary

This revision supplies an exact executable witness/oracle for the arity-at-most-two relation-image leaf. It does not establish a polynomial or quasipolynomial runtime bound for the backtracking phase, does not prove the homogeneous-block reduction feeding the relation image, and therefore does not close CRX1 or full graph isomorphism. AGI remains `NOT_AGI`.
