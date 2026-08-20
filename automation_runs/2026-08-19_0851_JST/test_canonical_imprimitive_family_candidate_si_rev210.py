from canonical_block_system import canonical_minimal_block_system
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v1 import AccountingChild, RecurrenceAccountingNode
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from quasipoly_recurrence_accounting_v4 import validate_quasipoly_recurrence_tree_v4
from u2_candidate_coset_string_iso_v4 import candidate_coset_string_isomorphism_u4
from u2_candidate_coset_string_iso_v5 import candidate_coset_string_isomorphism_u5


def klein_four_regular():
    # Regular V_4 on four points.  Its three order-two subgroups give three
    # equally minimum invariant 2+2 block systems, so no single member may be
    # selected by point labels as a canonical structural continuation.
    a = (1, 0, 3, 2)  # (0 1)(2 3)
    b = (2, 3, 0, 1)  # (0 2)(1 3)
    return schreier_stabilizer_chain((a, b))


def test_rev210_closes_multiple_canonical_minimum_block_systems_exactly():
    G = klein_four_regular()
    cert = canonical_minimal_block_system(G)
    assert cert.status == "multiple_canonical_minimal_block_systems", cert
    assert len(cert.block_systems) == 3

    source = (0, 0, 1, 2)
    target = source
    candidate = RightCoset(G, identity(G.degree))

    before = candidate_coset_string_isomorphism_u4(
        candidate,
        source,
        target,
        root_n=64,
        max_explicit_degree=2,
        max_group_order=1,
    )
    assert not before.exact, before
    assert "canonical_imprimitive_family" in before.status, before

    got = candidate_coset_string_isomorphism_u5(
        candidate,
        source,
        target,
        root_n=64,
        max_explicit_degree=2,
        max_group_order=1,
        max_family_quotient_order=8,
    )
    assert got.exact and got.coset is not None, got
    # Only identity in V_4 stabilizes this asymmetric color string.
    assert got.coset.subgroup.order == 1
    assert got.coset.contains(identity(G.degree))
    check = validate_quasipoly_recurrence_tree_v4(got.accounting)
    assert check.certified, check


def test_rev210_family_gate_fails_closed_instead_of_choosing_one_system():
    G = klein_four_regular()
    source = (0, 0, 1, 2)
    got = candidate_coset_string_isomorphism_u5(
        RightCoset(G, identity(G.degree)),
        source,
        source,
        root_n=64,
        max_explicit_degree=2,
        max_group_order=1,
        max_family_systems=2,
        max_family_quotient_order=8,
    )
    assert not got.exact
    assert "family_count_gate" in got.status


def test_v4_recurrence_allows_exact_terminal_small_quotient_fiber_only():
    terminal = RecurrenceAccountingNode(
        n=64,
        m=4,
        operation_kind="candidate_full_accept_terminal",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=8.0,
        children=(),
        terminal_certified=True,
        reason="synthetic exact same-domain quotient fiber",
    )
    parent = RecurrenceAccountingNode(
        n=64,
        m=4,
        operation_kind="imprimitive_small_quotient",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=10.0,
        children=(AccountingChild(terminal),),
        terminal_certified=False,
        reason="polynomial quotient enumeration whose only fiber terminates exactly",
    )
    old = validate_quasipoly_recurrence_tree_v3(parent)
    assert not old.certified
    assert old.status == "unexposed_imprimitive_kernel_progress"
    new = validate_quasipoly_recurrence_tree_v4(parent)
    assert new.certified, new
