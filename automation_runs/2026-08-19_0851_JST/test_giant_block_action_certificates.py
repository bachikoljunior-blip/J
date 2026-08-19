from collections import deque
from math import factorial

from permutation_group_schreier import compose, identity, schreier_stabilizer_chain
from giant_block_action_certificates import analyze_giant_block_action, _block_action


def wreath_block_action(k, s, extra_fixed=0):
    n = k * s + extra_fixed
    e = list(range(n))
    blocks = [tuple(range(i * s, (i + 1) * s)) for i in range(k)]

    swap_blocks = e.copy()
    for c in range(s):
        swap_blocks[c], swap_blocks[s + c] = swap_blocks[s + c], swap_blocks[c]

    cycle_blocks = e.copy()
    for i in range(k):
        for c in range(s):
            cycle_blocks[i * s + c] = ((i + 1) % k) * s + c

    gens = [tuple(swap_blocks), tuple(cycle_blocks)]
    if s > 1:
        within = e.copy(); within[0], within[1] = within[1], within[0]
        gens.append(tuple(within))
    return schreier_stabilizer_chain(gens), blocks


def closure(gens):
    n = len(gens[0])
    e = identity(n)
    seen = {e}
    todo = deque([e])
    while todo:
        x = todo.popleft()
        for g in gens:
            y = compose(x, g)
            if y not in seen:
                seen.add(y)
                todo.append(y)
    return seen


def test_small_wreath_action_matches_full_explicit_homomorphism_oracle():
    G, blocks = wreath_block_action(5, 2, 2)
    cert = analyze_giant_block_action(G, blocks)
    assert G.order == 3840
    assert cert.image_order == factorial(5)
    assert cert.kernel_order == 2 ** 5
    assert len(cert.affected_points) == 10
    assert len(cert.unaffected_points) == 2
    assert cert.affected_orbit_lemma_verified

    elements = closure(G.original_generators or [identity(G.degree)])
    point_to_block = {u: i for i, b in enumerate(blocks) for u in b}
    images = {_block_action(g, blocks, point_to_block) for g in elements}
    kernel = {g for g in elements if _block_action(g, blocks, point_to_block) == identity(5)}
    assert len(images) == cert.image_order
    assert len(kernel) == cert.kernel_order


def test_huge_giant_actions_do_not_enumerate_the_image_group():
    for k in (9, 12, 20):
        G, blocks = wreath_block_action(k, 2, 3)
        cert = analyze_giant_block_action(G, blocks)
        assert cert.status == "exact_giant_action_certificate"
        assert cert.image_order == factorial(k)
        assert cert.kernel_order == 2 ** k
        assert cert.group_order == (2 ** k) * factorial(k)
        assert len(cert.affected_points) == 2 * k
        assert len(cert.unaffected_points) == 3
        assert cert.unaffected_stabilizer_theorem_applicable
        assert cert.unaffected_stabilizer_theorem_verified
        assert cert.affected_orbit_lemma_verified
        assert cert.kernel_generator_count == k
