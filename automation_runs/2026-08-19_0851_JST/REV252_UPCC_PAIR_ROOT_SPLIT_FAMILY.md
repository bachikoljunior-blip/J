# AGI-GI rev252 — complete ordered two-root UPCC split family

Run identity: `codex/session-20260821-124648z`  
Durable claim: `agi/run-history/active/chatgpt-session-j-rev252-20260821T221325JST-3fda2080.json`  
Dedicated branch: `codex/agi-gi-rev252-upcc-pair-root-20260821-124648z`

## Scope and strict status

This revision advances one strict structural subcase of the unresolved corrected
Split-or-Johnson remainder. It does **not** prove the general corrected theorem,
pair source and target branches, solve downstream String Isomorphism children,
close the W1R-H6 parent, or establish AGI. The strict state remains `NOT_AGI`.

The new code is an in-place refinement below the existing UPCC residual. It does
not add an independent top-level root problem and it does not edit `MAIN.md` while
other sessions own the current shared integration line.

## Selected residual

`upcc_subconstituent_split_family_v1.py` already retains every one-root
subconstituent partition exposed by an exact full-ground uniprimitive coherent
configuration. That is complete and equivariant, but it can remain nonshrinking
because a one-root constituent cell may exceed the configured constant fraction.

rev252 takes the next finite individualization level without choosing a
label-dependent witness: it retains **every ordered injective pair** `(a,b)` of
roots. The order is intentional because the exact correlated-replacement k-WL
certificate records the two individualization positions separately. Under a
relation isomorphism `g`, the branch `(a,b)` maps to `(g(a),g(b))`; therefore the
complete family is equivariant as a set even though no individual branch is
canonically selected.

## Mechanical certificate

`upcc_pair_root_split_family_v1.py` accepts structural auxiliary shrink only after
checking all of the following:

1. the unindividualized exact k-WL/Design outcome is a full-ground
   `certified_twl_upcc`;
2. the complete ordered-pair inventory has exactly `v(v-1)` branches and fits the
   explicit branch cap;
3. an input-independent upper bound for the base run plus every pair-root run fits
   the caller-supplied total-work cap before the first k-WL execution;
4. every branch reaches an exact outcome rather than a tuple, round, or work cap;
5. every exact branch is either a canonical alpha-bounded point coloring or a
   canonical alpha-bounded imprimitive partition;
6. every returned partition is a nonempty disjoint cover of the whole ground and
   its largest cell is both strictly smaller than `v` and at most `alpha*v`;
7. the executed k-WL work never exceeds the admitted static upper bound.

The branch count satisfies

```text
v(v-1) <= root_n^2,
log2(branch_count) <= 2 log2(root_n).
```

This is only a structural branch frontier. The certificate deliberately contains
no exact parent coset and no recurrence terminal.

## Concrete residual closed

For the binary relation of the `4 x 4` rook graph (`v=16`) at `alpha=1/2`:

- the existing complete one-root family has cell sizes `(1,6,9)` and therefore
  fails the half-shrink gate because `9 > 8`;
- rev252 checks all `16*15 = 240` ordered two-root branches;
- 144 branches have size profile `(1,1,2,4,4,4)`;
- 96 branches have size profile `(1,1,2,3,3,6)`;
- the largest child size is therefore `6 <= 8`.

The regression verifies branch-by-branch relabeling transport on the `3 x 3` rook
relation, not merely equality of aggregate profile multisets.

## Fail-closed boundaries

The whole family is withheld when the base relation is not an exact full-ground
UPCC, the complete branch inventory is capped, the total static work admission
fails, any exact k-WL branch hits a resource boundary, or even one ordered pair
remains clique/UPCC/nonshrinking. No sampled subset of pairs is accepted as a
complete family.

## Focused verification

```text
python -m pytest -q test_upcc_pair_root_split_family_rev252.py
python -m py_compile upcc_pair_root_split_family_v1.py \
  test_upcc_pair_root_split_family_rev252.py
```

The focused suite contains five regressions: the rook-16 one-root residual,
branchwise relabeling equivariance, rank-two clique rejection, pre-execution total
work rejection, and complete-cover branch-cap rejection.

## Hourly continuation

`.github/workflows/j-rev252-session-hourly-refire.yml` is a session-specific
hourly watchdog at `46 * * * *`. It observes only this claim, branch, and PR
activity and emits a deduplicated durable continuation issue after 55 minutes of
inactivity. It never cancels, reruns, or mutates sibling workflows, branches, PRs,
or claims. The existing repository-wide watchdog remains independent.

## Remaining parent boundary

The next parent work must pair the complete source and target two-root families by
exact branch invariants, lift surviving ordered-root transport through the ambient
action, solve every smaller full-string SI child, and attach proof-carrying
multiplicity/progress accounting. Pair-root failures still require the Johnson or
general corrected Split-or-Johnson alternatives. Global W1R-H6 recurrence closure
and AGI remain unresolved.
