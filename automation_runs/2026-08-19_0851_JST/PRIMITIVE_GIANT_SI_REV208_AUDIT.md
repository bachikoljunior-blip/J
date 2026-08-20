# AGI-GI rev208 audit — literal primitive giant String Isomorphism

## Scope and problem-tree accounting

The active root remains the strict practical AGI root and the AGI state remains `NOT_AGI`.
The AGI-GI problem-tree forecast remains **512** and the effective non-replaced count remains **512**. This rev does not pre-cap a newly created branch to avoid the mandatory over-count rewrite; instead it replaces an internal part of existing leaf **W1R-H6-C2** in place. The actual count therefore does not exceed the forecast in this change.

This rev closes the `literal primitive giant A/S` subcase of H6-C2 at both direct candidate and invariant-orbit S1 dispatch boundaries. It does **not** claim the primitive non-giant, larger Johnson-ground, genuinely unresolved Split-or-Johnson image, or global W1R-H6 recurrence cases.

## World-solution / higher-layer audit

At the parent layer, Babai's quasipolynomial Graph/String Isomorphism framework identifies large alternating/symmetric images as the barrier handled by local certificates and affected/unaffected structure (Babai, *Graph Isomorphism in Quasipolynomial Time*, arXiv:1512.03547; see also the 2017 correction/update and later expositions).

At this particular child, however, the action classified by `classify_s1_structure` is on singleton blocks. Therefore an exact image of order `n!` or `n!/2` with trivial singleton-action kernel is literally `S_n` or `A_n` on the string coordinates; no quotient kernel remains. In that narrower case there is a simpler existing mathematical solution than invoking the full local-certificates machinery:

- under `S_n`, two strings are isomorphic iff their color multiplicities match, and the full solution set is the target color-class stabilizer times one classwise transporter;
- under `A_n`, intersect the same transporter coset with even parity. If any target color class has size at least two, an in-class transposition toggles transporter parity; the automorphism subgroup is the even kernel of the color stabilizer. If every class is a singleton, the unique transporter is either even (one exact solution) or odd (exact empty).

This is a higher-layer compression for the **literal full-action giant** child only: it eliminates unnecessary local-certificate/Design recursion for that child, but does not remove the giant-quotient-with-kernel branch elsewhere in the tree.

## Executable change

`primitive_giant_full_action_string_iso_v1.py` implements the exact terminal above. It reuses the existing exact giant certificate and paired-Schreier kernel substrate, audits the color-stabilizer order, verifies every returned subgroup generator lies in the ambient group and stabilizes the target string, and returns proof-carrying terminal accounting without enumerating `A_n` or `S_n`.

`u2_candidate_coset_string_iso_v3.py` places this terminal ahead of the existing v2 structural dispatcher when the candidate subgroup itself is a literal full-action giant. In addition, the established `s1_string_isomorphism_v2` now uses the same exact terminal after its small-order gate and before structural fallback. This second hook is the important rev206/rev207 integration point: existing `candidate_coset_string_isomorphism_u2` already decomposes intransitive candidate actions into invariant-orbit S1 children, so a literal `A_m`/`S_m` orbit child now closes exactly without changing or relaxing the coupled parent action. The rev207 proof replay calls the same candidate/S1 stack and therefore sees the same proof-carrying terminal.

The regression covers literal `S_9`, literal `A_9`, the singleton-color odd-parity exact-empty case, direct v3 candidate dispatch, direct S1 dispatch beyond the explicit-degree/enumeration caps, and the **existing v2 candidate** intransitive-orbit path with an `S_5` child. The latter verifies that callers need not migrate to a new parent API to gain the literal-giant closure.

## Remaining child after this attempt

The next unresolved part of **W1R-H6-C2** is now the non-literal remainder: primitive non-giant / larger Johnson-ground states and genuinely unresolved Split-or-Johnson image states. Exact giant quotients with nontrivial kernels still require the existing theorem-gated local-certificate/affected-unaffected machinery; they are not conflated with the literal full-action terminal.

No result in this rev is evidence of AGI, full Split-or-Johnson closure, or global quasipolynomial recurrence closure.
