# AGI-GI rev243 — Design nested primitive Johnson resource preflight

## Strict scope

This revision addresses only `CRX2/c2b2a2iii`: the resource boundary reached when an earlier intransitive child changes the current subgroup and a later initial-orbit image may be transitive primitive non-giant. The work is isolated on PR #174 and does not modify the rev242 shared Design pipeline-ledger branches or the separately claimed rev244 transitive-imprimitive sibling.

The root state remains **NOT_AGI**. This is one proof/resource child of the String Isomorphism implementation tree; it is not evidence for the independent AGI generality, performance, autonomy, or delivery requirements.

## Existing implementation reused

No second Johnson solver was added. The preflight is derived from the executable path already present in the repository:

- rev175: exact Johnson coordinate recognition, bounded exact-orbital fallback, generator decode and exact re-induction;
- rev177: complement-safe star/anti-star profiles, profile tables, signed partition transport, parity kernel and original-domain cosets;
- rev212: the shared primitive-non-giant candidate and S1 boundaries that invoke that profile path;
- rev224: caller-capped saturating arithmetic and conservative raw Schreier-chain bounds;
- rev238: the rule that an unknown-post-child structural path receives a standalone input-independent resource envelope without falsely certifying the path itself.

The missing contract was a single caller-derived budget available **before** the exact later subgroup exists. The runtime guards `max_recognition_nodes` and `max_partition_states` bounded individual operations, but they did not reserve recognition, profile construction, partition transport, original-domain Schreier work, and paired lift as one pre-execution envelope.

## Resource contract

`design_nested_primitive_johnson_resource_envelope` accepts only data available before the later child starts: original-root/current/image degrees, parent/image order upper bounds, a generator upper bound, the existing recognition and partition caps, and one arbitrary-precision `max_work`.

It then reserves, with `cap + 1` saturation:

1. the complete exact family of feasible parameters `C(v,k)=m`, `2<=k<=v/2`;
2. every possible canonical pair-color/Johnson comparison;
3. every comparison in the bounded exact-unordered-orbital fallback when that fallback is enabled;
4. the exact-GI node budget, Johnson graph construction, and target-automorphism Schreier reconstruction;
5. generator decode/re-induction, complement-safe source/target signatures, and profile tables;
6. the complete bounded signed partition-orbit attempt and its action transitions;
7. stabilizer, parity-kernel, target-conjugate, and parity-mode original-domain Schreier chains;
8. the later image, paired-action, kernel, lift-sift, and full-domain preimage chains back to the current full-string domain.

A bound is rejected before recognition starts when the original-root lift is invalid, no Johnson parameter exists, strict ground progress is unavailable, the supplied image-order bound is too loose for every feasible signed Johnson action, or the aggregate work exceeds the caller cap.

## Exact claim boundary

`resource_admitted=True` certifies only that the whole bounded attempt fits the finite budget. `exact_path_certified` is deliberately and permanently false in this revision.

In particular, rev243 does **not** assert that the unknown post-child subgroup will be primitive, Johnson, profile-determined, nonempty, or exactly solvable. Those facts remain checked by the existing classifier, Johnson recognizer, generator round-trip, profile solver, and proof-carrying S1/U2 return values. A partition-state or recognition cap may still produce a typed unresolved result; the preflight merely proves that even that fail-closed attempt was reserved before execution.

Accordingly the old leaf is refined into:

- `c2b2a2iii1`: unknown-post-child nested primitive-Johnson resource envelope — implemented by rev243;
- `c2b2a2iii2`: production complete-cover admission/path integration and execution-linked charge — still unresolved.

Replacing one leaf by its parent and two explicit children changes the effective count from 564 to 566. This remains below the persisted forecast 576, so the mandatory over-count rewrite trigger does not fire and the unresolved integration child is not suppressed.

## Regression evidence

The focused regression suite covers:

- the exact `J(5,2)` parameter family and canonical-plus-fallback comparison multiplicity;
- the signed-complement `J(6,3)` action bound `2*6!`;
- omission of the exact-orbital fallback above its explicit degree cap;
- exact arbitrary-precision `cap + 1` saturation;
- non-Johnson image degrees failing closed without a path claim;
- original-root, parent-order, image-order, and signed-Johnson-order guards.

Local execution completed all six focused tests and `py_compile`. The dedicated GitHub workflow also reruns the inherited rev238 nested-resource contract so the shared saturation/Schreier assumptions remain covered on the exact proposed head.

## Parallel and recovery contract

The active claim files and PR #174 are the durable ownership marker. Parallel workers must leave this branch untouched while the marker is fresh and may continue adjacent leaves. The hourly non-interrupting continuation watchdog on `main` leaves queued/running workflows and recently updated AGI-GI claims/PRs alone; only an idle/stale repository state emits a durable continuation re-fire request.
