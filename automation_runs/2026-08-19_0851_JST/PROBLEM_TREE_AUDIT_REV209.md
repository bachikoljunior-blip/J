# AGI-GI rev209 problem-tree audit

The parent leaf after rev208 is **H6-C2b**, the primitive-non-giant / higher-arity Johnson and genuinely unresolved Split-or-Johnson image path. Prediction remains **512** and effective non-replaced count remains **512**; the mandatory over-count rewrite trigger does not fire.

A direct attempt splits C2b into two existing-solution layers:

- **H6-C2b1:** the current primitive action is a certified Johnson action on a larger ground, but its represented signed-ground group is still polynomial/cap-small;
- **H6-C2b2:** the signed-ground group is too large and requires structural/logarithmic Design recursion.

This split exposes a missed cross-layer reuse. rev176 already implemented exact faithful signed-ground SI, and rev184 already implemented exact outcomes of logarithmic relation/Design descent, but U2's primitive-non-giant candidate boundary still stopped at rev173's small-ground cap. `u2_candidate_coset_string_iso_v4.py` now reuses those later substrates after all U3 paths fail: it shifts the source into subgroup coordinates for H*r, tries the exact rev176 signed-ground terminal, then tries rev184's logarithmic relation/Design exact outcomes, and translates only exact results back with the existing right-coset primitive. Nonexact structural evidence is never promoted to an exact parent claim.

The focused regression uses the certified J(9,2) action of PGL(2,8), degree 36 and group order 504. With the ordinary candidate enumeration cap forced to 128, U3 stops at `undetermined_johnson_ground_cap`; rev209 closes the same candidate through the faithful 9-point signed ground under a 1024 cap. A nontrivial right-coset representative and an equal-multiplicity exact-empty case are also checked.

If validation succeeds, **H6-C2b1** is solved in place. The next leaf is **H6-C2b2:** integrate proof-carrying recursive continuation for the large signed-ground states where rev184 returns a certified partition filter / second Johnson structural descent / homogeneous Design gate rather than an exact answer. Keep resource caps and missing theorem hypotheses fail-closed. AGI remains **NOT_AGI**.
