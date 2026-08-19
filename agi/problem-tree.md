# AGI root problem — problem tree

Updated: 2026-08-19 12:20 JST

## Root
Deliver AGI without lowering the achievement criteria, not merely as a prototype/research artifact, but in a form that is actually usable.

AGI itself is distinct from this problem-solving mechanism. Achievement must not be claimed without empirical evidence.

## Total problem-count prediction
Predicted total parent+child problems: **31**. The currently enumerated non-replaced tree is now **31**, exactly at the prediction. The mandatory cross-tree rewrite/consolidation rule has therefore **not** triggered yet; it triggers only if the active count exceeds 31.

## Tree v1

- P0 [open] Deliver rigorously demonstrated, practically usable AGI.
  - P1 [open-parent] Define falsifiable AGI acceptance contract.
    - P1.1 [resolved-v0] Specify generality criterion.
    - P1.2 [resolved-v0] Specify performance criterion.
    - P1.3 [resolved-v0] Specify autonomy criterion.
    - P1.4 [resolved-v0] Specify practical-delivery criterion.
    - P1.5 [resolved-v0] Specify anti-contamination / anti-gaming criterion.
  - P2 [open] Build an AGI system candidate distinct from the problem solver.
  - P3 [open-parent] Build evaluation harness and held-out/fresh task generation.
    - P3.1 [resolved-v1] Anti-weakening, fail-closed acceptance-manifest validation.
    - P3.2 [resolved-v1] Physically separated public/private task packs plus cryptographic freeze lock for manifest, packs, provenance, and immutable candidate identity.
    - P3.3 [open-parent] Execute candidates in evaluator-controlled task environments.
      - P3.3.1 [resolved-implementation] Isolated final container protocol: no candidate network, read-only root, dropped capabilities, no-new-privileges, PID/resource controls, immutable candidate digest. Mechanical final-path execution still requires independent CI/runtime verification under P3.3.2.
      - P3.3.2 [open/pending-runtime-evidence] Empirically verify the final container execution/isolation path on an environment with Docker; record the run rather than inferring success from code.
      - P3.3.3 [open-parent] Support nontrivial software/data/planning artifacts and evaluator-controlled tools.
        - P3.3.3a [resolved-v1] Writable `/work` arena with pristine read-only inputs, bounded no-symlink workspace snapshots, and hidden data-only artifact graders.
        - P3.3.3b [open] Build an evaluator-controlled tool/network broker so final tasks can use bounded external services without granting unrestricted candidate networking or exposing grader secrets.
      - P3.3.4 [resolved-framework] Evaluator-owned, hash-chained autonomy telemetry and derivation of completion, intervention, recovery, elapsed-time, resource-cost, policy-violation, and state-persistence metrics. This is instrumentation only; it does not establish the P6 autonomy gate.
    - P3.4 [resolved-v1] Conservative per-family/per-domain scoring with Wilson lower confidence bounds, equal required-domain weighting, and no averaging away a required family/domain failure.
    - P3.5 [resolved-framework] Deterministic fresh-task generator adapter interface with seed and generator/file provenance hashes.
    - P3.6 [resolved-v1] Tamper-evident evidence bundles, per-record hash chaining, and offline evidence verification/recomputation.
    - P3.7 [open-parent] Supply real, secret-preserving final task-generation content and human references.
      - P3.7.1 [resolved-framework] Generator-provider request/response and provenance mechanism; final generator implementation can remain sealed while its digest/version is frozen.
      - P3.7.2 [open] Build independent sealed generator banks across every required domain, with contamination/leakage checks and adversarial variants.
      - P3.7.3 [open] Collect competent-human reference distributions, determine statistically justified per-family sample sizes, and freeze thresholds/sample-size plan before final evaluation.
  - P4 [open] Demonstrate generality empirically.
  - P5 [open] Demonstrate performance empirically.
  - P6 [open] Demonstrate autonomy empirically.
  - P7 [open] Demonstrate robustness, security, and bounded operation.
  - P8 [open] Package the demonstrated system for practical use.
  - P9 [open] Independently reproduce evidence and audit achievement claim.

## P1 acceptance contract v0

An AGI claim is accepted only if **all** gates pass on a frozen candidate, with evaluation tasks/variants not available to the candidate during development.

### G1 Generality
Pass a preregistered suite spanning at least: language/knowledge work, mathematics, software engineering, data analysis, planning/decision tasks, multimodal interpretation where applicable, and novel rule/task induction. No single domain may account for more than 25% of the aggregate score. The candidate must exceed the declared competent-human reference threshold in every required domain, not merely on the mean.

### G2 Performance
Before evaluation, each task family defines objective success metrics and a competent-human reference distribution. The candidate must reach or exceed the preregistered competent-human threshold in every required family and on the macro aggregate, with uncertainty intervals reported. Failed families cannot be hidden by averaging.

### G3 Autonomy
On long-horizon held-out jobs, the candidate must independently decompose work, use permitted tools, detect errors, recover from failures, preserve state, and produce verifiable deliverables. Evaluation records intervention count, completion rate, elapsed/cost budget, recovery rate, and policy violations. Passing thresholds are frozen before the final run.

### G4 Practical delivery
The exact evaluated candidate must be runnable by a third party from a documented package/API/application, with reproducible environment/configuration, persistence where needed, observable logs, explicit resource requirements, and a repeatable acceptance test. A notebook/demo alone does not pass.

### G5 Anti-gaming and evidence
Final evaluation uses held-out or freshly generated task instances, records seeds/configuration/tool traces/results, separates development from final evaluation, reports failures as well as successes, and requires independent rerun of a statistically meaningful sample. Any material benchmark contamination or unverifiable result invalidates that result rather than being silently substituted.

## Current leaf selection
P3.3.2 is the next unresolved leaf with the smallest integration gap: verify the implemented final container path empirically. If external runtime evidence remains unavailable, proceed to P3.3.3b rather than treating implementation as execution evidence.

## Evidence status
**No AGI achievement is claimed.** Current work establishes and hardens evaluation infrastructure only. Development fixtures, toy CI fixtures, and framework-level resolutions are explicitly not evidence that P4–P9 pass.
