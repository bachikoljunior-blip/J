# AGI-GI rev500 — corrected-SOJ production caller replay envelope

## Scope

This revision owns only `w1r-h6/corrected-split-or-johnson/production-caller-binding-replay-envelope`.

It structurally consumes the public output contract described by the separately owned rev400 / PR #246 production-caller binder. It does not import rev400 branch-only code and does not modify rev292, rev293, rev295, rev340, rev360, rev400, CRX, `MAIN.md`, proof-DAG, recurrence, or shared coordination implementations.

## Contract

`soj_caller_replay_envelope_v1.py` independently rebuilds the exact deterministic digest payload published by rev400 and fails closed unless:

- schema is exactly `corrected-soj-production-caller-binding-v1`;
- `canonical` and `exact` are literal booleans equal to `true`;
- mode is exactly one of `small_ground_terminal` or `larger_ground_recursive`;
- result status is exactly `exact_nonempty` or `exact_empty`;
- all six proof identities are lowercase 64-hex SHA-256 strings;
- `accounted_work` is a nonnegative integer and the caller's predeclared `max_accounted_work` is not exceeded;
- `current_domain_size` and `original_root_n` are positive integers with `current_domain_size <= original_root_n`;
- the caller explicitly reports literal `replay_verified=true` after replaying its producer evidence.

The accepted state is sealed into a second deterministic SHA-256 identity covering the caller-binding identity, result/transition/original-instance identities, exact mode/status, charged work cap, and recurrence-domain measurements. Replay reconstructs the envelope from the original binding and rejects field drift or identity tampering.

## Strict boundary

This is a replay/accounting envelope only. It does not authenticate a SHA-looking identity, execute String Isomorphism, construct a Johnson reduction, execute the recursive child, prove recurrence closure, or promote a branch-only rev400 result into main-integrated production semantics.

The envelope exists to make a future production consumer fail closed on TOCTOU drift between an already-verified caller binding and the resource/domain context in which that binding is consumed.

AGI state remains `NOT_AGI`.
