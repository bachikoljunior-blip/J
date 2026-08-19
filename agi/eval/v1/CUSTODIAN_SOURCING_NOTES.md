# X2.1b custodian sourcing notes

Status: research input only. **No organization named here has agreed to participate, and none may be counted as an X2.1b custodian without an explicit engagement, conflict check, private bank delivery, qualification, and later X2.1c attestation.**

## Why external custody is operationally plausible

Current evaluation organizations demonstrate pieces of the operating model X2 requires, although none of these public examples by itself satisfies our cross-domain bank requirement.

- ARC Prize Foundation operates ARC-AGI evaluations that include semi-private evaluation sets and verified results, and in April 2026 published a controlled ARC-AGI-3 human study with 458 participants. Its ARC-AGI-3 methodology explicitly calibrates AI action efficiency to first-time human players. Sources: https://arcprize.org/blog/arc-agi-3-human-dataset and https://docs.arcprize.org/methodology
- METR reported an independent external predeployment evaluation of GPT-5.6 Sol in June 2026 under an NDA with non-public model access. METR also describes confidentiality levels, project-specific siloing, codenames, restricted completion access, and secret repository forks for sensitive evaluations. Sources: https://metr.org/blog/2026-06-26-gpt-5-6-sol/ and https://metr.org/blog/2026-02-17-how-we-protect-confidential-information/
- The UK AI Security Institute describes differentiated need-to-know access for predeployment testing and withholding some high-risk evaluation methodology. In July 2026 UK AISI and U.S. CAISI also published a joint model evaluation, demonstrating that cross-organization evaluation workflows are operationally possible. Sources: https://www.aisi.gov.uk/blog/early-lessons-from-evaluating-frontier-ai-systems and https://www.aisi.gov.uk/blog/preliminary-assessment-of-kimi-k3s-cyber-capabilities

These are **precedents, not endorsements or participation commitments**. They support the feasibility of independent/non-public evaluation custody, not the claim that our required banks already exist.

## X2.1b1 eligibility screen

A candidate custodian must pass all of these before assignment to a required family:

1. Organizational or legally accountable individual identity can be verified.
2. No control relationship with the X1 candidate developer/problem-solving process that would undermine independent custody.
3. No material sharing agreement with the other lineage assigned to the same family covering task templates, answer/grader logic, private datasets, final seeds, or candidate-specific traces.
4. Capability to keep generator content non-public through the final trial and independent rerun window.
5. Capability to build and privately transfer an immutable OCI image or equivalent offline artifact to the evaluator.
6. Willingness to commit image/content/seed identities before final candidate trials and retain evidence for X2.1c audit.
7. Willingness to disclose enough provenance categories to audit contamination/conflicts without disclosing final task content.
8. Ability to support the preregistered family with substantive tasks that exercise the intended capability, not trivial template variations.
9. Agreement that compromised/leaked families are invalidated fail-closed and are not silently replaced after seeing candidate results.

## Independence assignment rule

For each required family, assign at least two custodians from different custody groups and implementation lineages. The same organization may contribute to multiple families, but it must never be counted as two independent lineages for one family. Shared open-source libraries or public standards do not automatically destroy independence; shared private task templates, hidden datasets, grader logic, seed schedules, or candidate-specific tuning do.

A stronger target for high-impact families is three independent lineages, allowing one lineage to be invalidated without leaving the family with only a single surviving source. This is a robustness target, not yet a frozen requirement, because increasing it would add cost and must be preregistered before final evaluation.

## Outreach artifact still missing

J now contains the technical contribution and qualification protocol, but X2.1b1 still lacks explicit accepted custodians. The next real-world artifact needed is a signed/recorded participation and conflict declaration from enough independent parties to cover every preregistered family. Until those exist, no placeholder names from this note count toward coverage.
