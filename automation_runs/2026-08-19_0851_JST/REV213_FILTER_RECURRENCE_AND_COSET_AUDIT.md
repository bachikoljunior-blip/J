# rev213 significant-filter recurrence and right-coset audit

## Strict scope

Only the J repository AGI-GI rev series is progress evidence.  This work repairs
and composes String-Isomorphism machinery; it is not AGI and does not establish
generality, performance, autonomy, or usable AGI delivery.  Root status remains
**NOT_AGI**.

The persisted problem forecast remains **512**, with **512** effective
non-obsolete problems.  The observed count did not exceed the forecast, so the
mandatory full-tree rewrite trigger did not fire.  rev213 replaces the already
persisted `significant signed-ground profile filter / nonclosing restricted
candidate` leaf and its newly observed implementation children in place; it does
not suppress a new child to avoid the trigger.

## Concrete counterexample and decomposition

The selected leaf was reproduced on `J(13,2)` by coloring the six edges of a
ground `C6` red and every other pair uncolored.  rev177 returned
`verified_signed_ground_profile_partition_filter`: the ground split was
significant and exact as a partition transporter, but the relation was not
profile determined.  rev212 then returned `undetermined_johnson_ground_cap`.

The smaller `J(10,2)` form, with a `C5` on one five-point cell, exposed the same
filter with a cheaper exact regression.  Its proof tree decomposed the residual
into three implementation children:

1. a bounded Johnson-ground S1 child that rev173 could already solve exactly but
   S1 v3 never called after profile no-split;
2. a nested intransitive S1 child whose v1 self-recursion discarded the newer
   shared terminals;
3. a transitive imprimitive child with quotient degree inside the explicit and
   polylog auxiliary windows, but whose image order exceeded the unrelated small
   candidate-group cap.

## Existing solutions reused across parents

rev213 adds no generic node-capped search.  It composes existing exact operators:

- rev209 whole-candidate acceptance for identity S1 candidates;
- rev208 literal natural giant SI;
- rev173 bounded-ground Johnson SI;
- rev177 complement-safe signed Johnson profiles;
- canonical orbit preimage composition from S1 v1;
- rev210 candidate block/family SI for transitive imprimitive children; and
- the established explicit T1/polylog auxiliary window for a bounded quotient
  image.  Only when quotient degree is inside both gates may the local cap grow
  to `q!`; all larger quotients remain fail closed.

This is the same Babai/Luks-style shared substrate at the leaf, H6-C2, and W1R-H6
parents: canonical partitions, bounded auxiliary actions, exact coset
image/preimage, and recurrence accounting rather than a parallel solver tree.

## Right-coset orientation repair

The nonidentity regression revealed a pre-existing rev177 completeness bug.
Partition Schreier search naturally produced a **source**-partition stabilizer,
but J's `RightCoset(H, r)` convention requires `H` to act after `r`, hence to be
the **target** stabilizer.  Identity tests hid the error; a nonidentity `J(11,2)`
filter returned an alleged exact subgroup of order 240 instead of the known
`D10 x S6` order 7200.

rev213 conjugates the source stabilizer through the transporter before creating
the filter or exact right coset.  A source-side odd parity witness is composed
before the source-to-target transporter, and exact terminal generators are now
checked against the target relation.  The corrected nonidentity `J(10,2)` case
returns the full known order `10 * 5! = 1200`, contains the known transporter,
and has certified recurrence accounting.

## Remaining boundaries

This attempt does not solve profile `no_split` when the recognized Johnson ground
exceeds the explicit terminal, imprimitive quotients outside the explicit/polylog
window, partition-orbit or recognition caps, corrected Split-or-Johnson residuals,
the W1R-H6 parent, or the AGI root.  Those remain typed unresolved children.

The leaf may be marked integrated only after the exact proposed head passes the
general rev validation, the rev213 smoke, the earlier rev212--rev208 smokes, and
the independent nauty differential gate, then merges to `main`.
