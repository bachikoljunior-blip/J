# rev110 — recursive exact right-coset intersection without relation-orbit enumeration

Root remains **NOT_AGI**.

The rev109 continuation leaf was to control relation-orbit growth beyond explicit image enumeration. The direct implementation now replaces the compressed-relation BFS with two exact recursive operations over stabilizer chains:

1. a point-image right-coset witness search that recursively refines both cosets to a shared image and fails closed on a node limit;
2. exact subgroup intersection reconstruction using orbit-stabilizer recursion. For a selected point, the point stabilizer intersection is solved recursively and each feasible common orbit image is accepted only after an exact transporter-coset witness is found. Verified transporters plus the exact stabilizer generate the full intersection subgroup, with an internal `|G| = |G_p| * |Orb_G(p)|` check.

Independent local execution validation:

- deterministic random explicit-coset oracle: 1,000 degree-1..5 cases, maximum 86 recursive nodes;
- full degree-1..3 distinct-subgroup/right-coset audit: 1,313 cases, maximum 5 recursive nodes;
- additional deterministic degree-1..6 explicit oracle: 300 cases, maximum 37 recursive nodes;
- large non-contained subgroups: point stabilizers of different points in S_n for n=8,10,12,14. Each input subgroup had order `(n-1)!`, the certified intersection order was exactly `(n-2)!`, and each case used 4 recursive nodes. For n=14 this certifies intersection order 479,001,600 while the two input groups each have order 6,227,020,800.

This closes the specific rev109 relation-orbit-enumeration bottleneck at the exact primitive level. It does **not** establish a quasipolynomial worst-case bound for all recursive coset-intersection instances; the broader general-GI ceiling remains open.