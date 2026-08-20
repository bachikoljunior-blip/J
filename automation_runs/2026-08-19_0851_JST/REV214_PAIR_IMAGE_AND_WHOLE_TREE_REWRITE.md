# rev214 general pair-image closure and mandatory whole-tree rewrite

## Strict status

Only the J repository AGI-GI rev series is counted.  This revision composes an
exact String-Isomorphism subroutine; it is not an AGI implementation and does not
establish generality, performance, autonomy, or usable delivery.  Root status is
**NOT_AGI**.

## Direct attempt and observed decomposition

The selected leaf was reproduced on the full induced `S_9` action on `J(9,3)`.
The colored triples are the nine cyclic translates of `{0,1,3}` and the target is
a nonidentity ground relabeling.  Ground size 9 exceeds the existing explicit cap
8.  Every point has the same star histogram, the one-cell profile does not
determine the colored triple relation, and rev177 therefore returns
`undetermined_signed_ground_profile_no_split`.

rev184 canonically reaches arity path `(2,)` and a nonconstant homogeneous pair
relation, but stopped only because that pair relation is not itself a Johnson
scheme.  The already implemented rev211 machinery does not need that extra
structural label: the actual pair string has degree `C(9,2)=36 < C(9,3)=84`, its
induced action is exact, its SI coset can be lifted by paired Schreier preimage,
and the full triple string can be solved inside the proper filter.

The direct bridge closes in about 46 seconds locally.  The real top-level v7
dispatcher closes in about 133 seconds, returns target-stabilizer order 9,
contains the known nonidentity transporter, and validates under recurrence v4.
These are observations for this regression, not a general performance claim.

The broader parent remains unresolved and materializes five residual children:

1. `k<=2`, where no strictly lower pair image exists;
2. a completely homogeneous pair relation requiring a stronger Design/local
   certificate;
3. an exact but nonrestricting pair preimage, which must not recurse on itself;
4. exact pair-image intersection or recognition resource exhaustion; and
5. duplicated Johnson lift/descent work across current dispatch layers.

## Mandatory over-count traversal and rewrite

The persisted forecast/effective count was 512/512.  Replacing one leaf by the
solved subcase plus five real residual children transiently materializes 517
non-obsolete problems.  This exceeds the forecast; the full-tree rewrite trigger
therefore fires *before* these children are hidden or consolidated.

The traversal covers every non-obsolete AGI-GI stratum: primitive Johnson
relation leaves; H6-C2 candidate closure; W1R-H6 corrected Split-or-Johnson and
Design branch union; global proof-carrying recurrence/resource control; and the
AGI root's separate generality, performance, autonomy, and usable-delivery proof
obligations.  The following solution-shaped problems replace seven narrower
relation/filter/cap branches without declaring them solved:

- **CRX1 exact canonical relation quotient/preimage closure.**  Treat profile
  partitions, arbitrary informative lower-arity relations, second-Johnson pair
  relations, imprimitive quotients, and Design witness relations as the same
  exact action-image SI plus paired preimage/full-string intersection problem.
- **CRX2 information/symmetry-defect relation selection.**  Choose arity by
  strict degree shrink and measured color-stabilizer/symmetry defect, not by a
  privileged Johnson label; homogeneous outputs escalate to canonical
  local-certificate/Design machinery.
- **CRX3 replay-stable proof and resource substrate.**  Persist certified lifts,
  relation descents, target-side coset orientation, progress measures, and work
  charges across dispatchers; reject nonrestricting self-loops and caps
  fail-closed.  This attacks both correctness and the unusual systems-level
  performance problem of recomputing the same structural proof.

The rewrite removes the separate active branches for significant-profile
restricted candidates, profile no-split, generic higher-order relation,
second-Johnson pair image, bounded imprimitive quotient, partition/recognition
cap, and nonclosing restricted candidate.  CRX1--CRX3 replace those seven nodes,
so the post-rewrite effective count is 513 (`517 - 7 + 3`).  The new forecast is
**576**, not 512, leaving explicit room for future observed decompositions rather
than suppressing them to avoid another trigger.

rev214 implements the CRX1 nonconstant strict-pair subcase and two CRX3 guards:
homogeneous pair images fail closed, and a preimage equal to the ambient group is
allowed only to pass the whole-candidate exact terminal; otherwise it is rejected
as a same-domain self-loop.

## Existing-world solution containment

Babai's primary quasipolynomial GI/SI result places String Isomorphism and Coset
Intersection in one Luks-style group-action framework and uses canonical local
certificates, Design Lemma reduction, and Johnson structures rather than treating
every structural label as a separate solver:
https://arxiv.org/abs/1512.03547

Babai's tutorial states the cross-layer pattern directly: aggregate canonical
`O(log n)`-ary local certificates, reduce them to binary structure by the Design
Lemma, then return a divided domain to Luks recursion:
https://www.iti.zcu.cz/wl2018/pdf/wl2018_babai_tutorial2.pdf

rev214 contains only the mechanically certified strict pair-image instance of
that pattern.  It does not claim the general local-certificate theorem is fully
implemented.

## Remaining boundaries

CRX1 remains open for `k<=2`, homogeneous/nonrestricting relation images, and
node-capped image SI.  CRX2 and CRX3 remain open beyond the existing gates,
especially replay/memoization with proof identity.  W1R-H6, corrected global
Split-or-Johnson recurrence, independent empirical AGI criteria, and practical
AGI delivery remain unresolved.
