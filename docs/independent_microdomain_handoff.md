# Independent sealed micro-domain evaluation handoff

This handoff is for an evaluator that did not implement the candidate. It prepares evaluation; it does not constitute an evaluation result.

## Frozen candidate

The candidate-side boundary is `src/jagi`. The frozen rule-learning bundle is identified by `candidate_rule_learning_manifest.json`. Any later change to a file inside that boundary creates a different candidate and requires a new sealed task suite.

The evaluator must independently recompute every listed file SHA-256 and the aggregate bundle SHA-256 before creating or revealing scored tasks. The recursive project-management tree, `jagi_eval`, development benchmarks, and this handoff document are outside the candidate boundary and must not provide cognitive assistance during scored execution.

## Suite custody

The evaluator creates the decisive micro-domains after the recorded freeze time. Hidden cases and expected outputs remain evaluator-side. Candidate-visible task data may contain only task identifier, type declarations, up to three worked demonstrations, runtime operator/interface descriptions, constants/documentation allowed by the task, and a preregistered program/resource budget.

The evaluator records a suite hash, task-generation time, generator/version provenance, template and near-duplicate cluster identifiers, and an exposure ledger. A suite exposed to a candidate lineage is burned for modified descendants. A rerun on the same frozen candidate is allowed only for a verified evaluator-infrastructure failure.

## Required execution

For the adaptation gate, evaluate at least 40 independently generated micro-domains. Record zero-demonstration baseline where applicable, post-adaptation final-task success, structurally related surface-different transfer, and held-out regression impact. The evaluator, not the candidate, invokes the hidden-case scorer.

The candidate must receive no hidden cases, hidden answers, evaluator notes, or calls to the recursive project solver. Tool/network traffic is logged against the frozen candidate manifest.

## Evidence return

Return a signed evaluator report containing candidate bundle hash, suite hash, harness and environment hashes, preregistration hash, aggregate metrics with uncertainty, all exclusions/retries with reasons, and G0/G2 decisions. A later full AGI claim still requires all G0–G7 gates and two independent replication teams; this micro-domain handoff alone cannot establish AGI.
