# AGI root problem — problem tree

Updated: 2026-08-19 12:45 JST

## Root
Deliver AGI without lowering the achievement criteria, not merely as a prototype/research artifact, but in a form that is actually usable.

AGI itself is distinct from this problem-solving mechanism. Achievement must not be claimed without empirical evidence.

## Problem-count prediction and mandatory rewrite history
The previous prediction was **31** active parent+child problems. After resolving P3.3.3b, the next leaf P3.7.2 was attempted directly. A final secret generator bank cannot honestly be completed by placing its content in this public repository; the attempt therefore remained unresolved and was decomposed into five necessary subproblems: sealed execution/custody, cross-domain independent banks, adversarial variants, contamination/leakage auditing, and secret rotation/reproduction. That transient decomposition raised the active count from 31 to **36**, exceeding the prediction and triggering the required cross-tree rewrite.

The transversal rewrite below is not a duplicate-only merge. It replaces several old open branches with three cross-cutting solution problems. The main low-probability/high-leverage move is to stop treating final evaluation as a static benchmark collection and instead make it a **post-freeze blind evaluation foundry**: multiple independently custodied sealed generators create tasks only after the candidate digest is frozen; competent humans are calibrated on the same generated families; the same service runs the candidate and an independent rerun. This simultaneously attacks secret task generation, contamination, human baselines, generality/performance evidence, and independent audit without weakening any gate.

Reforecast total parent+child problems: **36**. X2.1's first direct implementation attempt established a concrete sealed-bank contract but did not supply real independently custodied non-public banks, so X2.1 was decomposed into three children. The first X2.1b provisioning attempt then produced a contributor/qualification path but still did not produce real third-party banks, so X2.1b is decomposed into three children. Tree v2 now enumerates **36** active non-replaced problems, exactly at the reforecast; a second transversal rewrite triggers only if a later decomposition raises the active count above 36.

## Tree v2 — active non-replaced problems

- P0 [open] Deliver rigorously demonstrated, practically usable AGI.
  - P1 [open-parent] Define falsifiable AGI acceptance contract.
    - P1.1 [resolved-v0] Specify generality criterion.
    - P1.2 [resolved-v0] Specify performance criterion.
    - P1.3 [resolved-v0] Specify autonomy criterion.
    - P1.4 [resolved-v0] Specify practical-delivery criterion.
    - P1.5 [resolved-v0] Specify anti-contamination / anti-gaming criterion.
  - P3 [resolved-runtime-v2] Provide the evaluator-controlled substrate needed to freeze criteria/tasks/candidate identity, execute candidates in isolated environments, score conservatively, and emit replay-checkable evidence.
    - P3.1 [resolved-v1] Anti-weakening, fail-closed acceptance-manifest validation.
    - P3.2 [resolved-v1] Physically separated public/private task packs plus cryptographic freeze lock for manifest, packs, provenance, and immutable candidate identity.
    - P3.3 [resolved-runtime-v2] Execute candidates in evaluator-controlled task environments, including writable artifact arenas and evaluator-mediated isolated external-service tools while candidate IP networking remains disabled.
      - P3.3.1 [resolved-v1] Isolated final container protocol: no candidate network, read-only root, dropped capabilities, no-new-privileges, PID/resource controls, immutable candidate digest.
      - P3.3.2 [resolved-runtime-v1] GitHub Actions run `32211831216` exercised the original isolated final-container mechanics. This is harness evidence only, not AGI evidence.
      - P3.3.3 [resolved-runtime-v2] Support nontrivial software/data/planning artifacts and evaluator-controlled tools.
        - P3.3.3a [resolved-v1] Writable `/work` arena with pristine read-only inputs, bounded no-symlink workspace snapshots, and hidden data-only artifact graders.
        - P3.3.3b [resolved-runtime-v2] A `network=none` candidate reaches only an evaluator AF_UNIX broker; external-service tools execute in separate immutable-digest provider containers whose network and credential configuration comes from sealed private rows. GitHub Actions run `32212664460` passed 25 tests plus both final-container and broker/provider mechanical integrations, including a credentialed provider/private-network service and credential-leak check. Harness evidence only, not AGI evidence.
      - P3.3.4 [resolved-framework] Evaluator-owned, hash-chained autonomy telemetry and required derived metrics. Instrumentation only; it does not establish the autonomy gate.
    - P3.4 [resolved-v1] Conservative family/domain scoring with Wilson lower bounds and no averaging away required failures.
    - P3.5 [resolved-framework] Deterministic fresh-task generator adapter with seed/generator/file provenance.
    - P3.6 [resolved-v1] Tamper-evident evidence bundles, per-record hash chaining, and offline verification/recomputation.
  - X1 [open] **Immutable AGI appliance.** Build the AGI candidate itself, distinct from this problem solver, directly as the exact third-party-runnable artifact to be evaluated: immutable build identity, documented API/application, persistence, observability, resource envelope, reproducible install/run path, and repeatable acceptance entrypoint. Replaces old P2 + P8 and the deployment side of P9.
  - X2 [open-parent] **Post-freeze blind human-calibrated evaluation foundry.** After X1 candidate digest freeze, generate secret tasks under independent custody, calibrate competent humans on the same families, execute candidate trials, and perform an independently custodied rerun. Replaces old P3.7/P3.7.2/P3.7.3 + P4 + P5 + the evaluation side of P9.
    - X2.1 [open-parent] Establish independently custodied, digest-pinned sealed generator banks spanning every required domain/family, with generator content unavailable to candidate development and at least two independent custody lineages per required family.
      - X2.1a [resolved-framework] Executable fail-closed bank registry/execution contract: no inline task/template/answer/secret content, immutable offline provider containers, two independent custody groups + implementation lineages + provider digests + content commitments per required family, and a commitment-only freeze lock. PR #13 merged after GitHub Actions run `32213000978` passed the full AGI eval integrity workflow. This validates the mechanism only; it does not establish that real independent banks exist.
      - X2.1b [open-parent] Provision real non-public sealed generator images and seed schedules under at least two genuinely independent custodians/implementation lineages for every preregistered required family. Public toy labels or self-asserted independence do not satisfy this leaf.
        - X2.1b1 [open] Source and qualify genuinely independent custodians for every required family, including conflict-of-interest and non-sharing constraints; a candidate list or public precedent is not a commitment to participate.
        - X2.1b2 [open] Have each accepted custodian construct substantive non-public generator content plus committed final seed schedules independently, with no candidate-specific tuning or shared private templates across lineages.
        - X2.1b3 [framework-pending-CI] Privately receive/stage the immutable bank images and run reserved offline structural qualification without publishing generated tasks. PR #14 implements the contributor protocol, staged-digest check, reserved qualification namespace, every-family structural validation, and hash-only qualification evidence; real bank staging remains outstanding even if CI passes.
      - X2.1c [open] Obtain and freeze auditable custody/lineage/content commitments before final candidate trials, then verify the staged image digests and registry lock without exposing generator content.
    - X2.2 [open] Build contamination/leakage auditing plus adversarial/metamorphic variant generation that can invalidate compromised families fail-closed rather than silently substitute them.
    - X2.3 [open] Collect competent-human reference distributions on generated families and freeze statistically justified thresholds/sample sizes before candidate final trials.
    - X2.4 [open] Run blind final generality/performance trials and an independently custodied statistically meaningful rerun against the exact X1 digest, preserving failures and provenance.
  - X3 [open-parent] **Long-horizon autonomy/security proving ground.** Use the same post-freeze evaluator substrate to measure autonomous decomposition, tool use, recovery, state persistence, containment and bounded operation under evaluator-injected faults and adversarial conditions. Replaces old P6 + P7 and the autonomy/security part of P9.
    - X3.1 [open] Long-horizon jobs with evaluator-owned fault injection, checkpoints, recovery observations and strict intervention accounting.
    - X3.2 [open] Adversarial policy/security trials covering tool misuse, privilege/secret boundary pressure, malicious inputs/artifacts and containment failures.
    - X3.3 [open] Resource/cost/duration stress trials that establish bounded operation and reproducibility under the frozen operational envelope.

## Replaced old open problems
P2, P3.7, P3.7.2, P3.7.3, P4, P5, P6, P7, P8 and P9 from Tree v1 are replaced by X1–X3 above and are excluded from the active count. Resolved descendants in the retained P1/P3 branches remain active historical prerequisites; the removed P3.7 branch is preserved by repository history but not double-counted.

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
X2.1b3 remains selected until PR #14's CI result is known. After the mechanical qualification path is validated, the unresolved real-world bottlenecks are X2.1b1 and X2.1b2: actual independent custodians and their substantive non-public bank images. No self-created duplicate banks may be counted as independent merely to close the tree.

## Evidence status
**No AGI achievement is claimed.** P3 and X2.1a are evaluation-infrastructure evidence only. X1, X2 and X3 remain open, so no claim is made that generality, performance, autonomy, robustness, practical delivery or independent reproduction has passed.
