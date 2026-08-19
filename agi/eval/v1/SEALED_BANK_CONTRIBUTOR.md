# Sealed generator-bank contributor protocol

This protocol is for third-party custodians who contribute **non-public** final-evaluation generator banks. It is evaluation infrastructure, not an AGI claim. Final task templates, answer logic, private datasets, seed schedules, and generator source MUST NOT be committed to J or disclosed to candidate development.

## Independence requirement

For every preregistered required family, the frozen registry requires at least two banks that differ in all of the following: custody group, implementation lineage, immutable provider-image digest, and sealed-content commitment. A label alone is not evidence of independence. Each custodian must retain records sufficient for the later X2.1c custody/lineage attestation and conflict-of-interest audit.

A custodian is disqualified for a family if its final generator content was materially derived from another bank assigned to that family, shared with candidate developers before the final trial, or constructed from candidate-specific failure traces. Common public standards/libraries are allowed, but shared task templates, answer keys, private datasets, or seed schedules are not.

## What the custodian keeps private

Keep generator source, task templates, answer/grader construction logic, private datasets, final seed schedules, signing material, and any internal review notes outside J. The final provider image must contain everything needed to generate its assigned tasks **offline**. It must not need runtime credentials, network access, host mounts, or external services.

## What the custodian delivers to the evaluator

Deliver the immutable OCI/container image through a private registry or offline image-transfer channel, not through this repository. Separately provide the registry metadata needed by `agi-sealed-bank-registry-v1`: bank ID, required domain/families, custody group, implementation lineage, image reference for staging, immutable `sha256:` image digest, sealed-content commitment, seed-schedule commitment, and later the X2.1c attestation commitments.

The image must implement `agi-taskgen-request-v1`: one JSON request on stdin and one JSON object on stdout containing `public` and `private` objects. The evaluator runs it with `network=none`, a read-only root, no host mounts, no environment-secret injection, dropped capabilities, `no-new-privileges`, PID/resource limits, and a disposable tmpfs.

## Qualification without publishing task content

Before the bank can enter a final registry, the evaluator stages the image locally, verifies that its image ID equals the declared immutable digest, validates the registry against every required family, and performs a **reserved qualification invocation**. Qualification output is never given to the candidate and is not stored in J; the evaluator stores only structural pass/fail and cryptographic hashes of the returned public/private objects.

The reserved seed namespace begins with `__qualification__:` and MUST be excluded from the committed final seed schedule. A bank must return a valid public task plus private grader record for its assigned family under this namespace. Qualification checks that the public half contains no forbidden grader/answer/private keys and that the private grader uses a supported fail-closed grader type. Passing qualification proves protocol mechanics only; it does not prove task quality, novelty, independence, or absence of contamination.

## Final freeze sequence

1. Candidate-development access to final banks remains prohibited.
2. Custodians finalize content and seed schedules independently, then provide commitments.
3. Evaluator stages all immutable images and runs reserved qualification.
4. X2.1c verifies custody/lineage attestations and freezes the registry lock.
5. The exact candidate digest is frozen before final task generation.
6. Final seeds/nonces are opened or derived according to the committed schedule only after the candidate freeze.
7. Generated public/private packs, generator provenance, candidate digest, and evidence are frozen and hash-linked.
8. Independent rerun custody receives the same frozen identities/commitments but does not receive candidate-development artifacts or unreleased task content.

## Non-evidence warning

A registry that contains placeholder custodians, self-created duplicate banks, public generator source, or toy fixtures is useful only for mechanical testing. It cannot satisfy X2.1b or support an AGI achievement claim.
