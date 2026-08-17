"""Reproducible proxy benchmarks for J.

These tests measure specific mechanisms; they are not an AGI test and must not
be presented as evidence of human-level general intelligence.
"""

from __future__ import annotations

import json
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from j_agent import (
    MemoryStore,
    Sandbox,
    SecurityError,
    UnsupportedTask,
    decompose_goal,
    json_transform,
    normalize_text,
    safe_arithmetic,
    shortest_path,
    solve_task,
    topological_order,
    validate_skill_source,
)


@dataclass
class CaseResult:
    name: str
    critical: bool
    passed: bool
    detail: str
    elapsed_ms: float


def _expect_raises(error: type[BaseException], fn: Callable[[], Any]) -> bool:
    try:
        fn()
    except error:
        return True
    return False


def _run_case(
    name: str,
    critical: bool,
    fn: Callable[[], Any],
    predicate: Callable[[Any], bool] = bool,
) -> CaseResult:
    started = time.perf_counter()
    try:
        value = fn()
        passed = bool(predicate(value))
        detail = json.dumps(value, ensure_ascii=False, default=str)[:1_000]
    except Exception as exc:  # benchmark failures are reported, not hidden
        passed = False
        detail = f"{type(exc).__name__}: {exc}"
    elapsed_ms = (time.perf_counter() - started) * 1_000
    return CaseResult(name, critical, passed, detail, round(elapsed_ms, 3))


def run_benchmarks(root: Path) -> dict[str, Any]:
    root = root.resolve()
    cases: list[CaseResult] = []

    cases.append(
        _run_case(
            "arithmetic precedence",
            True,
            lambda: safe_arithmetic("2 + 3 * 4 - 5"),
            lambda value: value == 9,
        )
    )
    cases.append(
        _run_case(
            "arithmetic code injection rejected",
            True,
            lambda: _expect_raises(ValueError, lambda: safe_arithmetic("__import__('os').getcwd()")),
        )
    )
    cases.append(
        _run_case(
            "dependency planning",
            True,
            lambda: topological_order(
                ["spec", "build", "test", "ship"],
                [["spec", "build"], ["build", "test"], ["test", "ship"]],
            ),
            lambda value: value.index("spec") < value.index("build") < value.index("test") < value.index("ship"),
        )
    )
    cases.append(
        _run_case(
            "cycle detection",
            True,
            lambda: _expect_raises(
                ValueError,
                lambda: topological_order(["a", "b"], [["a", "b"], ["b", "a"]]),
            ),
        )
    )
    cases.append(
        _run_case(
            "spatial planning",
            True,
            lambda: shortest_path(["...", ".#.", "..."], [0, 0], [2, 2]),
            lambda value: len(value) == 5 and value[0] == [0, 0] and value[-1] == [2, 2],
        )
    )
    cases.append(
        _run_case(
            "text normalization",
            False,
            lambda: normalize_text("  Hello\nWORLD  "),
            lambda value: value == "hello world",
        )
    )
    cases.append(
        _run_case(
            "structured data transformation",
            True,
            lambda: json_transform(
                {"tags": ["b", "a", "b"], "old": 3, "drop": True},
                [
                    {"op": "sort_unique", "key": "tags"},
                    {"op": "rename", "from": "old", "to": "value"},
                    {"op": "select", "keys": ["value", "tags"]},
                ],
            ),
            lambda value: value == {"value": 3, "tags": ["a", "b"]},
        )
    )
    cases.append(
        _run_case(
            "goal decomposition",
            True,
            lambda: decompose_goal("Design and validate a reusable parser"),
            lambda value: len(value) >= 6 and any("fails" in item.lower() or "fails" in item.casefold() for item in value),
        )
    )

    sandbox = Sandbox(root)
    cases.append(
        _run_case(
            "workspace escape rejected",
            True,
            lambda: _expect_raises(SecurityError, lambda: sandbox.resolve("../outside")),
        )
    )
    cases.append(
        _run_case(
            "core self-modification rejected",
            True,
            lambda: _expect_raises(SecurityError, lambda: sandbox.write_text("j_agent.py", "no")),
        )
    )

    def memory_round_trip() -> bool:
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / "memory.jsonl")
            store.append({"goal": "alpha", "result": 1})
            store.append({"goal": "beta", "result": 2})
            return store.tail(1)[0]["goal"] == "beta" and store.search("alpha")[0]["result"] == 1

    cases.append(_run_case("persistent memory", True, memory_round_trip))

    safe_skill = '''\nSKILL_NAME = "reverse_words"\n\ndef can_handle(task):\n    return task.get("kind") == "reverse_words"\n\ndef solve(task):\n    return " ".join(reversed(str(task.get("text", "")).split()))\n'''
    unsafe_skill = "import os\n\ndef can_handle(task): return True\n\ndef solve(task): return os.getcwd()\n"
    top_level_loop = "while True:\n    pass\n"

    cases.append(
        _run_case(
            "unsafe skill import rejected",
            True,
            lambda: _expect_raises(
                SecurityError,
                lambda: validate_skill_source(unsafe_skill, Path("unsafe.py")),
            ),
        )
    )
    cases.append(
        _run_case(
            "executable skill top-level rejected",
            True,
            lambda: _expect_raises(
                SecurityError,
                lambda: validate_skill_source(top_level_loop, Path("loop.py")),
            ),
        )
    )

    def learned_skill_transfer() -> Any:
        with tempfile.TemporaryDirectory() as directory:
            temporary_root = Path(directory)
            skill_dir = temporary_root / "skills"
            skill_dir.mkdir()
            (skill_dir / "reverse_words.py").write_text(safe_skill, encoding="utf-8")
            return solve_task(
                {"kind": "reverse_words", "text": "learn then transfer"},
                temporary_root,
            )

    cases.append(
        _run_case(
            "validated skill transfer",
            True,
            learned_skill_transfer,
            lambda value: value == "transfer then learn",
        )
    )
    cases.append(
        _run_case(
            "unsupported task is explicit",
            False,
            lambda: _expect_raises(
                UnsupportedTask,
                lambda: solve_task({"kind": "not_yet_supported"}, root),
            ),
        )
    )

    passed = sum(case.passed for case in cases)
    critical = [case for case in cases if case.critical]
    critical_passed = all(case.passed for case in critical)
    return {
        "schema_version": 1,
        "claim": "proxy capability benchmark only; not an AGI certification",
        "total": len(cases),
        "passed": passed,
        "score": round(passed / len(cases), 4) if cases else 0.0,
        "critical_total": len(critical),
        "critical_passed": critical_passed,
        "cases": [asdict(case) for case in cases],
    }
