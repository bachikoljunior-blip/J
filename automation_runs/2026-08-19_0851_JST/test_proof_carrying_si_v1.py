from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, schreier_stabilizer_chain
from proof_carrying_si_v1 import r1_string_isomorphism_child
from quasipoly_recurrence_accounting_v1 import validate_quasipoly_recurrence_tree


def cycle(n):
    return tuple((i + 1) % n for i in range(n))


def test_small_child_exact_coset_and_accounting_are_same_execution_object():
    G = schreier_stabilizer_chain([cycle(3)])
    proof = r1_string_isomorphism_child(
        G, (0, 1, 2), (0, 1, 2), root_n=64, max_explicit_degree=8
    )
    assert proof.status == "exact_small_intersection_coset"
    assert proof.exact and proof.terminal_certified and proof.local_cost_certified
    assert proof.coset is not None
    assert proof.coset.subgroup.order == 1
    assert proof.coset.contains(identity(3))
    assert proof.permutation_candidates_checked == 12
    validation = validate_quasipoly_recurrence_tree(proof.accounting)
    assert validation.certified, validation


def test_value_multiplicity_mismatch_is_exact_empty_proof():
    G = schreier_stabilizer_chain([identity(4)])
    proof = r1_string_isomorphism_child(
        G, (0, 0, 1, 1), (0, 1, 1, 1), root_n=64
    )
    assert proof.status == "exact_empty_value_multiplicity"
    assert proof.exact and proof.coset is None and proof.terminal_certified
    assert validate_quasipoly_recurrence_tree(proof.accounting).certified


def test_nonpolylog_child_never_falls_back_to_node_capped_exact_search():
    n = 20
    G = schreier_stabilizer_chain([cycle(n)])
    proof = r1_string_isomorphism_child(
        G, (0,) * n, (0,) * n, root_n=n, max_explicit_degree=20
    )
    assert proof.status == "undetermined_nonpolylog_child_requires_r1"
    assert not proof.exact
    assert proof.coset is None
    assert proof.permutation_candidates_checked == 0
    assert not proof.local_cost_certified
    assert not validate_quasipoly_recurrence_tree(proof.accounting).certified


def test_implementation_cap_fails_closed_inside_polylog_window():
    n = 9
    G = schreier_stabilizer_chain([cycle(n)])
    proof = r1_string_isomorphism_child(
        G, tuple(range(n)), tuple(range(n)), root_n=128,
        max_explicit_degree=8,
    )
    assert proof.status == "undetermined_explicit_terminal_cap"
    assert not proof.exact
    assert proof.permutation_candidates_checked == 0
