from __future__ import annotations

import hashlib
import json
import re
from typing import Optional, Protocol, runtime_checkable

from implicit_relation_image_action_v1 import ImplicitRelationImageAction
from implicit_relation_parent_outcome_v1 import ParentExactOutcomeContract


SOURCE_REVISION = 269
SOURCE_STATUS = "exact_empty_parent_auxiliary_image_obstruction"
EXACT_IMAGE_EMPTY_STATUSES = frozenset(
    {
        "exact_empty_feature_inventory_mismatch",
        "exact_empty_implicit_image_value_coset",
    }
)
EXACT_PREIMAGE_EMPTY_STATUS = "exact_empty_original_domain_relation_coset"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@runtime_checkable
class ExactImageEmptyContract(Protocol):
    status: str
    exact: bool
    complete: bool
    auxiliary_degree: int
    coset: Optional[object]


@runtime_checkable
class ExactOriginalPreimageEmptyContract(Protocol):
    status: str
    exact: bool
    complete: bool
    domain_degree: int
    auxiliary_degree: int
    representative: Optional[object]
    subgroup: Optional[object]
    coset: Optional[object]


def _require_digest(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase sha256:<64 hex> digest")
    return value


def _closed(
    status: str,
    *,
    domain: int,
    source_digest: str,
    target_digest: str,
    reason: str,
) -> ParentExactOutcomeContract:
    return ParentExactOutcomeContract(
        status=status,
        exact=False,
        complete=False,
        outcome_kind="undetermined",
        domain_degree=domain,
        auxiliary_degree=0,
        source_evidence_revision=0,
        source_evidence_status="",
        source_relation_digest=source_digest,
        target_relation_digest=target_digest,
        upstream_artifact_digest="",
        transcript_digest="",
        reason=reason,
    )


def _digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def certify_exact_empty_image_parent_outcome(
    action: ImplicitRelationImageAction,
    image_result: ExactImageEmptyContract,
    preimage_result: ExactOriginalPreimageEmptyContract,
    *,
    source_relation_digest: str,
    target_relation_digest: str,
    image_artifact_digest: str,
    preimage_artifact_digest: str,
) -> ParentExactOutcomeContract:
    """Promote a complete empty faithful auxiliary transporter to parent emptiness.

    The semantic implication is one-way and exact.  Every parent relation
    isomorphism belongs to the supplied original-domain group, hence rev257's
    induced action maps it to an element of the faithful auxiliary image group.
    Because the auxiliary feature string is the complete named unary/binary
    incidence encoding, that image element would lie in rev262's complete
    value-preserving transporter set.  Therefore an exact-empty rev262 image
    transporter excludes every parent relation isomorphism.  Rev267's exact
    empty original-domain preimage is required as an independent consistency
    witness before promotion.

    This boundary intentionally imports neither rev262 nor rev267 branch-only
    implementations; it accepts their exact structural result contracts.
    """
    source_relation_digest = _require_digest(
        source_relation_digest, "source_relation_digest"
    )
    target_relation_digest = _require_digest(
        target_relation_digest, "target_relation_digest"
    )
    image_artifact_digest = _require_digest(
        image_artifact_digest, "image_artifact_digest"
    )
    preimage_artifact_digest = _require_digest(
        preimage_artifact_digest, "preimage_artifact_digest"
    )

    if not isinstance(action, ImplicitRelationImageAction):
        return _closed(
            "fail_closed_rev257_action_type",
            domain=0,
            source_digest=source_relation_digest,
            target_digest=target_relation_digest,
            reason="semantic parent-empty promotion requires the concrete integrated rev257 action artifact",
        )

    domain = action.domain_degree
    auxiliary = action.auxiliary_degree
    if (
        isinstance(domain, bool)
        or not isinstance(domain, int)
        or domain <= 0
        or isinstance(auxiliary, bool)
        or not isinstance(auxiliary, int)
        or auxiliary <= 0
    ):
        return _closed(
            "fail_closed_rev257_action_degree",
            domain=domain if isinstance(domain, int) and not isinstance(domain, bool) else 0,
            source_digest=source_relation_digest,
            target_digest=target_relation_digest,
            reason="rev257 action must bind positive original and auxiliary degrees",
        )

    if (
        action.status != "exact_implicit_relation_image_paired_action"
        or action.domain_group is None
        or action.image_group is None
        or action.kernel is None
    ):
        return _closed(
            "fail_closed_rev257_action_not_exact",
            domain=domain,
            source_digest=source_relation_digest,
            target_digest=target_relation_digest,
            reason="rev257 did not provide its exact paired original/image/kernel action",
        )

    try:
        faithful = (
            action.kernel.order == 1
            and action.image_group.order == action.domain_group.order
            and len(tuple(action.source_features)) == auxiliary
            and len(tuple(action.target_features)) == auxiliary
            and tuple(action.source_features[:domain]) == (("point", False),) * domain
            and tuple(action.target_features[:domain]) == (("point", False),) * domain
        )
    except (AttributeError, TypeError):
        faithful = False
    if not faithful:
        return _closed(
            "fail_closed_rev257_faithful_action_contract",
            domain=domain,
            source_digest=source_relation_digest,
            target_digest=target_relation_digest,
            reason="rev257 action failed the neutral-layer faithful-image invariants required by the semantic implication",
        )

    if not isinstance(image_result, ExactImageEmptyContract):
        return _closed(
            "fail_closed_rev262_image_result_type",
            domain=domain,
            source_digest=source_relation_digest,
            target_digest=target_relation_digest,
            reason="image evidence does not implement the rev262 structural exact-result contract",
        )
    if (
        image_result.status not in EXACT_IMAGE_EMPTY_STATUSES
        or image_result.exact is not True
        or image_result.complete is not True
        or image_result.auxiliary_degree != auxiliary
        or image_result.coset is not None
    ):
        return _closed(
            "fail_closed_rev262_exact_empty_image_contract",
            domain=domain,
            source_digest=source_relation_digest,
            target_digest=target_relation_digest,
            reason="rev262 evidence is not one of the complete exact-empty image transporter outcomes bound to the rev257 auxiliary degree",
        )

    if not isinstance(preimage_result, ExactOriginalPreimageEmptyContract):
        return _closed(
            "fail_closed_rev267_preimage_result_type",
            domain=domain,
            source_digest=source_relation_digest,
            target_digest=target_relation_digest,
            reason="preimage evidence does not implement the rev267 structural exact-result contract",
        )
    if (
        preimage_result.status != EXACT_PREIMAGE_EMPTY_STATUS
        or preimage_result.exact is not True
        or preimage_result.complete is not True
        or preimage_result.domain_degree != domain
        or preimage_result.auxiliary_degree != auxiliary
        or preimage_result.representative is not None
        or preimage_result.subgroup is not None
        or preimage_result.coset is not None
    ):
        return _closed(
            "fail_closed_rev267_exact_empty_preimage_contract",
            domain=domain,
            source_digest=source_relation_digest,
            target_digest=target_relation_digest,
            reason="rev267 evidence did not preserve the same complete exact-empty image transporter as an empty original-domain preimage",
        )

    upstream_digest = _digest(
        {
            "schema": "rev269-upstream-v1",
            "image_artifact_digest": image_artifact_digest,
            "preimage_artifact_digest": preimage_artifact_digest,
            "image_status": image_result.status,
            "preimage_status": preimage_result.status,
            "domain_degree": domain,
            "auxiliary_degree": auxiliary,
            "domain_group_order": action.domain_group.order,
            "image_group_order": action.image_group.order,
            "kernel_order": action.kernel.order,
        }
    )
    transcript_digest = _digest(
        {
            "schema": "rev269-parent-empty-v1",
            "source_evidence_revision": SOURCE_REVISION,
            "source_evidence_status": SOURCE_STATUS,
            "outcome_kind": "exact_empty",
            "domain_degree": domain,
            "auxiliary_degree": auxiliary,
            "source_relation_digest": source_relation_digest,
            "target_relation_digest": target_relation_digest,
            "upstream_artifact_digest": upstream_digest,
        }
    )

    return ParentExactOutcomeContract(
        status="exact_parent_outcome_empty",
        exact=True,
        complete=True,
        outcome_kind="exact_empty",
        domain_degree=domain,
        auxiliary_degree=auxiliary,
        source_evidence_revision=SOURCE_REVISION,
        source_evidence_status=SOURCE_STATUS,
        source_relation_digest=source_relation_digest,
        target_relation_digest=target_relation_digest,
        upstream_artifact_digest=upstream_digest,
        transcript_digest=transcript_digest,
        reason=(
            "rev257 certifies a faithful complete named unary/binary auxiliary action; "
            "rev262 proves its complete value transporter empty and rev267 independently "
            "certifies the corresponding original-domain preimage empty, so no parent "
            "relation isomorphism can exist"
        ),
    )


__all__ = [
    "EXACT_IMAGE_EMPTY_STATUSES",
    "EXACT_PREIMAGE_EMPTY_STATUS",
    "SOURCE_REVISION",
    "SOURCE_STATUS",
    "certify_exact_empty_image_parent_outcome",
]
