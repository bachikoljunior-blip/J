# AGI-GI rev282 — quotient relation/action invariance certificate

## Scope

Rev282 adds one standalone structural certificate under `CRX1/homogeneous-block-reduction/quotient-relation-action-invariance-certificate`. It is the collision-free rescope of the same implementation first validated on the superseded rev281 draft. It consumes only the already main-integrated rev274 group/block-action equivariance certificate and caller-supplied named unary/binary relations on the quotient block domain.

It does **not** discover a block system, choose a canonical homogeneous relation, solve quotient or original-domain String Isomorphism, lift quotient cosets, factor the block-action kernel, or alter any production dispatcher. Those are separate active or historical scopes. AGI state remains **NOT_AGI**.

## Exact contract

`certify_quotient_relation_action_invariance` first replays the rev274 `BlockActionProvenance`. It then normalizes the supplied source/target relation families and requires:

1. a non-vacuous named unary and/or binary quotient relation family;
2. identical source/target names within each arity;
3. all quotient points and ordered pairs to lie in the exact rev274 block domain;
4. every source relation to be invariant under every exact source quotient generator;
5. every target relation to be invariant under every exact target quotient generator; and
6. the rev274-certified block bijection to transport every named source relation exactly to its target relation.

Only if all six checks succeed is an immutable `exact_quotient_relation_action_invariance` certificate emitted. Its digest binds the complete normalized quotient relation data, the exact quotient generators, the block bijection, and the upstream rev274 certificate digest. Replay recomputes both the upstream rev274 proof and this certificate and rejects any digest or payload drift.

The certificate proves a structural quotient-level fact only. It deliberately carries no String-Isomorphism right-coset or AGI achievement claim.

## Fail-closed boundary

Malformed mappings, duplicate/out-of-range points or pairs, source/target name mismatch, non-invariance under either quotient action, relation transport mismatch, a malformed/tampered rev274 certificate, or rev282 digest drift all remain typed fail-closed results. Empty individual relations are allowed because the empty relation is a genuine invariant; an entirely empty relation vocabulary is rejected to avoid a vacuous certificate.

## Parallel isolation and rescope

The implementation adds only four rev282-reserved problem-state files. It does not modify rev275 through rev281 sibling paths, rev273/rev274 shared code, W1R-H6 sibling work, CRX2, CRX3, `MAIN.md`, sibling claims, sibling workflows, or open sibling PRs.

The previous rev281 draft was closed unmerged after a later independent execution also selected target revision 281. This session did not modify that sibling; it marked only its own earlier claim as superseded and selected verified-free rev282. The generic implementation module was never merged from rev281, so this branch contains the sole live proposed copy.

At rescope time the repository-wide canonical admission checker remained fail-closed because the fresh rev275 sibling claim is noncanonical. Rev282 does not repair or rewrite that sibling record. The exact `attempt_solution` evidence path is reserved in the rev282 claim, but no admitted evidence is fabricated while the canonical generator cannot load the registry. The draft PR therefore remains non-mergeable by this session until that shared blocker clears and canonical evidence can be generated.

## Regression boundary

The dedicated smoke runs the rev282 suite plus the inherited rev274 certificate suite. Rev282 regressions cover exact nonidentity block-bijection transport, deterministic relation ordering/digests, unary and binary name mismatch, exact transport mismatch, unary and binary group-invariance rejection, range validation, non-vacuity, upstream rev274 tamper rejection, rev282 digest tamper rejection, and replay against the wrong block action.
