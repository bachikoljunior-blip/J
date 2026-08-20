from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import log2

from candidate_full_accept_terminal_v1 import exact_if_entire_candidate_maps_string
from coset_stabilizer_primitives import RightCoset
from paired_action_coset_preimage_v1 import (
    PairedActionCosetPreimage,
    paired_action_coset_preimage,
)
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v4 import validate_quasipoly_recurrence_tree_v4


@dataclass(frozen=True)
class PairedActionFullCandidateArtifact:
    """Immutable proof of an image-coset preimage and its full-string child."""

    status: str
    domain_degree: int
    image_degree: int
    root_n: int
    image_generators: tuple[tuple[int, ...], ...]
    image_coset: RightCoset
    source_identity: tuple[object, ...]
    target_identity: tuple[object, ...]
    candidate_parameter_identity: tuple[tuple[str, object], ...]
    preimage: PairedActionCosetPreimage
    candidate: ProofCarryingCoset | None
    nonrestricting: bool
    recurrence_status: str
    preimage_log2_cost_bound: float
    reason: str


@lru_cache(maxsize=128)
def _memoized_paired_action_preimage(group, image_generators, image_coset):
    return paired_action_coset_preimage(group, image_generators, image_coset)


def _build_paired_action_preimage_uncached(group, image_generators, image_coset):
    return paired_action_coset_preimage(group, image_generators, image_coset)


def build_paired_action_preimage_artifact(group, image_generators, image_coset):
    """Replay-stable exact preimage; unhashable inputs change reuse only."""
    images = tuple(tuple(q) for q in image_generators)
    identity = (group, images, image_coset)
    try:
        hash(identity)
    except TypeError:
        return _build_paired_action_preimage_uncached(*identity)
    return _memoized_paired_action_preimage(*identity)


build_paired_action_preimage_artifact.cache_clear = _memoized_paired_action_preimage.cache_clear
build_paired_action_preimage_artifact.cache_info = _memoized_paired_action_preimage.cache_info


def _normalize_candidate_parameters(candidate_parameters):
    if isinstance(candidate_parameters, dict):
        items = tuple(candidate_parameters.items())
    else:
        items = tuple(candidate_parameters)
    normalized = tuple(sorted(((str(k), v) for k, v in items), key=lambda item: item[0]))
    names = tuple(k for k, _ in normalized)
    if len(set(names)) != len(names):
        raise ValueError("candidate parameter names must be unique")
    if "root_n" in names:
        raise ValueError("root_n is a separate proof-identity field")
    return normalized


def _freeze_identity_value(value):
    """Snapshot ordinary mutable values without making them cache-eligible."""
    if isinstance(value, tuple):
        return ("tuple", tuple(_freeze_identity_value(x) for x in value))
    if isinstance(value, list):
        return ("list", tuple(_freeze_identity_value(x) for x in value))
    if isinstance(value, dict):
        items = (
            (_freeze_identity_value(k), _freeze_identity_value(v))
            for k, v in value.items()
        )
        return ("dict", tuple(sorted(items, key=repr)))
    if isinstance(value, (set, frozenset)):
        return (
            "set",
            tuple(sorted((_freeze_identity_value(x) for x in value), key=repr)),
        )
    if value is None or isinstance(value, (bool, int, float, str, bytes)):
        return ("atom", value)
    try:
        hash(value)
        kind = "hashable-object"
    except TypeError:
        kind = "opaque"
    return (
        kind,
        type(value).__module__,
        type(value).__qualname__,
        repr(value),
    )


def _build_paired_action_full_candidate_artifact_uncached(
    group,
    image_generators,
    image_coset,
    source,
    target,
    root_n,
    candidate_dispatch,
    candidate_parameters,
):
    preimage = build_paired_action_preimage_artifact(
        group, image_generators, image_coset
    )
    preimage_bound = (
        log2(
            max(
                1,
                preimage.sift_levels
                + preimage.kernel_order.bit_length()
                + preimage.image_order.bit_length(),
            )
        )
        + 32.0 * log2(max(2, root_n))
        + 32.0
    )
    source_identity = tuple(_freeze_identity_value(x) for x in source)
    target_identity = tuple(_freeze_identity_value(x) for x in target)
    parameter_identity = tuple(
        (name, _freeze_identity_value(value))
        for name, value in candidate_parameters
    )

    def artifact(
        status,
        *,
        candidate=None,
        nonrestricting=False,
        recurrence_status="not_checked",
        reason,
    ):
        return PairedActionFullCandidateArtifact(
            status,
            int(group.degree),
            int(preimage.image_degree),
            root_n,
            image_generators,
            image_coset,
            source_identity,
            target_identity,
            parameter_identity,
            preimage,
            candidate,
            bool(nonrestricting),
            recurrence_status,
            preimage_bound,
            reason,
        )

    if preimage.status != "exact_paired_action_coset_preimage" or preimage.coset is None:
        return artifact(
            "undetermined_paired_action_preimage_" + preimage.status,
            reason=(
                "the image right coset did not yield a certified complete original-domain preimage: "
                + preimage.reason
            ),
        )

    nonrestricting = (
        preimage.coset.subgroup.order == group.order
        and group.contains(preimage.coset.representative)
    )
    if nonrestricting:
        candidate = exact_if_entire_candidate_maps_string(
            preimage.coset,
            source,
            target,
            root_n=root_n,
        )
        if not candidate.exact:
            return artifact(
                "undetermined_paired_action_nonrestricting_candidate",
                candidate=candidate,
                nonrestricting=True,
                reason=(
                    "the exact preimage equals the ambient subgroup and the whole-candidate terminal did not close the full string; refusing a same-domain recursion loop"
                ),
            )
    else:
        candidate = candidate_dispatch(
            preimage.coset,
            source,
            target,
            root_n=root_n,
            **dict(candidate_parameters),
        )
        if not candidate.exact:
            return artifact(
                "undetermined_paired_action_full_candidate_" + candidate.status,
                candidate=candidate,
                reason=(
                    "the complete paired-action preimage is proper, but its full-string candidate child remains unresolved: "
                    + candidate.reason
                ),
            )

    recurrence = validate_quasipoly_recurrence_tree_v4(candidate.accounting)
    if not recurrence.certified:
        return artifact(
            "undetermined_paired_action_candidate_accounting_" + recurrence.status,
            candidate=candidate,
            nonrestricting=nonrestricting,
            recurrence_status=recurrence.status,
            reason=(
                "the full-string child is exact but its recurrence certificate failed replay: "
                + recurrence.reason
            ),
        )
    return artifact(
        "exact_paired_action_full_candidate",
        candidate=candidate,
        nonrestricting=nonrestricting,
        recurrence_status=recurrence.status,
        reason=(
            "paired Schreier lifting reconstructed the complete original-domain image-coset preimage; the full string was solved inside a proper filter or by the whole-ambient-candidate terminal, and recurrence accounting replay succeeded"
        ),
    )


@lru_cache(maxsize=64)
def _memoized_paired_action_full_candidate_artifact(
    group,
    image_generators,
    image_coset,
    source,
    target,
    root_n,
    candidate_dispatch,
    candidate_parameters,
):
    return _build_paired_action_full_candidate_artifact_uncached(
        group,
        image_generators,
        image_coset,
        source,
        target,
        root_n,
        candidate_dispatch,
        candidate_parameters,
    )


def build_paired_action_full_candidate_artifact(
    group,
    image_generators,
    image_coset,
    source_values,
    target_values,
    *,
    root_n: int,
    candidate_dispatch,
    candidate_parameters=(),
):
    """Return one proof identity for paired preimage, loop guard and full SI.

    The identity includes the complete frozen domain group, generator pairing,
    oriented image right coset, full source/target strings, dispatcher identity,
    recurrence root and every dispatcher resource gate.  A bounded cache may
    reuse that proof object, but unhashable inputs bypass it and all unresolved
    results remain unresolved.
    """
    if isinstance(root_n, bool) or not isinstance(root_n, int):
        raise TypeError("root_n must be an integer")
    if root_n < int(group.degree):
        raise ValueError("root_n must dominate the full candidate domain")
    if not callable(candidate_dispatch):
        raise TypeError("candidate_dispatch must be callable")
    images = tuple(tuple(q) for q in image_generators)
    source = tuple(source_values)
    target = tuple(target_values)
    if len(source) != int(group.degree) or len(target) != int(group.degree):
        raise ValueError("full string/group degree mismatch")
    parameters = _normalize_candidate_parameters(candidate_parameters)
    identity = (
        group,
        images,
        image_coset,
        source,
        target,
        root_n,
        candidate_dispatch,
        parameters,
    )
    try:
        hash(identity)
    except TypeError:
        return _build_paired_action_full_candidate_artifact_uncached(*identity)
    return _memoized_paired_action_full_candidate_artifact(*identity)


build_paired_action_full_candidate_artifact.cache_clear = (
    _memoized_paired_action_full_candidate_artifact.cache_clear
)
build_paired_action_full_candidate_artifact.cache_info = (
    _memoized_paired_action_full_candidate_artifact.cache_info
)


__all__ = [
    "PairedActionFullCandidateArtifact",
    "build_paired_action_preimage_artifact",
    "build_paired_action_full_candidate_artifact",
]
