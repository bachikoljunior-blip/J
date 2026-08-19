from collections import deque
from itertools import combinations

from permutation_group_schreier import compose, identity, schreier_stabilizer_chain
from giant_block_action_certificates import _block_action
from local_fullness_certificates import local_fullness_certificate


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
    within = e.copy(); within[0], within[1] = within[1], within[0]
    return schreier_stabilizer_chain([tuple(swap_blocks), tuple(cycle_blocks), tuple(within)]), blocks


def closure(gens):
    n = len(gens[0]); e = identity(n); seen = {e}; todo = deque([e])
    while todo:
        x = todo.popleft()
        for g in gens:
            y = compose(x, g)
            if y not in seen:
                seen.add(y); todo.append(y)
    return seen


def test_all_three_point_test_sets_match_explicit_small_group_oracle():
    G, blocks = wreath_block_action(5, 2)
    elements = closure(G.original_generators)
    point_to_block = {u: i for i, b in enumerate(blocks) for u in b}

    for special_block in (None, 0):
        values = [0] * G.degree
        if special_block is not None:
            for u in blocks[special_block]: values[u] = 1
        explicit_aut = [g for g in elements if all(values[g[i]] == values[i] for i in range(G.degree))]
        explicit_images = {_block_action(g, blocks, point_to_block) for g in explicit_aut}

        for T in combinations(range(5), 3):
            cert = local_fullness_certificate(G, blocks, values, T)
            q = list(range(5)); a, b, c = T; q[a] = b; q[b] = c; q[c] = a
            assert cert.full == (tuple(q) in explicit_images)


def test_large_full_and_nonfull_certificates_do_not_enumerate_source_group():
    for k in (12, 20):
        G, blocks = wreath_block_action(k, 2)

        constant = [0] * G.degree
        full = local_fullness_certificate(G, blocks, constant, (0, 1, 2, 3, 4), max_nodes=500000)
        assert full.status == "certified_full"
        assert full.full is True

        broken = [0] * G.degree
        for u in blocks[0]: broken[u] = 1
        nonfull = local_fullness_certificate(G, blocks, broken, (0, 1, 2, 3), max_nodes=500000)
        assert nonfull.status == "certified_nonfull"
        assert nonfull.full is False
        assert nonfull.missing_alt_generator is not None

        unaffected_test = local_fullness_certificate(G, blocks, broken, (1, 2, 3, 4), max_nodes=500000)
        assert unaffected_test.status == "certified_full"
