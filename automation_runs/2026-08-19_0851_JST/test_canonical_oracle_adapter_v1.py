import shutil

from canonical_oracle_adapter_v1 import graph6_text, canonicalize_with_external_oracle


def test_graph6_known_small_graphs():
    assert graph6_text(0, []) == '?'
    assert graph6_text(1, []) == '@'
    assert graph6_text(2, []) == 'A?'
    assert graph6_text(2, [(0, 1)]) == 'A_'


def test_graph6_is_edge_order_independent():
    a = graph6_text(5, [(0, 1), (2, 4), (1, 3)])
    b = graph6_text(5, [(3, 1), (4, 2), (1, 0)])
    assert a == b


def test_external_oracle_is_explicitly_fail_closed_when_absent():
    r = canonicalize_with_external_oracle(4, [(0, 1), (1, 2), (2, 3)])
    if shutil.which('labelg') is None:
        assert r.status == 'oracle_unavailable'
        assert r.canonical_text is None
    else:
        assert r.status == 'canonical'
        assert r.backend == 'nauty-labelg'
        assert r.canonical_text
