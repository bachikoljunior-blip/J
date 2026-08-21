# Rev268 — implicit relation production-parent orchestration

## Scope

Rev268 is an additive, fail-closed orchestration boundary for the CRX1 bounded-arity relation-image path. It does not copy or import branch-only sibling implementations. Instead, the production parent accepts the exact descendants as dependency-injected callables and validates their public result contracts before allowing a parent outcome to be promoted.

This revision remains `NOT_AGI`. It does not close CRX1, GI, or AGI.

## Descendant contracts composed

The parent boundary composes these independently owned leaves:

- rev265: original-root resource envelope and immutable phase reservation split;
- rev263: structural exact-empty parent preflight;
- rev262: exact auxiliary image/value-coset intersection;
- rev267: exact original-domain preimage of the image result;
- rev261: nonempty semantic parent-coset verification;
- rev266: normalized exact parent outcome.

No sibling source file is imported or modified by rev268.

## Ordered routes

### Structurally certified exact-empty route

`rev265 -> rev263 -> rev266`

The image machinery is not invoked when rev263 has already proved one of its accepted structural parent obstructions. Domain-size and relation-signature mismatch evidence legitimately carries auxiliary degree zero; feature-inventory mismatch must bind the admitted auxiliary degree.

### Nonempty route

`rev265 -> rev263(inconclusive) -> rev262 -> rev267 -> rev261 -> rev266`

Every transition must be exact and complete and must retain the admitted domain/auxiliary degrees. The final normalized result must bind the caller-supplied source/target relation digests and cite rev261 evidence.

## Deliberate exact-empty image gap

A semantically important gap remains explicit rather than being papered over. When rev263 finds no structural obstruction but rev262 later proves the auxiliary image empty, rev267 can preserve that result as `exact_empty_original_domain_relation_preimage`. Current rev263/rev266 contracts, however, do not accept that image/preimage emptiness as semantic parent-empty evidence.

Rev268 therefore returns the non-promoted state:

`undetermined_exact_empty_image_parent_semantic_bridge`

It does **not** call rev266 and does **not** claim an exact parent-empty result in that case. The next independent leaf is a proof-producing bridge from exact image/original-domain preimage emptiness to an exact semantic parent-empty certificate that the normalization boundary can validate.

## Fail-closed invariants

- rev265 must be admitted, root-lift certified, order compatible, image-gate certified, and within its declared work cap;
- the six phase reservations must occur in the expected order and sum exactly to the admitted work bound;
- callback exceptions are contained as undetermined results;
- incomplete descendant results are never promoted;
- degree mismatches are never promoted;
- exact-empty results may not carry a right coset;
- normalized outcomes must bind the expected relation digests and the correct source evidence revision;
- no branch-only sibling module imports are allowed by the dedicated smoke workflow.

## Validation

`test_implicit_relation_production_parent_rev268.py` covers:

- ordered nonempty composition;
- structural exact-empty short-circuiting;
- zero auxiliary degree for structural domain mismatch;
- exact-empty image/preimage preservation without semantic overpromotion;
- malformed preflight rejection;
- resource-envelope and phase-reservation rejection;
- incomplete image rejection;
- relation-digest mismatch rejection;
- callback exception containment.

The dedicated GitHub Actions smoke job compiles the module/tests, runs the focused regressions, and checks the no-sibling-import boundary.
