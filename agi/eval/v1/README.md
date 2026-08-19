# AGI evaluation harness v1

This directory is an **evaluation mechanism**, not the AGI candidate. It exists to freeze criteria before final evaluation, keep candidate-visible task material separate from grader secrets, run a frozen candidate through a narrow protocol, and produce replay-checkable evidence. Passing the development fixtures is not evidence of AGI.

## What v1 adds over v0

- **Anti-weakening manifest validation.** Required gates/domains, fail-closed behavior, uncertainty reporting, independent rerun, candidate digests and sealed private packs cannot silently be removed.
- **Public/private task separation.** `public*.jsonl` contains only candidate-visible prompts/files/policies. `private*.jsonl` contains trusted graders and preregistered competent-human lower-bound thresholds. Public packs are recursively checked for common answer/grader leakage keys.
- **Fresh-task generation with provenance.** `generate_taskpack.py` invokes deterministic generator adapters from frozen seeds and writes physically separate public/private packs plus generator/file hashes.
- **Cryptographic freeze.** `freeze_eval.py` locks manifest, public pack, private pack, generator provenance and candidate identity/digest. Final mode rejects a draft manifest, missing sample-size plan, insufficient domain/family coverage, missing provenance or mutable candidate identity.
- **Candidate isolation path.** `run_harness.py` has a development command mode and a final container mode. Final mode is fail-closed and requires the container path. The container is launched without network, with a read-only root, dropped Linux capabilities, `no-new-privileges`, a PID limit and only a read-only task mount. Hidden grader data is never mounted or put on stdin.
- **Conservative statistics.** Family success is summarized with a preregistered-confidence Wilson lower bound and compared with the frozen competent-human lower-bound threshold. Required family/domain failures cannot be averaged away. The macro number is the equal-weight average across required domains, not a task-count-weighted average.
- **Tamper-evident evidence.** Per-task records are hash-chained. The evidence bundle records candidate, manifest, task-pack and lock identities; `verify_evidence.py` recomputes hashes, the chain, and the summary.

## Development smoke test

From this directory:

```bash
python -m pytest -q
python freeze_eval.py --manifest manifest-v1.yaml --public public-example.jsonl --private private-example.jsonl --candidate-id example --candidate-digest dev-local --mode development --out dev-lock.json
python run_harness.py --manifest manifest-v1.yaml --public public-example.jsonl --private private-example.jsonl --lock dev-lock.json --candidate-id example --candidate-digest dev-local --adapter-mode command --adapter python /absolute/path/to/example_adapter.py --mode development --out dev-evidence.json
python verify_evidence.py --evidence dev-evidence.json --manifest manifest-v1.yaml --public public-example.jsonl --private private-example.jsonl --lock dev-lock.json
```

The example suite intentionally covers only two domains, so even perfect answers must **not** produce a generality/performance pass.

## Final-mode CI mechanics test

`ci_container_integration.py` is a toy mechanical test only. CI builds `ci_fixture/Dockerfile`, obtains its immutable local image ID, creates a temporary six-domain fixture, freezes it, runs the candidate in the final container path, and verifies the evidence. The fixture explicitly changes the claim to `CI MECHANICS FIXTURE — NOT AN AGI CLAIM`; it is never accepted as AGI evidence.

## Important remaining limits

This v1 harness does not supply the real held-out task bank, competent-human baseline study, autonomy-specific environments/telemetry, third-party deployment package, or independent reproduction. Those belong to later problem-tree leaves. The final manifest is intentionally `status: draft` and has no frozen `minimum_trials_per_family`, so it cannot be used for a final claim yet.

Two current external evaluation lessons influenced the design. ARC-AGI-2 separates public, semi-private and private evaluation sets and explicitly tracks efficiency; its 2026 competition targets a private 85% accuracy milestone under efficiency limits. METR's May 2026 Time Horizon 1.1 work emphasizes human-grounded task duration and confidence intervals, while its January 2026 limitations note warns that time-horizon results are domain-dependent and that very high reliability requires much larger task suites. These are methodology inputs, not substitutes for this project's frozen AGI contract.

Primary references:
- https://arcprize.org/arc-agi/2
- https://arcprize.org/competitions/2026/arc-agi-2
- https://metr.org/time-horizons/
- https://metr.org/notes/2026-01-22-time-horizon-limitations/
