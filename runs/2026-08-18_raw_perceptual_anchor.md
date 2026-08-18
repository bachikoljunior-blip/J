# Fixed-root run: raw perceptual anchor identity

Selected leaf: `C2.2b2b2b5b2d` — discover and persist cross-environment anchor identity from raw perceptual observations and interventions.

Implemented a bounded raw-image primitive that extracts connected foreground components, tracks components within an environment by appearance continuity, derives intervention-response signatures from displacement and area change, and infers cross-environment identity from response structure rather than cross-environment color/position. Disjoint held-out actions validate the mapping.

Negative controls cover response-signature twins, held-out intervention drift, and segmentation topology changes. Focused suite: 4/4 passed. Full candidate regression suite: 126/126 passed.

Result: `solved_v0_1` only for the bounded assumptions (near-black background, separated components, stable within-environment appearance, already-aligned discrete actions). General vision, occlusion, viewpoint invariance, learned segmentation, texture-rich scenes, and continuous actions remain unresolved.

Root certification remains `NOT_AGI`.
