# Signed custodian acceptance protocol

This protocol turns an X2.1b1 participation statement into a tamper-evident evaluator input. It does **not** make a self-declaration true: legal identity, control relationships, conflicts, and non-sharing claims still require external evidence and X2.1c audit before a custodian is counted as genuinely independent.

## Acceptance record

A custodian prepares one canonical JSON object with schema `agi-custodian-acceptance-v1`. It identifies a stable custodian ID, signing principal, implementation lineage, SHA-256 commitments to separately retained identity evidence and conflict-review evidence, every preregistered domain/family assignment it accepts, and all required declarations.

Required true declarations state that final bank content remains non-public through the independent rerun, no private task material is shared with peer lineages, no candidate-specific tuning occurs after assignment, material leakage invalidates the affected family fail-closed, and audit evidence is retained. Required false declarations state that the custodian is not controlled by the candidate developer and the candidate developer has no access to final bank content.

The evaluator never treats an organization name in a plan, issue, or note as participation. Participation begins only when the evaluator has a valid signed acceptance plus the separately reviewable evidence commitments named by that acceptance.

## Signature

The acceptance JSON is canonicalized with the evaluator's `canonical_json` function, terminated by a newline, and signed using an OpenSSH signing key with namespace `agi-custodian-acceptance-v1`. The evaluator keeps an `allowed_signers` file mapping the accepted principal to the public key and verifies the detached signature with `ssh-keygen -Y verify`.

A signing key proves control of the key, not organizational independence. Two records signed by two keys controlled by the same entity are still one real custodian and must fail the later identity/conflict audit even if the documentary coverage gate cannot infer that fact by itself.

## Bundle gate

`verify_custodian_bundle.py` verifies every detached signature before computing coverage. For every required family, documentary coverage requires at least two distinct custodian IDs, identity-evidence commitments, implementation lineages, and signing principals. The report stores only hashes and assignment counts and labels the result `requires_external_identity_and_conflict_audit`; it intentionally never upgrades documentary separation into a factual independence claim.

The family matrix remains authoritative. Acceptances for undeclared families fail closed, and changing the final family surface requires a new preregistered/frozen foundry input lock rather than silently dropping hard families.

## What resolves X2.1b1

X2.1b1 is not resolved by these files or by toy signatures. It requires enough real accepted custodians to cover every frozen required family at the configured independence minimum, plus external evidence that the claimed custody groups and implementation lineages are genuinely independent. Only then can the tree advance from sourcing/qualification to substantive private bank construction and final custody attestation.
