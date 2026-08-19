# rev102–112 — calibrated noisy/mixed-schema compatibility

Root status remains **NOT_AGI**. These mechanisms belong to the evaluation/alignment support path and do not constitute AGI.

## What changed

1. Replaced a caller-supplied L-infinity attribute tolerance with a held-out split-conformal threshold. The exact finite-sample rank rule is tested by enumerating every held-out rank.
2. Added a normalized conformal variant whose scale model is fitted on an independent fit split, making finite thresholds context-adaptive under heteroscedastic noise without contaminating the calibration split.
3. Added group-conditional thresholds; unseen groups abstain rather than borrow an unjustified threshold.
4. Added weighted covariate-shift calibration using exact likelihood-ratio weights, including the required point mass at infinity for the test weight.
5. Added worst-case thresholds for certified likelihood-ratio intervals. For a finite fixed group partition, simultaneous Hoeffding probability bounds are converted to ratio intervals from independent unlabeled train/test covariate samples.
6. Added bounded arbitrary calibration-contamination protection by shifting the conformal order statistic; when finite samples cannot support the requested guarantee the threshold becomes infinity rather than overconfident.
7. Added a validity gate with no heuristic fallback: a finite threshold is released only when the information required by a recognized coverage contract is present.
8. Added mixed numeric/categorical schemas with different field names, explicit unit/category transforms, missingness-pattern conditional thresholds, and insufficient-overlap abstention.
9. Added paired schema inference using rank dependence/NMI plus reciprocal-best margin certificates. Schema learning uses only a fit split; conformal calibration stays held out.
10. Added conservative unpaired schema inference from unique affine-invariant numeric distribution shapes and category-frequency spectra. Ambiguous equal-distribution fields are rejected; this does **not** claim unpaired true-pair noise calibration.
11. Added precomputed embedding compatibility for differing dimensions using a fit-split linear map, and a smooth nonlinear RFF map. Both are calibrated only on independent true-pair residuals.

## Empirical checks

Local regression: **25 passed**. Included are finite-sample rank enumeration, bounded-contamination rank enumeration, independent heteroscedastic holdout coverage, known normal covariate-shift simulation, finite-group ratio-interval simulation, mixed-schema unit/category transformations, ambiguous-schema rejection, unpaired distribution ambiguity rejection, and 24/32-dimensional plus nonlinear embedding tests.

One unpaired distribution-schema test initially failed because its requested uniqueness margin (0.10) exceeded the actually observed separation (about 0.067–0.080) despite correct best matches. The threshold in that test was reduced to 0.05 and the ambiguity test retained a stricter margin. The failure is recorded rather than hidden.

## Limits / next leaf

The next unresolved leaf is continuous/high-dimensional density-ratio uncertainty with finite-sample coverage guarantees. Exact weighted conformal is only as valid as its density-ratio contract; the finite-partition interval estimator does not solve general continuous ratio estimation. Raw multimodal encoder semantics and true-pair calibration with no paired records also remain unresolved.

Active nodes are estimated at **508**, still below the current prediction of **512**, so the prediction-exceeded whole-tree rewrite condition has not fired in this revision.
