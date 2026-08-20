# AGI-GI rev209 problem-tree audit

## Starting leaf and problem-count trigger

The canonical parent after rev208 is **H6-C2**. rev208 removed the literal natural-domain `A_n/S_n` candidate subleaf, but primitive non-giant / larger-Johnson candidates and genuinely unresolved Split-or-Johnson image states remain fail-closed.

The predicted total remains **512** and the effective non-replaced count remains **512**. The actual count has not exceeded the prediction, so the mandatory over-count full-tree rewrite trigger does not fire. rev209 therefore replaces internal H6-C2 subleaves in place rather than adding parallel active branches.

## World-solution inclusion audit

At the parent level, Babai's quasipolynomial String Isomorphism framework does not solve the large primitive barrier with an unrelated generic search. It repeatedly moves between exact permutation-group/coset operations, Johnson-type actions, local certificates, Design-Lemma/Split-or-Johnson structure, and strictly smaller auxiliary actions. Luks-style orbit/block decomposition and exact coset lifting remain the algebraic substrate.

The J tree already contains those ingredients in separate revisions:

- rev179: paired action image/kernel and exact coset preimage;
- rev180/rev181: complement-safe lower-arity Johnson relation images and full-candidate restriction;
- rev182: adaptive strongest informative relation selection;
- rev183: simultaneous lower-arity relation images under one strict shrink budget;
- rev177: exact signed-ground profile-determined terminal;
- rev184+: logarithmic certificate / Design machinery for the genuinely homogeneous remainder.

Therefore the correct cross-layer move is to route H6-C2 through these existing exact substrates before inventing another Johnson solver or another generic recursive branch.

## Direct attempt and replacement

`u2_candidate_coset_string_iso_v3.py` now treats a transitive `primitive_non_giant` candidate as follows after rev208's literal-giant check:

1. remove the fixed candidate representative exactly and work in the subgroup coordinate system;
2. try rev183's joint complement-safe lower-arity relation-image SI;
3. if the Johnson lift is certified but the joint selection does not close, try rev182's adaptive single-relation path;
4. when no useful lower arity remains, try rev177's exact profile-determined signed-ground terminal;
5. translate only exact subgroup results back to the original right candidate coset;
6. otherwise delegate unchanged to v2 and retain its typed fail-closed result.

A failed exact Johnson-ground lift is used as a routing certificate: subsequent Johnson-only reducers are skipped rather than repeating the same bounded recognizer. Nonexact profile splits, relation filters, theorem evidence, and resource-limited searches are never promoted to exact parent answers.

The focused regressions use ground size above the old explicit cap and exercise three distinct existing-solution routes: J(10,4) joint pair+triple image, J(9,4) adaptive single relation when the two-relation degree budget does not fit, and J(9,2) profile closure when no lower configured arity exists. The fixtures keep a nontrivial S_{v-1} exact stabilizer rather than forcing an expensive all-distinct string merely for testing.

## Resulting boundary

If validation succeeds, these relation-informative/profile-determined larger-Johnson subleaves are removed from H6-C2. The remaining substantive boundary is narrower:

**H6-C3:** close relation-homogeneous / non-profile-determined primitive states and genuinely unresolved corrected Split-or-Johnson image states with proof-carrying recursive Design/Johnson continuation, while preserving rev207's polynomial-lift accounting invariant. Primitive non-giant states that are not certified Johnson also remain here until an exact Split-or-Johnson structural certificate routes them.

Missing theorem hypotheses, nonexact structural evidence, node/resource overflow, or an unverified recurrence charge remain fail-closed. Full W1R-H6, global quasipolynomial closure, and AGI are not claimed. AGI remains **NOT_AGI**.
