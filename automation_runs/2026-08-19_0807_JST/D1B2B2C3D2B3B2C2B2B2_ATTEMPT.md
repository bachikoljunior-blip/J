# D1b2b2c3d2b3b2c2b2b2 attempt — operational quotient without a declared latent summary

## Direct attempt

The latent-coordinate classification target is attacked by eliminating latent coordinates from the equivalence criterion. A latent model is mapped to the family of observable push-forward laws induced by the declared observation/intervention regimes. Two hidden models are in the same operational equivalence class exactly when that family of laws is equal. This definition does not require a latent-space isomorphism or a user-declared shared sufficient statistic.

For Euclidean observable outcomes and a finite intervention family, `operational_equivalence.py` implements a representation-independent empirical discrepancy with a Gaussian characteristic kernel. It uses independent bounded linear-MMD blocks and an explicit simultaneous Hoeffding interval. Finite data therefore yields one of `equivalent`, `different`, or `undetermined`; lack of evidence is not converted into a false equality claim.

An exact order-invariant signature is also implemented for finite empirical atomic measures only. It is deliberately not interpreted as identifying unknown population laws.

## Result and limits

This resolves a bounded child: representation-independent operational quotienting for a finite declared regime family and finite-dimensional Euclidean outcomes, with conservative finite-sample auditing. It does not solve the unrestricted parent. Remaining children cover infinite/adaptive intervention families, heterogeneous trajectories, safe substitution for planning/counterfactuals, and canonical representative selection. Focused tests: 4 passed. Root certification remains `NOT_AGI`.
