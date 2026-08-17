from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks import run_benchmarks
from j_agent import (
    Decision,
    MemoryStore,
    OfflinePlanner,
    Sandbox,
    SecurityError,
    UnsupportedTask,
    decompose_goal,
    extract_json,
    json_transform,
    normalize_text,
    safe_arithmetic,
    shortest_path,
    solve_task,
    topological_order,
    validate_skill_source,
)


class DecisionTests(unittest.TestCase):
    def test_invalid_fields_fall_back_to_safe_values(self) -> None:
        decision = Decision.from_mapping({"status": "mystery", "action": "shell", "args": []})
        self.assertEqual(decision.status, "continue")
        self.assertEqual(decision.action, "none")
        self.assertEqual(decision.args, {})

    def test_json_extraction_handles_fence(self) -> None:
        self.assertEqual(extract_json('```json\n{"status":"done"}\n```')["status"], "done")


class SandboxTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.sandbox = Sandbox(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_path_escape_and_absolute_paths_are_blocked(self) -> None:
        with self.assertRaises(SecurityError):
            self.sandbox.resolve("../outside")
        with self.assertRaises(SecurityError):
            self.sandbox.resolve("/tmp/outside")

    def test_writes_are_allowlisted(self) -> None:
        with self.assertRaises(SecurityError):
            self.sandbox.write_text("j_agent.py", "bad")
        path = self.sandbox.write_text("workspace/result.txt", "ok")
        self.assertEqual(path, "workspace/result.txt")
        self.assertEqual((self.root / path).read_text(encoding="utf-8"), "ok")

    def test_child_environment_removes_credentials(self) -> None:
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "secret", "GITHUB_TOKEN": "secret", "SAFE_VALUE": "ok"},
            clear=False,
        ):
            env = self.sandbox._sanitized_env()
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("GITHUB_TOKEN", env)
        self.assertNotIn("SAFE_VALUE", env)
        self.assertIn("PATH", env)


class GeneralistFunctionTests(unittest.TestCase):
    def test_arithmetic_and_injection_rejection(self) -> None:
        self.assertEqual(safe_arithmetic("(8 + 4) / 3"), 4)
        with self.assertRaises(ValueError):
            safe_arithmetic("__import__('os').getcwd()")

    def test_topological_order_and_cycle(self) -> None:
        order = topological_order(["a", "b", "c"], [["a", "b"], ["b", "c"]])
        self.assertLess(order.index("a"), order.index("c"))
        with self.assertRaises(ValueError):
            topological_order(["a", "b"], [["a", "b"], ["b", "a"]])

    def test_shortest_path(self) -> None:
        path = shortest_path(["...", ".#.", "..."], [0, 0], [2, 2])
        self.assertEqual(path[0], [0, 0])
        self.assertEqual(path[-1], [2, 2])
        self.assertEqual(len(path), 5)

    def test_text_and_json_transform(self) -> None:
        self.assertEqual(normalize_text("  A\n B "), "a b")
        value = json_transform(
            {"items": ["b", "a", "b"], "old": 7},
            [
                {"op": "sort_unique", "key": "items"},
                {"op": "rename", "from": "old", "to": "new"},
            ],
        )
        self.assertEqual(value, {"items": ["a", "b"], "new": 7})

    def test_goal_decomposition_is_actionable(self) -> None:
        steps = decompose_goal("Build a robust parser")
        self.assertGreaterEqual(len(steps), 6)
        self.assertTrue(any("success criteria" in step.lower() for step in steps))


class SkillTests(unittest.TestCase):
    def test_unsafe_skill_is_rejected(self) -> None:
        with self.assertRaises(SecurityError):
            validate_skill_source("import os\n", Path("bad.py"))
        with self.assertRaises(SecurityError):
            validate_skill_source("while True:\n    pass\n", Path("loop.py"))

    def test_validated_skill_extends_task_support(self) -> None:
        source = '''\nSKILL_NAME = "reverse_words"\n\ndef can_handle(task):\n    return task.get("kind") == "reverse_words"\n\ndef solve(task):\n    return " ".join(reversed(str(task["text"]).split()))\n'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "skills").mkdir()
            (root / "skills" / "reverse_words.py").write_text(source, encoding="utf-8")
            result = solve_task({"kind": "reverse_words", "text": "one two three"}, root)
        self.assertEqual(result, "three two one")

    def test_unknown_task_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(UnsupportedTask):
                solve_task({"kind": "unknown"}, Path(directory))


class MemoryAndPlannerTests(unittest.TestCase):
    def test_memory_round_trip_and_search(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / "memory.jsonl")
            store.append({"goal": "alpha", "value": 1})
            store.append({"goal": "beta", "value": 2})
            self.assertEqual(store.tail(1)[0]["goal"], "beta")
            self.assertEqual(store.search("alpha")[0]["value"], 1)

    def test_offline_planner_requires_passing_evidence(self) -> None:
        planner = OfflinePlanner()
        history = [
            {"decision": {"action": "list_files"}, "result": []},
            {"decision": {"action": "read_file"}, "result": "readme"},
            {"decision": {"action": "run_tests"}, "result": {"returncode": 0}},
            {"decision": {"action": "benchmark"}, "result": {"returncode": 0}},
            {"decision": {"action": "write_file"}, "result": {"ok": True}},
        ]
        decision = planner.decide({"goal": "improve", "history": history, "files": ["README.md"]})
        self.assertEqual(decision.status, "done")


class BenchmarkTests(unittest.TestCase):
    def test_all_critical_proxy_benchmarks_pass(self) -> None:
        root = Path(__file__).resolve().parents[1]
        report = run_benchmarks(root)
        self.assertTrue(report["critical_passed"], json.dumps(report, indent=2))


if __name__ == "__main__":
    unittest.main()
