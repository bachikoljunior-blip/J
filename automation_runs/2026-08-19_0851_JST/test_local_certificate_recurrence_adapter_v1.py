from permutation_group_schreier import schreier_stabilizer_chain
from local_certificate_recurrence_adapter_v1 import local_certificate_recurrence_step


def wreath_block_action(k, s):
    n = k * s
    e = list(range(n))
    blocks = [tuple(range(i * s, (i + 1) * s)) for i in range(k)]
    swap_blocks = e.copy()
    for c in range(s):
        swap_blocks[c], swap_blocks[s + c] = swap_blocks[s + c], swap_blocks[c]
    cycle_blocks = e.copy()
    for i in range(k):
        for c in range(s):
            cycle_blocks[i * s + c] = ((i + 1) % k) * s + c
    within = e.copy()
    within[0], within[1] = within[1], within[0]
    return schreier_stabilizer_chain([tuple(swap_blocks), tuple(cycle_blocks), tuple(within)]), blocks


def test_broken_block_produces_verified_canonical_recurrence_step():
    G, blocks = wreath_block_action(10, 2)
    values = [0] * G.degree
    for u in blocks[0]:
        values[u] = 1

    result = local_certificate_recurrence_step(G, blocks, values, test_size=3)
    assert result.status == "verified_local_certificate_recurrence_step"
    assert result.relation.significant_split
    assert result.validation is not None and result.validation.progress_verified
    assert result.certificate is not None
    assert result.certificate.canonical
    assert result.certificate.local_certificate_count == 120
    assert tuple(child.domain_size for child in result.certificate.children) == (1, 9)
    assert all(child.canonical_partition_cells == (1, 9) for child in result.certificate.children)


def test_uniform_full_relation_fails_closed_without_inventing_children():
    G, blocks = wreath_block_action(10, 2)
    values = [0] * G.degree
    result = local_certificate_recurrence_step(G, blocks, values, test_size=3)
    assert result.status == "canonical_local_relation_no_recurrence_split"
    assert result.relation.full_count == result.relation.test_count
    assert result.certificate is None
    assert result.validation is None


def test_relabeling_preserves_accounting_partition_signature():
    G, blocks = wreath_block_action(10, 2)
    values = [0] * G.degree
    for u in blocks[0]:
        values[u] = 1
    base = local_certificate_recurrence_step(G, blocks, values, test_size=3)

    permutation = list(range(1, 10)) + [0]
    reordered = [blocks[i] for i in permutation]
    again = local_certificate_recurrence_step(G, reordered, values, test_size=3)

    assert again.status == base.status == "verified_local_certificate_recurrence_step"
    assert tuple(child.domain_size for child in again.certificate.children) == tuple(
        child.domain_size for child in base.certificate.children
    )
    assert again.validation.charged_log2_work == base.validation.charged_log2_work


def test_testset_resource_limit_remains_fail_closed():
    G, blocks = wreath_block_action(10, 2)
    result = local_certificate_recurrence_step(
        G, blocks, [0] * G.degree, test_size=3, max_test_sets=10
    )
    assert result.status == "undetermined_testset_limit"
    assert result.certificate is None
    assert result.validation is None
