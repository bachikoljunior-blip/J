from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import isfinite
from typing import Hashable, Iterable

from bipartite_split_or_johnson_gate_v1 import certify_bipartite_split_or_johnson_gate


@dataclass(frozen=True)
class BipartiteTwinQuotientRefinement:
    status: str
    left_size: int
    right_size: int
    source_left_cells: tuple[tuple[int, ...], ...]
    target_left_cells: tuple[tuple[int, ...], ...]
    source_right_cells: tuple[tuple[int, ...], ...]
    target_right_cells: tuple[tuple[int, ...], ...]
    source_left_labels: tuple[int, ...]
    target_left_labels: tuple[int, ...]
    source_right_labels: tuple[int, ...]
    target_right_labels: tuple[int, ...]
    left_cell_pairing: tuple[tuple[int, int], ...]
    right_cell_pairing: tuple[tuple[int, int], ...]
    refinement_rounds: int
    invariant_mismatch: bool
    unique_quotient_mapping: bool
    exact: bool
    complete_for_quotient: bool
    reason: str


def _token(value):
    if value is None:
        return ("none",)
    if isinstance(value, bool):
        return ("bool", int(value))
    if isinstance(value, int) and not isinstance(value, bool):
        return ("int", int(value))
    if isinstance(value, str):
        return ("str", value)
    if isinstance(value, bytes):
        return ("bytes", value.hex())
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("non-finite vertex colors are not canonical")
        return ("float", value.hex())
    if isinstance(value, tuple):
        return ("tuple", tuple(_token(x) for x in value))
    raise ValueError(
        "paired twin-quotient refinement requires canonically serializable colors "
        "(None/bool/int/float/str/bytes/tuple)"
    )


def _normalize_edges(left_size, right_size, edges, normalize_by_complement):
    edge_set = set()
    for a, b in edges:
        a = int(a)
        b = int(b)
        if not 0 <= a < left_size or not 0 <= b < right_size:
            raise ValueError("bipartite edge endpoint outside the declared part")
        edge_set.add((a, b))
    if normalize_by_complement and len(edge_set) > left_size * right_size / 2:
        edge_set = {
            (a, b)
            for a in range(left_size)
            for b in range(right_size)
            if (a, b) not in edge_set
        }
    return edge_set


def _build_quotient(gate, edges, left_colors, right_colors, normalize_by_complement):
    n1, n2 = gate.left_size, gate.right_size
    lp = tuple(0 for _ in range(n1)) if left_colors is None else tuple(left_colors)
    rp = tuple(1 for _ in range(n2)) if right_colors is None else tuple(right_colors)
    if len(lp) != n1 or len(rp) != n2:
        raise ValueError("vertex-color sequence length mismatch")
    edge_set = _normalize_edges(n1, n2, edges, normalize_by_complement)
    lcells = tuple(gate.left_twin_classes)
    rcells = tuple(gate.right_twin_classes)

    lbase = []
    for cell in lcells:
        colors = {_token(lp[x]) for x in cell}
        if len(colors) != 1:
            raise AssertionError("rev199 twin class mixed left colors")
        lbase.append(("L", next(iter(colors)), len(cell)))
    rbase = []
    for cell in rcells:
        colors = {_token(rp[x]) for x in cell}
        if len(colors) != 1:
            raise AssertionError("rev199 twin class mixed right colors")
        rbase.append(("R", next(iter(colors)), len(cell)))

    matrix = []
    for lcell in lcells:
        row = []
        for rcell in rcells:
            bit = (lcell[0], rcell[0]) in edge_set
            for a in lcell:
                for b in rcell:
                    if ((a, b) in edge_set) != bit:
                        raise AssertionError("twin quotient block is not complete or empty")
            row.append(int(bit))
        matrix.append(tuple(row))
    return lcells, rcells, tuple(lbase), tuple(rbase), tuple(matrix)


def _label_universe(values):
    ordered = sorted(set(values), key=repr)
    return {value: i for i, value in enumerate(ordered)}


def _paired_refine(source, target):
    slc, src, slbase, srbase, smat = source
    tlc, trc, tlbase, trbase, tmat = target
    init = _label_universe(slbase + srbase + tlbase + trbase)
    sl = tuple(init[x] for x in slbase)
    sr = tuple(init[x] for x in srbase)
    tl = tuple(init[x] for x in tlbase)
    tr = tuple(init[x] for x in trbase)

    cap = 2 * (len(slc) + len(src) + len(tlc) + len(trc)) + 8
    for round_no in range(1, cap + 1):
        def signatures(left_labels, right_labels, matrix):
            left = []
            for i, label in enumerate(left_labels):
                nbr = Counter((right_labels[j], matrix[i][j]) for j in range(len(right_labels)))
                left.append(("LQ", label, tuple(sorted(nbr.items()))))
            right = []
            for j, label in enumerate(right_labels):
                nbr = Counter((left_labels[i], matrix[i][j]) for i in range(len(left_labels)))
                right.append(("RQ", label, tuple(sorted(nbr.items()))))
            return tuple(left), tuple(right)

        sls, srs = signatures(sl, sr, smat)
        tls, trs = signatures(tl, tr, tmat)
        ids = _label_universe(sls + srs + tls + trs)
        nsl = tuple(ids[x] for x in sls)
        nsr = tuple(ids[x] for x in srs)
        ntl = tuple(ids[x] for x in tls)
        ntr = tuple(ids[x] for x in trs)
        if (nsl, nsr, ntl, ntr) == (sl, sr, tl, tr):
            return nsl, nsr, ntl, ntr, round_no
        sl, sr, tl, tr = nsl, nsr, ntl, ntr
    raise AssertionError("paired twin-quotient refinement failed to stabilize")


def _unique_pairing(source_labels, target_labels):
    if Counter(source_labels) != Counter(target_labels):
        return None
    if len(set(source_labels)) != len(source_labels):
        return ()
    target_by_label = {label: j for j, label in enumerate(target_labels)}
    return tuple((i, target_by_label[label]) for i, label in sorted(enumerate(source_labels), key=lambda x: x[1]))


def refine_bipartite_twin_quotient_pair(
    left_size: int,
    right_size: int,
    source_edges: Iterable[tuple[int, int]],
    target_edges: Iterable[tuple[int, int]],
    *,
    alpha: float = 0.75,
    source_left_colors: Iterable[Hashable] | None = None,
    target_left_colors: Iterable[Hashable] | None = None,
    source_right_colors: Iterable[Hashable] | None = None,
    target_right_colors: Iterable[Hashable] | None = None,
    normalize_by_complement: bool = True,
) -> BipartiteTwinQuotientRefinement:
    """Jointly refine source/target twin quotients with comparable exact labels.

    Rev200 exposes a canonical *partition* but a full isomorphism routine still
    needs source/target-comparable cell information. This function collapses exact
    left/right twin classes to a two-sorted complete/empty quotient and performs
    paired 1-WL-style color refinement, assigning every refinement label from the
    joint source/target signature universe.

    A label-histogram mismatch is an exact non-isomorphism certificate. If every
    final quotient label is unique on each side, the only possible quotient cell
    map is mechanically determined and then checked against every quotient block.
    Ambiguous stable labels remain fail closed: no arbitrary representative is
    promoted to a theorem conclusion.
    """
    source_edges = tuple(source_edges)
    target_edges = tuple(target_edges)
    sg = certify_bipartite_split_or_johnson_gate(
        left_size,
        right_size,
        source_edges,
        alpha=alpha,
        left_colors=source_left_colors,
        right_colors=source_right_colors,
        normalize_by_complement=normalize_by_complement,
    )
    tg = certify_bipartite_split_or_johnson_gate(
        left_size,
        right_size,
        target_edges,
        alpha=alpha,
        left_colors=target_left_colors,
        right_colors=target_right_colors,
        normalize_by_complement=normalize_by_complement,
    )
    source = _build_quotient(
        sg, source_edges, source_left_colors, source_right_colors, normalize_by_complement
    )
    target = _build_quotient(
        tg, target_edges, target_left_colors, target_right_colors, normalize_by_complement
    )
    slc, src, slbase, srbase, smat = source
    tlc, trc, tlbase, trbase, tmat = target
    sl, sr, tl, tr, rounds = _paired_refine(source, target)

    left_mismatch = Counter(sl) != Counter(tl)
    right_mismatch = Counter(sr) != Counter(tr)
    if left_mismatch or right_mismatch:
        return BipartiteTwinQuotientRefinement(
            "exact_twin_quotient_invariant_mismatch",
            int(left_size), int(right_size), slc, tlc, src, trc,
            sl, tl, sr, tr, (), (), rounds,
            True, False, True, True,
            "joint twin-quotient refinement produced different source/target label multiplicities",
        )

    lpairs = _unique_pairing(sl, tl)
    rpairs = _unique_pairing(sr, tr)
    if lpairs == () or rpairs == ():
        return BipartiteTwinQuotientRefinement(
            "ambiguous_twin_quotient_refinement",
            int(left_size), int(right_size), slc, tlc, src, trc,
            sl, tl, sr, tr, (), (), rounds,
            False, False, True, False,
            "paired refinement is invariant-compatible but at least one quotient color class contains multiple cells; no arbitrary cell matching is selected",
        )
    if lpairs is None or rpairs is None:
        raise AssertionError("pairing mismatch should have been caught by histogram check")

    lmap = dict(lpairs)
    rmap = dict(rpairs)
    for si, ti in lpairs:
        if slbase[si] != tlbase[ti] or len(slc[si]) != len(tlc[ti]):
            return BipartiteTwinQuotientRefinement(
                "exact_twin_quotient_base_mismatch",
                int(left_size), int(right_size), slc, tlc, src, trc,
                sl, tl, sr, tr, lpairs, rpairs, rounds,
                True, False, True, True,
                "uniquely refined left quotient cells disagree in exact base color/size data",
            )
    for sj, tj in rpairs:
        if srbase[sj] != trbase[tj] or len(src[sj]) != len(trc[tj]):
            return BipartiteTwinQuotientRefinement(
                "exact_twin_quotient_base_mismatch",
                int(left_size), int(right_size), slc, tlc, src, trc,
                sl, tl, sr, tr, lpairs, rpairs, rounds,
                True, False, True, True,
                "uniquely refined right quotient cells disagree in exact base color/size data",
            )
    for si in range(len(slc)):
        for sj in range(len(src)):
            if smat[si][sj] != tmat[lmap[si]][rmap[sj]]:
                return BipartiteTwinQuotientRefinement(
                    "exact_twin_quotient_adjacency_mismatch",
                    int(left_size), int(right_size), slc, tlc, src, trc,
                    sl, tl, sr, tr, lpairs, rpairs, rounds,
                    True, False, True, True,
                    "the uniquely forced quotient cell map does not preserve a complete/empty bipartite block",
                )

    return BipartiteTwinQuotientRefinement(
        "exact_unique_twin_quotient_mapping",
        int(left_size), int(right_size), slc, tlc, src, trc,
        sl, tl, sr, tr, lpairs, rpairs, rounds,
        False, True, True, True,
        "paired exact refinement uniquely determines every twin-quotient cell map and direct block verification succeeds; internal permutations inside paired twin cells remain for the ambient transport layer",
    )
