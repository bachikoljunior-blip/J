# rev139 — existing-solution containment audit

Series: **AGI-GI rev系列**

This audit applies the required question "does an existing world solution already contain a solution to this child?" to the current unresolved canonical-labeling/GI branch and retrospectively to the major active algorithmic children represented in the rev series.

## Findings

1. **General GI / String Isomorphism / Coset Intersection** — Babai's quasipolynomial GI framework already supplies an existence proof and a high-level decomposition: Luks-style string isomorphism plus group-theoretic local certificates, canonical partitioning, Design Lemma, and Split-or-Johnson. This contains the conceptual solution target for the remaining general nonregular primitive/coherent obstruction, but not a drop-in verified implementation for J.
2. **Practical canonical labeling / automorphism groups** — nauty/Traces and bliss already compute canonical labelings and automorphism generators for broad graph classes. They are therefore suitable as independent differential oracles and practical fallback/reference implementations. They do not by themselves prove that J's internal master reduction realizes Babai's quasipolynomial worst-case recurrence.
3. **Johnson obstruction** — the rev-series exact Johnson recognizer/reduction aligns directly with Babai's statement that Johnson configurations are the obstruction to effective canonical partitioning; keep it as a certified internal terminal/reduction rather than re-solving the same recognition problem from scratch.
4. **Permutation-group primitives** — J's Schreier chain, stabilizer, transporter, and coset work overlaps standard computational permutation-group machinery. Existing systems/literature can be used as differential oracles, while J retains its fail-closed independently checked implementation.
5. **Regular-prime primitive terminal** — no external result found in this audit justifies replacing rev136–rev138's exact affine minimization with an unverified shortcut. Keep the internal certificate path and validate it end-to-end.

## Consequence for the problem tree

Do not expand the remaining general primitive/coherent child into ad-hoc graph-family terminals indefinitely. Replace that expansion strategy with three integration children:

- B1: executable independent canonical-label differential oracle (nauty/Traces or bliss) for J's exact outputs;
- B2: explicit Babai-style local-certificate + canonical-partition recurrence contract for the nonregular primitive/coherent branch;
- B3: end-to-end recurrence/complexity and relabeling-invariance validation, fail-closed when the contract cannot be certified.

This is a containment/integration result, not an AGI result. AGI remains NOT_AGI.