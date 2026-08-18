# Fixed-root run: nonlinear/distributed cross-environment representation alignment

The broad nonlinear/distributed feature-correspondence leaf was attempted without lowering its scope. A paired-probe RBF-kernel baseline solved only the information-preserving paired nonlinear subcase, so the parent was decomposed. The next unpaired branch was then processed rather than claimed solved.

For unpaired samples with shared condition identities, an orthogonal distributed subcase was implemented from condition centroids with full-rank identifiability and held-out covariance checks. A rank-deficient condition family is explicitly rejected. This solved only a linear/orthogonal child.

The nonlinear unpaired branch was then attempted. An initial isotonic quantile transport was rejected after finite-sample tests exposed artificial flat regions and poor extrapolation. It was replaced by a bounded one-dimensional monotone low-degree polynomial transport, fitted only from condition-wise quantiles and validated on disjoint conditions by Wasserstein distance. Information-destroying folds such as x→x² are rejected by the positive-derivative gate.

Full candidate regression suite after these changes: 138/138 passed. The next unresolved leaf is multivariate unpaired information-preserving nonlinear diffeomorphism recovery. Root certification remains NOT_AGI; active problem count is 131 against the current prediction of 218, so the tree-wide consolidation trigger has not fired.
