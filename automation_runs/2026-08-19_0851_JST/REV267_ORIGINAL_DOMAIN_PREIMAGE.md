# Rev267 — exact original-domain paired preimage

## Scope

Rev267 occupies only `crx1/bounded-arity-relation-image/implicit-generator-group/original-domain-paired-preimage`.
It ports the previously green but concurrency-superseded PR #202 child onto the current rev257 contract while keeping the still-active rev262 implementation path untouched.

The new `implicit_relation_image_preimage_coset_v2.py` accepts rev262 through a narrow structural result contract rather than importing rev262's active file.  For a nonempty exact auxiliary image right coset it uses rev257's stored paired Schreier transversals to lift the representative and every image-stabilizer generator, adjoins the exact homomorphism kernel, independently checks the lifted auxiliary images, verifies original-domain containment, and certifies

`|preimage(K)| = |ker(phi)| * |K|`.

No original-domain group enumeration is used.

## Exact-empty and fail-closed behavior

An exact-empty auxiliary transporter is promoted only when the image result is exact, complete, and carries no coset.  If rev257 itself is exact-empty, rev267 requires compatible empty image evidence instead of silently accepting contradictory downstream evidence.  Incomplete image results, wrong contract status, auxiliary-degree mismatch, representatives outside the exact image group, and image-subgroup generators outside that group are rejected or left undetermined.

## Existing-solution audit

PR #202 contained the first implementation of this child and its focused smoke was reported green, but both rev259 ownership records were later marked `superseded`; no production implementation from that claim was integrated.  Rev267 therefore reuses the mathematical paired-lift idea under a new unoccupied target revision, tightens contradictory-evidence handling, and removes the direct import of the old rev258 value-coset module.

## Strict boundary

Rev267 does not compute the rev262 value-preserving image intersection, does not modify rev261 or rev263 parent verification, does not discharge rev265 original-root resource accounting, does not normalize rev266 parent outcomes, and does not wire a production parent.  CRX1, graph isomorphism, and AGI remain unresolved.  State remains `NOT_AGI`.

## Current-main takeover checkpoint

The original owner became stale with PR #212 still unmerged. A fresh takeover
claim therefore replays the implementation on the current canonical main,
regenerates phase evidence from the current claim registry, and requires both
the focused tests and the complete exact-head workflow set before integration.
The mathematical scope and strict boundary above are unchanged.
