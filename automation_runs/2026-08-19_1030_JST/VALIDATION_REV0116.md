# rev116 additional validation

Root remains **NOT_AGI**. These checks validate only the bounded calibration/support machinery.

- Full deterministic/local regression: **54 passed**; Python compileall passed.
- End-to-end supported covariate-shift pipeline: 18 independent additional runs, all 18 produced a finite ready calibrator; minimum empirical test coverage was 0.9252 and mean coverage 0.9374 for a nominal conditional alpha of 0.1 plus certificate events in that stress setup. These frequencies are sanity checks, not substitutes for the stated model contracts.
- Known-truth Lipschitz ratio interval stress: **600 grid point checks, 0 misses** across 120 random exponential tilts; **240 32-dimensional slab point checks, 0 misses** across 80 runs; all 80 slab runs had finite upper bounds under the selected sample sizes and mild smoothness.
- Robust weight-interval conformal stress: **560** random small interval instances (n=2..8) were exhaustively enumerated over every lower/upper calibration-weight corner and both test-weight endpoints; **0 cases** had the robust threshold below the worst exact weighted threshold.
- 64-dimensional slab benchmark: 120,000 P samples + 120,000 Q samples, 16 slabs, about 0.096 seconds in the local test environment; all 16 upper intervals finite. This is a performance observation for one synthetic setup, not a general complexity certification.

Known limitations remain unchanged: global smoothness/model membership outside recognized evidence contracts is not certified from fit quality; high-dimensional slab bounds can be vacuous as domain diameter or L grows; the root AGI criteria are untouched.
