# rev101 — explicit bounded-noise attribute compatibility

Root remains **NOT_AGI**.

The noise-tolerant attribute leaf was attacked under an explicit semantic contract: a pair is attribute-compatible only when its observed feature vectors are within a caller-declared L-infinity tolerance. A partial positive-edge-budget branch-and-bound search finds a complete minimum-cardinality witness, and exclusion feasibility searches certify forced pairs. The tolerance is never inferred silently; if the declared bound is too small, the system rejects or abstains. Search/exclusion cutoffs fail closed.

Focused regression: **4 passed**. Twenty random five-node noisy cases were checked against an independent exhaustive compatibility/budget oracle with no false forced pair. A 24-vs-27 clustered continuous-attribute case with repeated latent clusters, three unmatched distractors and two edge flips found a full witness; every released identity lies in the planted mapping. A symmetric cycle releases none, and a deliberately undersized tolerance rejects shifted unique attributes.

This is not general noisy-attribute inference because the noise radius is externally supplied and attributes share one Euclidean schema. The leaf is decomposed into `...c1` explicit bounded compatibility (`solved_v0_1`), `...c2` learned/calibrated compatibility uncertainty (unresolved), and `...c3` missing/heterogeneous/mixed-schema attributes (unresolved). Estimated active nodes: **483**, below 512.