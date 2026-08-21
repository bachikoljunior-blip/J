# CRX1 image-SI resource admission certificate

## Scope

This parallel session owns only `CRX1/node-resource-capped-image-SI/resource-admission-certificate`.
It does not modify the rev248 exact relation-image solver, any CRX2/CRX3 implementation,
`MAIN.md`, an existing workflow, or another active claim.  The implementation is a new,
standalone preflight/audit module that can be consumed after the exact solver branch is
integrated.

## Gap closed by this leaf

The existing signed-Johnson relation-image path invokes
`right_coset_intersection_recursive(..., max_nodes=allowed_nodes)`.  Exhausting that cap
correctly returns `undetermined_node_limit`, but a successful run is still search-luck
dependent unless the caller can prove in advance that the complete recursive search tree
fits the cap.  A node cap alone is not an exactness or complexity certificate.

This leaf supplies that missing reserve-before-execute proof boundary:

1. both input right-coset subgroup orders must be certified;
2. every recursive intersection receives a theorem-derived worst-case node reservation;
3. every relation image must be certified strictly smaller and restricting, unless an
   independent whole-candidate exact terminal closes the same-domain case;
4. the complete cover's node and work envelopes are summed with `cap+1` saturation before
   the first search; and
5. actual exact statuses, search nodes, and work units are checked against the immutable
   reservation after execution.

Rejection executes zero search nodes and remains fail closed.

## Recursive-intersection node theorem

For image degree `n` and input right-coset subgroup orders `h` and `k`, define

```text
s = min(h, k)
B(n, h, k) = (n + 1)^2 (s + 1).
```

`B` bounds every `_Budget.tick()` performed by the current
`right_coset_intersection_recursive` implementation.

### Witness search

Each recursive child fixes one new domain point image.  Sibling children are disjoint
point-image fibers of both input cosets, so all leaves inject into both cosets.  The depth is
at most `n`, the number of leaves is at most `s`, and one witness search uses at most
`n*s + 1` ticks.

### Subgroup intersection

Each subgroup-recursion level fixes a new common point, hence there are at most `n` levels.
At one level, common orbit images `y` have stabilizer orders `h/|Orb_H(p)|` and
`k/|Orb_K(p)|`.  Summing the smaller stabilizer order over the common images is at most
`s`.  Therefore all transporter witness searches at one level use at most `n*s + n` ticks.
Adding the initial witness search, at most `n` subgroup-recursion ticks, and all transporter
searches is dominated by `B`.

The bound is deliberately loose.  Its purpose is to remove search luck: when
`B <= min(max_image_si_nodes, root_degree**image_si_poly_power)`, the admitted call cannot
return `undetermined_node_limit` unless the implementation or counters violate the frozen
execution identity.

## Public contract

`crx1_image_si_resource_admission_v1.py` exports:

- `recursive_coset_intersection_node_upper_bound`: exact or `cap+1`-saturated theorem bound;
- `CRX1ImageSIRequest`: frozen subgroup-order, setup-work, per-node-work, and progress proof
  identity for one image intersection;
- `johnson_relation_image_resource_request`: reproduces the existing signed-Johnson charge
  `2*d*m*(t+1)*k + search_nodes*max(2,d+m+v)^6`;
- `crx1_image_si_resource_admission`: complete-cover preflight; and
- `record_crx1_image_si_execution`: post-execution exact-status and counter audit.

Typed fail-closed statuses distinguish missing order certificates, nonshrinking or
nonrestricting images, per-intersection polynomial-node overflow, complete-cover node
overflow, complete-cover work overflow, and an empty request cover.

## Integration handoff

The exact relation-image branch can consume this module without sharing implementation
paths:

1. construct the certified image chain and value-preserving coset as it already does;
2. build a `johnson_relation_image_resource_request` from their exact orders;
3. run the admission before `right_coset_intersection_recursive`;
4. preserve the current unresolved result on rejection;
5. on admission, pass the returned polynomial gate as `max_nodes`; and
6. record `status`, `search_nodes`, and the existing mechanical `work_units` afterward.

An admitted `undetermined_node_limit` must be treated as an invariant failure, not as a new
structural outcome.

## Verification

Run from `automation_runs/2026-08-19_0851_JST`:

```bash
python -m py_compile \
  crx1_image_si_resource_admission_v1.py \
  test_crx1_image_si_resource_admission_v1.py
python -m unittest -v test_crx1_image_si_resource_admission_v1.py
```

The 15 regressions cover the closed-form theorem and saturation, complete-cover admission,
uncertified orders, same-domain/nonrestricting rejection, whole-candidate terminal escape,
contradictory proof inputs, per-call polynomial overflow, aggregate node overflow, work
saturation, strict boolean proof fields, the signed-Johnson charge identity, execution
counter auditing, omitted cover members, and empty-cover rejection.

## Claim boundary

This closes the resource-admission certificate leaf only.  It does not claim that the rev248
exact witness branch, all CRX1 consumers, the corrected Split-or-Johnson parent, or the AGI
root is solved.  No AGI-GI revision number is allocated by this branch.
