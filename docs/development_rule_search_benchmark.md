# Development benchmark: compositional numeric rule search

This is **not AGI evidence** and is not part of the sealed achievement suite. It is a deterministic development benchmark used only to expose scaling behavior of the current symbolic synthesis mechanism.

The generator samples expressions from the same numeric `Input/Constant/Add/Multiply` grammar used by the searcher. Three demonstrations use inputs 1, 2, and 4; generalization is checked on 3, 5, 7, and 11. The beam limit is 2,000 candidates per cost level.

Local run results after the current implementation:

| target expression cost | trials | solution found | held-out generalized | mean explored behaviors | max explored behaviors |
|---:|---:|---:|---:|---:|---:|
| 3 | 30 | 30 | 30 | 15.4 | 31 |
| 5 | 30 | 30 | 30 | 29.63 | 127 |
| 7 | 30 | 30 | 30 | 90.7 | 400 |
| 9 | 10 | 10 | 10 | 108.7 | 354 |
| 11 | 10 | 9 | 9 | 403.4 | 2,641 |

Interpretation: behavioral-equivalence pruning keeps the small in-grammar search tractable through these generated cases, but the first miss appears at cost 11 and the explored-behavior count rises sharply. More importantly, because targets are sampled from the searcher's own hand-built grammar, this does **not** resolve open-domain rule induction or the requirement to learn abstractions outside that grammar. Those remain explicit unresolved child problems.
