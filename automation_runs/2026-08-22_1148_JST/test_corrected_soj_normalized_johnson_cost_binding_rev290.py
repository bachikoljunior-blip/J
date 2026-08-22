from __future__ import annotations

from dataclasses import replace
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import sys

HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "corrected_soj_normalized_johnson_cost_binding_v1.py"
spec = importlib.util.spec_from_file_location("rev290_binding", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)

BindingError = module.CorrectedSOJNormalizedJohnsonCostBindingError
bind = module.bind_normalized_johnson_terminal_cost
replay = module.replay_normalized_johnson_terminal_cost_binding

H64_A = "a" * 64
H64_B = "b" * 64
H64_C = "c" * 64


def expect_error(fn, fragment: str) -> None:
    try:
        fn()
    except BindingError as exc:
        assert fragment in str(exc), (fragment, str(exc))
    else:
        raise AssertionError(f"expected BindingError containing {fragment!r}")


def fixtures(*, proof_identity: str | None = H64_C):
    transition = NS(
        status="certified_corrected_soj_explicit_johnson_embedding",
        transition_kind="johnson_embedding",
        theorem_input_gate=True,
        canonical=True,
        exact=True,
        progress_certified=True,
        multiplicative_cost=2.0,
        max_multiplicative_cost=4.0,
        johnson_ground_size=4,
        johnson_subset_size=2,
        johnson_vertex_count=6,
        reason="certified",
    )
    terminal = NS(
        status="exact_primitive_johnson_ground_coset",
        operation_kind="primitive_johnson_ground_terminal",
        root_n=20,
        domain_size=6,
        canonical=True,
        exact=True,
        local_cost_certified=True,
        local_log2_cost_bound=3.0,
        terminal_certified=True,
        johnson_ground_size=4,
        johnson_subset_size=2,
        ground_permutations_checked=24,
        recognition_search_nodes=7,
        proof_identity=proof_identity,
    )
    normalized = NS(
        schema="rev288_corrected_soj_strict_evidence_v1",
        root_n=20,
        current_domain_size=10,
        transition=transition,
        terminal=terminal,
        full_johnson_vertex_count=6,
        replay_stable_upstream_identity=proof_identity is not None,
        evidence_identity=H64_A,
    )
    cost_transition = NS(**vars(transition), snapshot_identity=H64_B)
    cost_terminal = NS(**vars(terminal))
    accounting = NS(
        n=20,
        m=10,
        operation_kind="corrected_soj_johnson_terminal_composition",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=5.0,
        children=(),
        terminal_certified=True,
        reason="combined",
    )
    validation = NS(certified=True, status="certified_quasipolynomial_recurrence")
    cost = NS(
        certified=True,
        current_domain_size=10,
        transition=cost_transition,
        terminal=cost_terminal,
        transition_log2_charge=2.0,
        terminal_log2_charge=3.0,
        accounting_root=accounting,
        validation=validation,
        proof_identity=H64_C,
        reason="bound",
    )
    return normalized, cost


def test_valid_binding_and_replay() -> None:
    normalized, cost = fixtures()
    binding = bind(
        normalized,
        cost,
        normalized_replay_verified=True,
        terminal_cost_replay_verified=True,
    )
    assert binding.certified is True
    assert binding.root_n == 20
    assert binding.current_domain_size == 10
    assert binding.combined_log2_charge == 5.0
    assert binding.upstream_terminal_identity_present is True
    assert len(binding.binding_identity) == 64
    assert replay(
        binding,
        normalized,
        cost,
        normalized_replay_verified=True,
        terminal_cost_replay_verified=True,
    )


def test_allows_structural_exact_empty_without_terminal_identity() -> None:
    normalized, cost = fixtures(proof_identity=None)
    normalized.terminal.status = "exact_empty_primitive_johnson_ground"
    cost.terminal.status = "exact_empty_primitive_johnson_ground"
    binding = bind(
        normalized,
        cost,
        normalized_replay_verified=True,
        terminal_cost_replay_verified=True,
    )
    assert binding.terminal_status == "exact_empty_primitive_johnson_ground"
    assert binding.upstream_terminal_identity_present is False


def test_requires_exact_replay_booleans() -> None:
    normalized, cost = fixtures()
    expect_error(
        lambda: bind(
            normalized,
            cost,
            normalized_replay_verified=1,
            terminal_cost_replay_verified=True,
        ),
        "exact bool",
    )
    expect_error(
        lambda: bind(
            normalized,
            cost,
            normalized_replay_verified=True,
            terminal_cost_replay_verified=False,
        ),
        "mechanically verified",
    )


def test_rejects_transition_drift() -> None:
    normalized, cost = fixtures()
    cost.transition.reason = "drifted"
    expect_error(
        lambda: bind(normalized, cost, normalized_replay_verified=True, terminal_cost_replay_verified=True),
        "cost.transition.reason",
    )


def test_rejects_terminal_drift() -> None:
    normalized, cost = fixtures()
    cost.terminal.recognition_search_nodes = 8
    expect_error(
        lambda: bind(normalized, cost, normalized_replay_verified=True, terminal_cost_replay_verified=True),
        "cost.terminal.recognition_search_nodes",
    )


def test_rejects_root_or_measure_drift() -> None:
    normalized, cost = fixtures()
    cost.accounting_root.n = 21
    expect_error(
        lambda: bind(normalized, cost, normalized_replay_verified=True, terminal_cost_replay_verified=True),
        "accounting root_n",
    )
    normalized, cost = fixtures()
    cost.accounting_root.m = 9
    expect_error(
        lambda: bind(normalized, cost, normalized_replay_verified=True, terminal_cost_replay_verified=True),
        "accounting measure",
    )


def test_rejects_charge_drift_and_nonfinite() -> None:
    normalized, cost = fixtures()
    cost.accounting_root.local_log2_cost_bound = 4.0
    expect_error(
        lambda: bind(normalized, cost, normalized_replay_verified=True, terminal_cost_replay_verified=True),
        "differs from transition plus terminal",
    )
    normalized, cost = fixtures()
    cost.terminal_log2_charge = float("nan")
    expect_error(
        lambda: bind(normalized, cost, normalized_replay_verified=True, terminal_cost_replay_verified=True),
        "finite",
    )


def test_rejects_invalid_identity_and_terminal_children() -> None:
    normalized, cost = fixtures()
    normalized.evidence_identity = "A" * 64
    expect_error(
        lambda: bind(normalized, cost, normalized_replay_verified=True, terminal_cost_replay_verified=True),
        "lowercase SHA-256",
    )
    normalized, cost = fixtures()
    cost.accounting_root.children = (NS(),)
    expect_error(
        lambda: bind(normalized, cost, normalized_replay_verified=True, terminal_cost_replay_verified=True),
        "terminal leaf",
    )


def test_rejects_replay_stability_flag_drift() -> None:
    normalized, cost = fixtures()
    normalized.replay_stable_upstream_identity = False
    expect_error(
        lambda: bind(normalized, cost, normalized_replay_verified=True, terminal_cost_replay_verified=True),
        "replay-stability flag",
    )


def test_replay_detects_tampering() -> None:
    normalized, cost = fixtures()
    binding = bind(normalized, cost, normalized_replay_verified=True, terminal_cost_replay_verified=True)
    tampered = replace(binding, binding_identity="d" * 64)
    assert not replay(
        tampered,
        normalized,
        cost,
        normalized_replay_verified=True,
        terminal_cost_replay_verified=True,
    )


def test_module_has_no_branch_only_sibling_imports() -> None:
    import ast

    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    forbidden_fragments = (
        "corrected_soj_strict_evidence",
        "corrected_soj_johnson_terminal_cost",
        "rev288",
        "rev286",
    )
    assert not any(
        fragment in name
        for name in imported
        for fragment in forbidden_fragments
    ), imported


if __name__ == "__main__":
    tests = [
        value
        for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    for case in tests:
        case()
    print(f"rev290 normalized Johnson cost binding: {len(tests)} tests passed")
