from types import SimpleNamespace

import design_tuple_full_string_union_si_v1 as _union
from coset_stabilizer_primitives import RightCoset
from design_union_reconstruction_resource_v1 import (
    design_union_reconstruction_resource_envelope,
)
from permutation_group_schreier import identity, schreier_stabilizer_chain


def _branch(degree=4):
    group = schreier_stabilizer_chain((identity(degree),))
    return group, SimpleNamespace(coset=RightCoset(group, identity(degree)))


def _plan(branch):
    return SimpleNamespace(
        exact_empty=False,
        complete=True,
        status="certified_complete_design_tuple_transport_cover",
        branches=(branch,),
        surviving_branch_count=1,
        local_log2_cost_bound=1.0,
    )


def test_union_cap_rejects_before_first_reconstruction_chain(monkeypatch):
    group, branch = _branch()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("union Schreier chain started before admission")

    monkeypatch.setattr(_union, "schreier_stabilizer_chain", forbidden)
    got = _union.solve_design_tuple_transport_full_string(
        group, _plan(branch), (0, 0, 0, 0), (0, 0, 0, 0),
        root_n=4,
        max_design_full_string_child_work=10**30,
        max_design_union_reconstruction_work=1,
        quasipoly_constant=10**6,
    )
    assert got.status == "design_union_reconstruction_work_cap_exceeded"
    assert not got.exact and got.branches_checked == 1
    assert got.union_resource_envelope is not None
    assert got.union_resource_envelope.work_upper_bound == 2


def test_admitted_union_records_every_generator_input():
    group, branch = _branch()
    got = _union.solve_design_tuple_transport_full_string(
        group, _plan(branch), (0, 0, 0, 0), (0, 0, 0, 0),
        root_n=4,
        max_design_full_string_child_work=10**30,
        max_design_union_reconstruction_work=10**20,
        quasipoly_constant=10**6,
    )
    assert got.exact and got.complete and got.coset is not None
    proof = got.union_resource_envelope
    assert proof is not None and proof.admitted and proof.complete
    assert proof.executed_generator_count == proof.generator_input_count


def test_resource_envelope_uses_caller_cap_plus_one_saturation():
    group, branch = _branch()
    result = SimpleNamespace(exact=True, coset=branch.coset)
    got = design_union_reconstruction_resource_envelope(
        group, (result,), max_work=7,
    )
    assert not got.admitted
    assert got.work_upper_bound == 8


def test_exact_empty_union_needs_no_reconstruction_phase():
    cycle = schreier_stabilizer_chain(((1, 2, 3, 4, 0),))
    branch = SimpleNamespace(coset=RightCoset(cycle, identity(5)))
    got = _union.solve_design_tuple_transport_full_string(
        cycle, _plan(branch),
        (1, 1, 0, 0, 0), (1, 0, 1, 0, 0),
        root_n=5, max_group_order=2,
        max_design_full_string_child_work=10**20,
        max_design_union_reconstruction_work=1,
        quasipoly_constant=10**6,
    )
    assert got.exact and got.coset is None
    assert got.union_resource_envelope is None
