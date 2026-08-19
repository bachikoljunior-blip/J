from block_action_preimage_coset_v1 import block_action_preimage_coset
from giant_block_action_certificates import _block_action
from permutation_group_schreier import identity, schreier_stabilizer_chain


def wreath_block_action(k, s, *, include_swap=True):
    n = k * s
    e = list(range(n))
    blocks = [tuple(range(i * s, (i + 1) * s)) for i in range(k)]
    cycle_blocks = e.copy()
    for i in range(k):
        for c in range(s):
            cycle_blocks[i * s + c] = ((i + 1) % k) * s + c
    gens = [tuple(cycle_blocks)]
    swap_blocks = e.copy()
    for c in range(s):
        swap_blocks[c], swap_blocks[s + c] = swap_blocks[s + c], swap_blocks[c]
    if include_swap:
        gens.append(tuple(swap_blocks))
    within = e.copy()
    within[0], within[1] = within[1], within[0]
    gens.append(tuple(within))
    return schreier_stabilizer_chain(gens), blocks, tuple(cycle_blocks), tuple(swap_blocks)


def test_exact_preimage_coset_contains_known_block_cycle_and_has_exact_kernel():
    G, blocks, domain_cycle, _ = wreath_block_action(5, 2)
    quotient_cycle = (1, 2, 3, 4, 0)
    r = block_action_preimage_coset(G, blocks, quotient_cycle)
    assert r.status == "exact_block_action_preimage_coset"
    assert r.image_order == 120
    assert r.kernel_order == 32
    assert r.kernel_order * r.image_order == G.order
    assert r.coset.contains(domain_cycle)

    point_to_block = {u: i for i, b in enumerate(blocks) for u in b}
    assert _block_action(r.representative, blocks, point_to_block) == quotient_cycle
    for h in r.kernel.original_generators:
        assert G.contains(h)
        assert _block_action(h, blocks, point_to_block) == identity(5)


def test_exact_preimage_coset_contains_known_block_transposition():
    G, blocks, _, domain_swap = wreath_block_action(5, 2)
    quotient_swap = (1, 0, 2, 3, 4)
    r = block_action_preimage_coset(G, blocks, quotient_swap)
    assert r.status == "exact_block_action_preimage_coset"
    assert r.coset.contains(domain_swap)


def test_quotient_membership_failure_is_certified_without_fake_lift():
    G, blocks, _, _ = wreath_block_action(5, 2, include_swap=False)
    quotient_swap = (1, 0, 2, 3, 4)
    r = block_action_preimage_coset(G, blocks, quotient_swap)
    assert r.status == "quotient_not_in_image"
    assert r.representative is None
    assert r.coset is None
    assert r.image_order == 5
