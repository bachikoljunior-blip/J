# rev288 — strict corrected-SOJ Johnson evidence normalization

## Scope

Claim: `chatgpt-session-j-rev288-soj-strict-evidence-normalization-20260822T1144JST-d409a702`.

This revision owns only `w1r-h6/corrected-split-or-johnson/strict-johnson-transition-terminal-evidence-normalization`.
It is deliberately file-disjoint from rev275–rev287 and from every CRX1/CRX2/CRX3 shared implementation path.

## Problem

Several downstream corrected Split-or-Johnson consumers necessarily read public fields from independently owned transition and terminal artifacts. A consumer that normalizes those fields with `bool(...)`, `int(...)`, or `float(...)` before validating their original type can accidentally accept coercible values such as `"false"`, `1`, `2.5`, numeric strings, NaN, or infinity.

rev288 adds a strict structural boundary before accounting or production dispatch. It consumes sibling contracts only as read-only public field shapes and imports no active sibling implementation.

## Contract

`normalize_corrected_soj_johnson_evidence`:

- accepts only exact `bool` values for theorem/canonical/exact/cost/terminal gates;
- accepts only exact `int` values for combinatorial dimensions and counters;
- accepts only finite JSON-style numeric values for cost fields;
- validates the exact corrected-SOJ Johnson status/kind and exact primitive-Johnson terminal statuses;
- requires the complete `J(v,k)` vertex count `C(v,k)` and identical transition/terminal Johnson parameters;
- requires the terminal root/domain to match caller context and the complete Johnson domain;
- requires a strict pre-transition domain reduction;
- permits a missing upstream terminal proof identity but records that fact explicitly; malformed non-null identities fail closed;
- emits one deterministic SHA-256 identity over the complete normalized transcript;
- provides replay by full reconstruction/equality rather than trusting a stored digest.

This layer performs **no** transition admission, terminal execution, recurrence accounting, coset promotion, caller routing, or production integration.

## Parallel boundary

The formerly blocking legacy rev275 record was superseded by its independently owned schema-v2 takeover claim. rev288 did not modify either record. With the canonical registry restored, rev288 obtained exclusive `attempt_solution` and `publish` admission with zero conflicts and persisted both replayable evidence objects from registry source `e5118818cea87bfa4b04d9d1968cb5877a6d4b39`, digest `sha256:e3eb4671d7271a0a57bf095314edc12d240a5ab5546fce34601dca24108f3a74`.

rev276 / PR #221, rev281 / PR #226, rev283 / PR #228, rev284 / PR #229, rev285 / PR #230, rev286 / PR #231, rev289 and later sibling work remain untouched. No sibling workflow is cancelled or manually rerun; no sibling branch or PR is rebased, force-pushed, overwritten, closed, merged, or modified.

## Validation

The dedicated rev288 smoke runs the focused strict-type/replay regression suite and `py_compile`. It also verifies that the rev288 module/test do not import active sibling corrected-SOJ branch-only implementations. On the evidence-producing exact head, all 21 focused tests passed, compile and import-boundary checks passed, and canonical `attempt_solution` / `publish` decisions were both `admitted=true`, `mode=exclusive`, `conflicts=[]`. The repository-wide phase-evidence guard subsequently replayed the persisted evidence successfully on the proposal head.

AGI state remains `NOT_AGI`.
