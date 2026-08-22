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

The active rev275 registry record remains independently owned and legacy/non-schema-v2. rev288 does not modify or normalize it and will not fabricate `attempt_solution` or `publish` evidence while canonical registry replay is unavailable.

Likewise rev276 / PR #221, rev281 / PR #226, rev283 / PR #228, rev284 / PR #229, rev285 / PR #230, rev286 / PR #231, and any rev287 work remain untouched. No sibling workflow is cancelled or manually rerun; no sibling branch or PR is rebased, force-pushed, overwritten, closed, merged, or modified.

## Validation

The dedicated rev288 smoke runs the focused strict-type/replay regression suite and `py_compile`. It also verifies that the rev288 module/test do not import the active rev281/rev283/rev284/rev285/rev286 branch-only modules.

AGI state remains `NOT_AGI`.
