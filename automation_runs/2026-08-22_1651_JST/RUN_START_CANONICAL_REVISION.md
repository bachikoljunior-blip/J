# Run-start canonical revision hardening

## Observed failure

At run start `3610223404f44988fd2b91bf65c346b8674da739` already reached
integrated `AGI-GI rev952` commit
`cc5e882b8a45d5e24e9878baf59639535255b4cd`, while `MAIN.md`
still declared rev950. Copying that declaration produced an incorrect record
and required an append-only correction.

## Existing-world audit and solution

The repository already defines canonical integrations in
`automation/agi_gi_main_revision_guard.py`: only reachable subjects matching
`AGI-GI revN:` count, and the numeric maximum wins. The new record generator
reuses that parser and the exact starting ref; it deliberately never reads
`MAIN.md`.

It emits one deterministic JSONL object to stdout. Ref resolution, absence of
a canonical integration, invalid SHA, empty run identity, and a timestamp
without the `+09:00` offset all fail closed before persistence.

## Boundary

This prevents run-history revision drift. It does not implement String
Isomorphism, Graph Isomorphism, general intelligence, or AGI.
