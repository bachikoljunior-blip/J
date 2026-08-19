# AGI root problem — problem tree

Updated: 2026-08-19 11:05 JST

## Root
Deliver AGI without lowering the achievement criteria, not merely as a prototype/research artifact, but in a form that is actually usable.

AGI itself is distinct from this problem-solving mechanism. Achievement must not be claimed without empirical evidence.

## Initial total problem-count prediction
Predicted total parent+child problems: **31** (working estimate; revise when observed tree exceeds it).

## Tree v0

- P0 [open] Deliver rigorously demonstrated, practically usable AGI.
  - P1 [open] Define falsifiable AGI acceptance contract.
    - P1.1 [resolved-v0] Specify generality criterion.
    - P1.2 [resolved-v0] Specify performance criterion.
    - P1.3 [resolved-v0] Specify autonomy criterion.
    - P1.4 [resolved-v0] Specify practical-delivery criterion.
    - P1.5 [resolved-v0] Specify anti-contamination / anti-gaming criterion.
  - P2 [open] Build an AGI system candidate distinct from the problem solver.
  - P3 [open] Build evaluation harness and held-out task generation.
  - P4 [open] Demonstrate generality empirically.
  - P5 [open] Demonstrate performance empirically.
  - P6 [open] Demonstrate autonomy empirically.
  - P7 [open] Demonstrate robustness, security, and bounded operation.
  - P8 [open] Package the demonstrated system for practical use.
  - P9 [open] Independently reproduce evidence and audit achievement claim.

## Resolved leaf: P1 acceptance contract v0

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

## Next leaf
P3: turn this contract into an executable, versioned evaluation manifest/harness so later system work is judged against fixed tests rather than post-hoc criteria.

## Evidence status
No AGI achievement is claimed. This commit only establishes the initial problem tree and resolves the first leaf at specification level.