from __future__ import annotations

from dataclasses import dataclass


def _require_positive_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _require_nonnegative_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def _require_bool(name: str, value: bool) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")
    return value


def _sat_add(left: int, right: int, stop: int) -> int:
    """Return min(left + right, stop) without constructing an oversized integer."""
    if left >= stop or right >= stop or left > stop - right:
        return stop
    return left + right


def _sat_mul(left: int, right: int, stop: int) -> int:
    """Return min(left * right, stop) without constructing an oversized integer."""
    if left == 0 or right == 0:
        return 0
    if left >= stop or right >= stop or left > (stop - 1) // right:
        return stop
    return left * right


def _sat_pow(base: int, exponent: int, stop: int) -> int:
    """Return min(base**exponent, stop) by exponentiation with saturation."""
    result = 1
    factor = base
    power = exponent
    while power:
        if power & 1:
            result = _sat_mul(result, factor, stop)
            if result >= stop:
                return stop
        power >>= 1
        if power:
            factor = _sat_mul(factor, factor, stop)
    return result


def recursive_coset_intersection_node_upper_bound(
    degree: int,
    left_coset_order: int,
    right_coset_order: int,
    *,
    stop: int | None = None,
) -> int:
    """Bound every ``_Budget.tick`` in ``right_coset_intersection_recursive``.

    Let ``s = min(|H|, |K|)`` for the two input right-coset subgroups and let
    ``n`` be their common degree.  The implementation's witness search refines
    disjoint point-image fibers.  A root-to-leaf path fixes a new domain image at
    every recursive call, so its depth is at most ``n``; the leaves inject into
    both input cosets, so there are at most ``s`` leaves.  Hence one witness
    search uses at most ``n*s + 1`` ticks.

    The subgroup-intersection recursion fixes a new common point at every level,
    so it has at most ``n`` levels.  At one level, the sum over common orbit
    images of the smaller transporter-stabilizer order is at most ``s``.  All
    transporter witness searches at that level therefore use at most ``n*s+n``
    ticks.  Adding the initial witness search and the subgroup-recursion ticks is
    dominated by

        (n + 1)^2 (s + 1).

    This is deliberately loose, but it is finite, replay-stable, and independent
    of search luck.  Supplying ``stop=cap+1`` gives cap+1 saturation for admission
    checks without materializing huge integers.
    """
    n = _require_positive_int("degree", degree)
    left = _require_positive_int("left_coset_order", left_coset_order)
    right = _require_positive_int("right_coset_order", right_coset_order)
    if stop is not None:
        stop = _require_positive_int("stop", stop)
        square = _sat_mul(n + 1, n + 1, stop)
        return _sat_mul(square, min(left, right) + 1, stop)
    return (n + 1) * (n + 1) * (min(left, right) + 1)


@dataclass(frozen=True)
class CRX1ImageSIRequest:
    """One exact recursive image-coset intersection requested by a CRX1 caller."""

    image_degree: int
    left_coset_order: int
    right_coset_order: int
    setup_work_upper_bound: int
    per_node_work_upper_bound: int
    strict_image_progress_certified: bool
    restricting_preimage_certified: bool
    whole_candidate_terminal_certified: bool = False
    left_order_certified: bool = True
    right_order_certified: bool = True




def johnson_relation_image_resource_request(
    *,
    parent_degree: int,
    auxiliary_degree: int,
    subset_size: int,
    relation_arity: int,
    image_degree: int,
    image_group_order: int,
    value_coset_order: int,
    strict_image_progress_certified: bool,
    restricting_preimage_certified: bool,
    relation_determines_string: bool = False,
    image_group_order_certified: bool = True,
    value_coset_order_certified: bool = True,
) -> CRX1ImageSIRequest:
    """Build the request matching the existing signed-Johnson image-SI charge.

    ``signed_johnson_complement_safe_relation_image_si`` currently charges

      setup = 2*d*m*(t+1)*k
      per recursive node = max(2, d+m+v)^6,

    where ``m`` is the parent degree, ``v`` the certified ground/auxiliary degree,
    ``k`` the Johnson subset size, ``t`` the relation arity, and ``d`` the image
    degree.  This helper freezes exactly that execution identity for preflight.
    """
    parent = _require_positive_int("parent_degree", parent_degree)
    auxiliary = _require_positive_int("auxiliary_degree", auxiliary_degree)
    subset = _require_positive_int("subset_size", subset_size)
    arity = _require_positive_int("relation_arity", relation_arity)
    image = _require_positive_int("image_degree", image_degree)
    left = _require_positive_int("image_group_order", image_group_order)
    right = _require_positive_int("value_coset_order", value_coset_order)
    if not (arity <= subset < auxiliary):
        raise ValueError("Johnson relation parameters must satisfy arity <= subset_size < auxiliary_degree")
    setup = max(1, 2 * image * parent * (arity + 1) * subset)
    per_node = max(2, image + parent + auxiliary) ** 6
    return CRX1ImageSIRequest(
        image,
        left,
        right,
        setup,
        per_node,
        _require_bool("strict_image_progress_certified", strict_image_progress_certified),
        _require_bool("restricting_preimage_certified", restricting_preimage_certified),
        _require_bool("relation_determines_string", relation_determines_string),
        _require_bool("image_group_order_certified", image_group_order_certified),
        _require_bool("value_coset_order_certified", value_coset_order_certified),
    )


def _normalized_request(raw: CRX1ImageSIRequest) -> CRX1ImageSIRequest:
    if not isinstance(raw, CRX1ImageSIRequest):
        raise TypeError("requests must contain CRX1ImageSIRequest values")
    image_degree = _require_positive_int("image_degree", raw.image_degree)
    left = _require_positive_int("left_coset_order", raw.left_coset_order)
    right = _require_positive_int("right_coset_order", raw.right_coset_order)
    setup = _require_nonnegative_int("setup_work_upper_bound", raw.setup_work_upper_bound)
    per_node = _require_positive_int("per_node_work_upper_bound", raw.per_node_work_upper_bound)
    return CRX1ImageSIRequest(
        image_degree,
        left,
        right,
        setup,
        per_node,
        _require_bool("strict_image_progress_certified", raw.strict_image_progress_certified),
        _require_bool("restricting_preimage_certified", raw.restricting_preimage_certified),
        _require_bool("whole_candidate_terminal_certified", raw.whole_candidate_terminal_certified),
        _require_bool("left_order_certified", raw.left_order_certified),
        _require_bool("right_order_certified", raw.right_order_certified),
    )




__all__ = [
    "CRX1ImageSIRequest",
    "johnson_relation_image_resource_request",
    "recursive_coset_intersection_node_upper_bound",
]
