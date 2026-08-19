# rev115 — certificate provenance and guarantee composition

Root remains **NOT_AGI**. Active-node count stays 512; this revision advances the current unresolved leaf without further decomposition.

Added a fail-closed contract registry for smoothness evidence. A contract manifest binds a stable contract ID to schema version, model family assumptions, proof reference, implementation SHA-256, authorized calibrator kind and failure-probability semantics. Canonical manifest hashing makes records reproducible; a contract ID cannot be silently reused with changed assumptions. Evidence records bind the manifest digest to an input digest and numeric certificate. Unknown contracts, changed manifests, wrong calibrators, missing input provenance, invalid status, nonfinite bounds or invalid failure probabilities all abstain.

Also added conservative coverage composition. If a downstream conformal stage has conditional miscoverage at most alpha whenever all certificate events hold, and the certificate events have failure upper bounds delta_i, the exported unconditional lower bound is `max(0, 1 - alpha - sum(delta_i))`. No independence assumption is made.

Focused registry tests: 4 passed. Coverage-composition tests: 3 passed. Full local regression through this revision: **48 passed**.

This still does not establish the semantic truth of an arbitrary model-family contract from finite observations. The current leaf therefore remains unresolved rather than upgrading a provenance mechanism into a false model-validity proof.
