# Security model

J treats model output and generated skills as untrusted input.

## Enforced in the core

- File paths are resolved under one repository root; absolute paths, traversal, and `.git` access are rejected.
- Writes are allowlisted to `skills/`, `tests/generated/`, `docs/`, `state/`, `reports/`, and `workspace/`.
- Core code, workflow configuration, acceptance tests, benchmark definitions, and project metadata are protected from agent writes.
- The agent exposes no arbitrary shell or arbitrary Python execution tool.
- Validation subprocesses are fixed commands, run with token-, secret-, password-, and API-key-like environment variables removed.
- Generated skills are parsed before loading. Imports are allowlisted; dangerous builtin access, dunder attributes, classes, async code, context managers, and executable top-level statements are rejected.
- GitHub Actions uses a read-only repository token.

## Important limitation

These controls are defense in depth at the application/tool layer. They are not equivalent to a hardened VM, seccomp profile, or formally verified language sandbox. Generated skills should therefore run in an ephemeral container for higher-risk deployments, with CPU, memory, filesystem, and network controls supplied by the host.

## Reporting

Do not include secrets in an issue. Report the smallest reproducible example and the affected commit.
