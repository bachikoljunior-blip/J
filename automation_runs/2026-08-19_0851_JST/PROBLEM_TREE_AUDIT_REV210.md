# AGI-GI rev210 problem-tree audit

## Parent boundary

rev208 closes a candidate whose represented natural-domain subgroup itself is literal `A_n` or `S_n`. rev209 routes many larger-Johnson primitive-non-giant candidates through existing relation-image/profile substrates. A separate typed giant case nevertheless remains above those leaves: an intransitive parent candidate can have an invariant orbit image that is literally `A_m` or `S_m` even though the full parent group is neither.

Prediction remains **512**, effective non-replaced count remains **512**, and the over-count trigger does not fire.

## Cross-layer solution reuse

The existing U2 intransitive dispatcher already has the correct exact architecture for this case:

1. form the exact image of the current subgroup on one invariant orbit;
2. solve String Isomorphism on that image with S1;
3. lift the returned image coset through the exact orbit-action preimage, thereby restoring the full kernel rather than pretending the image is the parent group;
4. continue with later invariant orbits until all constraints are intersected.

The only missing link was that `s1_string_isomorphism_v2` stopped at the general structural giant path once its small-group enumeration cap was exceeded. rev208 already supplies a stronger terminal for the special image case where the represented image itself is literal `S_m/A_m`: exact color-class transport plus the exact target-color stabilizer/parity intersection.

rev210 therefore does not add another giant solver. It reuses rev208's `exact_literal_giant_string_isomorphism` inside S1 before the general structural dispatcher. This lets the already-existing orbit-image/preimage recursion close direct products and other intransitive parent actions whose orbit image is literal giant, while preserving the parent kernel exactly.

The regression uses `S_7 x S_7` on two 7-point invariant orbits with the small-order cap forced below `|S_7|`. The parent is not a literal giant on 14 points, both orbit images are, and exact sequential preimage recovers the expected `S_6 x S_6` string stabilizer. A direct S7 S1 regression verifies that the new path is actually used above the enumeration cap.

## Branch deletion and remaining boundary

This removes the need to treat **literal giant invariant-orbit images** as instances of the heavier local-certificates branch. It does **not** eliminate the true nonliteral giant-quotient case where a parent action maps onto `A_m/S_m` with nontrivial structure not already represented as a solved invariant-orbit image; that case still requires the existing affected/unaffected/local-certificate/kernel machinery.

After rev210 validation, the remaining W1R-H6 frontier therefore consists of the genuinely nonliteral giant quotient, relation-homogeneous/non-profile-determined primitive/Johnson states, primitive non-giant non-Johnson states, and remaining corrected Split-or-Johnson recursion/accounting. Missing theorem gates and nonexact children remain fail-closed.

AGI remains **NOT_AGI**. No global W1R-H6, quasipolynomial closure, or practical AGI claim is made.
