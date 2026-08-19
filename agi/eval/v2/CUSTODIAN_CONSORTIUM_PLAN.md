# Federated blind-evaluation custodian consortium plan

Updated: 2026-08-19 13:xx JST

This is a sourcing and execution plan for external evaluation custody. It is **not** evidence that any named organization has agreed to participate, and it is not AGI evidence.

## Why this exists

The previous X2.1b1 leaf required genuinely independent custodians, not project-owned fixtures or public benchmark labels. A direct attempt found no existing relevant correspondence in the connected mailbox and no already-accepted outside custodian. Public research nevertheless confirms that several independent organizations already operate pieces of the required workflow. The useful move is therefore to recruit a federation around a capability-backed work order rather than ask one organization to cover the whole acceptance suite.

## Capability precedents and public routes

These organizations are **feasibility precedents / possible outreach targets only**. Naming them here does not imply endorsement, interest, commitment, or participation.

| Organization | Publicly demonstrated relevant capability | Public route |
|---|---|---|
| ARC Prize Foundation | Hidden/semi-private evaluations, controlled verification, human baselines, published independence/conflict policy | https://arcprize.org/policy ; team@arcprize.org |
| METR | Third-party frontier-model evaluations, private evaluation work, autonomous-task suites | https://metr.org/risk-assessment/ ; https://metr.org/contact ; info@metr.org ; tasks@metr.org |
| Epoch AI | Independent benchmark construction, math benchmark curation, human-baseline work, custom research/consultations | https://epoch.ai/contact ; info@epoch.ai |
| OpenMined | Privacy-preserving external AI audit infrastructure and a secure-enclave AI-evaluation pilot with AISI/Anthropic | https://openmined.org/partner/ ; https://openmined.org/blog/secure-enclaves-for-ai-evaluation/ |
| NIST Center for AI Standards and Innovation (CAISI) | Government AI evaluation work; secure-evaluation collaboration with OpenMined announced in 2026 | https://www.nist.gov/caisi |
| UK AI Security Institute (AISI) | Frontier-system evaluation research, multi-modal evaluation agenda, bilateral/international evaluation partnerships | https://www.aisi.gov.uk/ ; https://www.aisi.gov.uk/research-agenda |

No private benchmark content from any organization is requested or stored in this repository.

## Federation design: evaluation capsules

A custodian should not be recruited to supply only a benchmark file. For each assigned family, it supplies a sealed **evaluation capsule** whose private side is held by that custodian and whose public side is commitment-only.

A capsule must bind:

1. stable custodian identity and signing principal;
2. external identity/conflict evidence commitment;
3. assigned preregistered family IDs;
4. immutable offline generator image digest;
5. non-public generator/task/answer/template commitment;
6. independently chosen final seed-schedule commitment;
7. adversarial/metamorphic variant generator commitment;
8. contamination canaries / leakage-audit procedure commitment;
9. competent-human calibration protocol and frozen sample/threshold plan;
10. declarations covering non-sharing, no candidate-specific tuning, retention, leakage invalidation, and candidate-developer separation.

Every required family needs at least two capsules from genuinely independent custody groups and implementation lineages. Documentary relabeling does not create independence.

## Public work order

Repository issue #16 is the public expression-of-interest channel. Prospective custodians are asked to disclose only capability/identity/contact metadata in public and keep task content, answers, seeds, templates, private keys, and generator source out of the issue.

Acceptance remains fail-closed and uses the signed custodian machinery already present in `agi/eval/v1/`. The signature proves control of an accepted key over a declaration; it does not prove real-world independence. External conflict/identity audit is therefore mandatory before a custodian counts toward coverage.

## Recruitment sequence

1. Publish the capability-backed work order (done via issue #16).
2. Prepare targeted outreach drafts for organizations with demonstrated relevant capability; do not represent public precedent as participation.
3. For each response, map offered families against the frozen family matrix and reject coverage gaps or duplicate lineages.
4. Verify signed participation declaration and open the external identity/conflict evidence under controlled audit.
5. Only after acceptance, privately exchange capsule interface details and stage immutable images.
6. Require a second independent lineage for the same family before the family is coverage-complete.
7. Freeze capsule commitments only after the exact candidate digest is frozen, then proceed to reserved qualification and final trials.

## Success condition for the recruitment slice

Recruitment is not complete until every required family has at least two accepted, externally audited, non-colluding custodians with signed commitments. Public candidate lists, email drafts, expressions of interest, or a single accepted custodian do not resolve the slice.

## Evidence status

The public work order and this plan improve execution readiness only. At the time of writing, no real outside custodian has been counted as accepted, no substantive third-party sealed generator bank has been staged, and no AGI claim is made.
