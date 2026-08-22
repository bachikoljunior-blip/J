# AGI-GI rev1900 — Johnson child semantic reduction binding

## Scope

This revision owns only
`w1r-h6/corrected-split-or-johnson/larger-ground-recursive-child-semantic-reduction-binding`.

It sits between the main-integrated rev287 `J(v,k) -> v` relational-reduction
certificate and the separately owned rev1700 recursive child-instance executor.
It imports/replays only the main-integrated rev287 public contract. It does not
import rev1700, rev293, or any other sibling branch-only implementation.

## Constructed child string

For a parent string `x` on the certified Johnson vertices and each canonical
ground point `p`, define the child value

`F(x)[p] = multiset { freeze(x[S]) : p in S }`.

`freeze` is a closed deterministic value encoding. Opaque values and non-finite
floats fail closed instead of receiving process-dependent identities.

Rev287 has already reconstructed the complete canonical point-incidence star
family and checked every ambient generator against its induced ground
permutation. Rev1900 replays that certificate, derives the induced Johnson
vertex permutation from each ground generator again, and mechanically checks

`F(g.x) = g.F(x)`

for both supplied source and target strings.

Consequently every parent transporter represented by the certified ground
action is necessarily a transporter of the constructed child strings. The
child String-Isomorphism result can therefore be used as a *complete candidate
cover* for later exact parent filtering.

## Deliberate one-way boundary

The converse is false in general and is not certified. Incident color
multisets can forget higher-order structure. The regression suite includes the
edge-colored `J(6,2)` example whose red subgraph is a 6-cycle on one side and
two disjoint triangles on the other: every ground point has the same red/blue
incident-color profile, while the identity ground permutation does not
transport the parent string.

Accordingly the binding fixes these fields:

- `parent_to_child_transport_certified = True`;
- `child_to_parent_transport_certified = False`;
- `parent_solution_equivalence_certified = False`.

Rev1900 also exposes an exact per-candidate verifier that lifts one ground
permutation to the certified Johnson vertices and tests the complete original
parent source/target strings. It does not enumerate a child coset and does not
turn the one-way projection into a theorem of parent/child solution equality.

## Replay and accounting boundary

The immutable binding identity includes the rev287 reduction identity, frozen
parent-string digests, exact child values and digests, profile schema, measures,
and a conservative semantic-construction work bound. Replay reruns rev287 from
the original embedding/generators and reconstructs the entire child binding.

## Validation and admission boundary

The first ordinary pull-request head (`39d59b7f4f2fd3f4bbe10c835029f307d752a8bc`)
completed the dedicated rev1900 smoke successfully. It passed Python
compilation, all 9 focused rev1900 regressions, all 11 inherited rev287
relational-reduction regressions, the sibling-implementation dependency gate,
and fresh canonical `attempt_solution` and `publish` previews.

The first evidence-persistence workflow version generated the two new JSON
files correctly but used `git diff --quiet` before staging them; Git does not
report untracked files through that check. The rev1900-owned workflow was fixed
without touching or rerunning any sibling workflow: it now stages exactly the
two reserved evidence paths first and tests `git diff --cached --quiet`.

That ordinary PR-triggered run then committed both canonical records on the
dedicated branch as bot commit
`533d8c9133cc8167781b71696cfd987d35aca561`. Both records are
`event_type=problem_solving_phase_admission`, `mode=exclusive`,
`admitted=true`, and `conflicts=[]`; they bind target revision 1900, this exact
scope/claim, and the four rev1900 problem-state paths. They were mechanically
generated from canonical registry source
`c935438642bba01c3d91ae650850755c9f40d5c3` with registry digest
`sha256:bae9f8ae776e37ddf9a03f4e16cc9e532456f9e7dae0525e10c053ebecde21cf`.
No evidence was copied or fabricated from a sibling.

This connector-authored documentation heartbeat follows the bot evidence commit
so normal pull-request checks evaluate a head that already contains replayable
phase evidence; no workflow is manually rerun.

This revision does not execute recursive String-Isomorphism, lift a child
result, perform full parent-coset filtering, change recurrence/proof-DAG
accounting, close corrected Split-or-Johnson, prove GI, or establish AGI.
State remains `NOT_AGI`.
