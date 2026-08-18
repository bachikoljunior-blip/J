# rev78 direct attempt — continuous-attribute approximation/stability and shift validation

Root remains **NOT_AGI**.

A direct attempt derived and implemented a distribution-free perturbation certificate for the fixed-skeleton WL/RFF graph feature map. For H refinement iterations and node-mass normalization, the explicit feature map obeys

`||F(A,X)-F(A,Y)||_2 <= sqrt(H+1) * L_phi * ||X-Y||_F`,

where `L_phi = sqrt(2/m) ||W||_2` is a global Lipschitz bound for the m-component random-Fourier attribute map. The implementation computes both the realized feature displacement and the deterministic upper bound.

For the atomic RBF random-Fourier approximation, a pointwise Hoeffding radius `sqrt(8 log(2/delta)/m)` is also implemented. Independent shifted/heavy-tailed synthetic cases were used only as sanity checks; they were not used to fit the bound.

Local cumulative regression rev75–78: **20 passed**.

The broad leaf is still unresolved because these results do not cover population-level bandwidth/model selection under shift, simultaneous graph-population confidence, or structural edits. It is decomposed into:

- `...c2d1`: deterministic fixed-skeleton continuous-attribute perturbation bound — unresolved pending dedicated leaf validation;
- `...c2d2`: atomic RFF approximation confidence and finite-family extension — unresolved;
- `...c2d3`: stability under bounded structural edits, not only attribute perturbations — unresolved;
- `...c2d4`: leakage-resistant population/domain-shift calibration and independent external validation — unresolved.

Estimated active-node count after decomposition: **447**, below prediction 512.
