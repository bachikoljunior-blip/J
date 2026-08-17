from __future__ import annotations

import argparse
import ast
import copy
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter, deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Protocol

ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL = os.getenv("J_MODEL", "gpt-5")
DEFAULT_MAX_STEPS = int(os.getenv("J_MAX_STEPS", "12"))
MAX_RESULT_CHARS = 24_000
MAX_SKILL_SOURCE_CHARS = 64_000

PROTECTED_WRITE_PATHS = (
    ".git",
    ".github",
    "scripts",
    "AGI_CRITERIA.md",
    "SECURITY.md",
    "benchmarks.py",
    "tests/test_core.py",
    "pyproject.toml",
)
ALLOWED_WRITE_PATHS = (
    "skills",
    "tests/generated",
    "docs",
    "state",
    "reports",
    "workspace",
)


class UnsupportedTask(ValueError):
    """Raised when no built-in or validated plugin can solve a task."""


class SecurityError(ValueError):
    """Raised when an operation attempts to leave the repository boundary."""


@dataclass(frozen=True)
class Decision:
    status: str
    summary: str
    action: str = "none"
    args: dict[str, Any] | None = None
    next_goal: str | None = None

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "Decision":
        status = str(value.get("status", "continue")).lower()
        if status not in {"continue", "done", "blocked"}:
            status = "continue"
        action = str(value.get("action", "none")).lower()
        if action not in {
            "none",
            "list_files",
            "read_file",
            "write_file",
            "search_text",
            "run_tests",
            "benchmark",
            "remember",
        }:
            action = "none"
        args = value.get("args")
        return cls(
            status=status,
            summary=str(value.get("summary", ""))[:4_000],
            action=action,
            args=args if isinstance(args, dict) else {},
            next_goal=(str(value["next_goal"])[:4_000] if value.get("next_goal") else None),
        )


class Planner(Protocol):
    name: str

    def decide(self, context: dict[str, Any]) -> Decision:
        ...


def _path_is_or_is_under(path: str, prefix: str) -> bool:
    normalized = path.replace("\\", "/").strip("/")
    prefix = prefix.strip("/")
    return normalized == prefix or normalized.startswith(prefix + "/")


class Sandbox:
    """Repository-confined file and validation tools.

    There is intentionally no arbitrary shell or Python execution tool. The only
    subprocesses are fixed validation commands with secrets removed from the
    child environment.
    """

    def __init__(self, root: Path = ROOT):
        self.root = root.resolve()

    def resolve(self, relative: str | Path) -> Path:
        candidate = Path(relative)
        if candidate.is_absolute():
            raise SecurityError("absolute paths are not allowed")
        resolved = (self.root / candidate).resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise SecurityError("path escapes repository") from exc
        if ".git" in resolved.relative_to(self.root).parts:
            raise SecurityError(".git access is not allowed")
        return resolved

    def relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.root).as_posix()

    def _assert_writable(self, relative: str | Path) -> Path:
        path = self.resolve(relative)
        rel = self.relative(path)
        if any(_path_is_or_is_under(rel, p) for p in PROTECTED_WRITE_PATHS):
            raise SecurityError(f"protected path: {rel}")
        if not any(_path_is_or_is_under(rel, p) for p in ALLOWED_WRITE_PATHS):
            raise SecurityError(f"writes are limited to {', '.join(ALLOWED_WRITE_PATHS)}")
        return path

    def list_files(self, pattern: str = "**/*", limit: int = 250) -> list[str]:
        out: list[str] = []
        for path in sorted(self.root.glob(pattern)):
            if not path.is_file():
                continue
            rel = self.relative(path)
            if rel.startswith(".git/"):
                continue
            out.append(rel)
            if len(out) >= max(1, min(limit, 1_000)):
                break
        return out

    def read_text(self, relative: str, max_chars: int = MAX_RESULT_CHARS) -> str:
        path = self.resolve(relative)
        if not path.is_file():
            raise FileNotFoundError(relative)
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars]

    def write_text(self, relative: str, content: str) -> str:
        path = self._assert_writable(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return self.relative(path)

    def search_text(self, query: str, pattern: str = "**/*", limit: int = 100) -> list[dict[str, Any]]:
        if not query:
            return []
        matches: list[dict[str, Any]] = []
        for rel in self.list_files(pattern=pattern, limit=1_000):
            path = self.resolve(rel)
            if path.stat().st_size > 1_000_000:
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for number, line in enumerate(lines, 1):
                if query.lower() in line.lower():
                    matches.append({"path": rel, "line": number, "text": line[:500]})
                    if len(matches) >= max(1, min(limit, 500)):
                        return matches
        return matches

    def _sanitized_env(self) -> dict[str, str]:
        home = self.root / "workspace" / ".home"
        home.mkdir(parents=True, exist_ok=True)
        return {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(home),
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "PYTHONPATH": str(self.root),
            "J_SANDBOX": "1",
        }

    def run_fixed(self, command: list[str], timeout: int = 180) -> dict[str, Any]:
        completed = subprocess.run(
            command,
            cwd=self.root,
            env=self._sanitized_env(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = (completed.stdout + completed.stderr)[-MAX_RESULT_CHARS:]
        return {"returncode": completed.returncode, "output": output}

    def execute(self, action: str, args: dict[str, Any]) -> Any:
        if action == "none":
            return {"ok": True, "message": "no operation"}
        if action == "list_files":
            return self.list_files(str(args.get("pattern", "**/*")), int(args.get("limit", 250)))
        if action == "read_file":
            return self.read_text(str(args["path"]))
        if action == "write_file":
            path = self.write_text(str(args["path"]), str(args.get("content", "")))
            return {"ok": True, "path": path}
        if action == "search_text":
            return self.search_text(
                str(args.get("query", "")),
                str(args.get("pattern", "**/*")),
                int(args.get("limit", 100)),
            )
        if action == "run_tests":
            return self.run_fixed([sys.executable, "-m", "unittest", "discover", "-v"])
        if action == "benchmark":
            return self.run_fixed([sys.executable, "-m", "j_agent", "--benchmark"])
        if action == "remember":
            return {"ok": True, "note": str(args.get("note", ""))[:4_000]}
        raise ValueError(f"unknown action: {action}")


class MemoryStore:
    def __init__(self, path: Path):
        self.path = path

    def append(self, event: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

    def tail(self, limit: int = 30) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                events.append(value)
        return events

    def search(self, text: str, limit: int = 10) -> list[dict[str, Any]]:
        needle = text.lower()
        found: list[dict[str, Any]] = []
        for event in reversed(self.tail(500)):
            if needle in json.dumps(event, ensure_ascii=False).lower():
                found.append(event)
                if len(found) >= limit:
                    break
        return found


def extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    candidates = [stripped]
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    candidates.extend(fenced)
    first = stripped.find("{")
    last = stripped.rfind("}")
    if 0 <= first < last:
        candidates.append(stripped[first : last + 1])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("no JSON object found")


def safe_arithmetic(expression: str) -> int | float:
    tree = ast.parse(expression, mode="eval")
    binary = {
        ast.Add: lambda a, b: a + b,
        ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: a / b,
        ast.FloorDiv: lambda a, b: a // b,
        ast.Mod: lambda a, b: a % b,
        ast.Pow: lambda a, b: a**b,
    }
    unary = {ast.UAdd: lambda a: a, ast.USub: lambda a: -a}

    def visit(node: ast.AST) -> int | float:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in binary:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and (abs(right) > 12 or abs(left) > 1_000_000):
                raise ValueError("exponent is outside safety limits")
            result = binary[type(node.op)](left, right)
            if abs(result) > 10**15:
                raise ValueError("result is outside safety limits")
            return result
        if isinstance(node, ast.UnaryOp) and type(node.op) in unary:
            return unary[type(node.op)](visit(node.operand))
        raise ValueError("unsupported arithmetic expression")

    return visit(tree)


def topological_order(nodes: Iterable[str], edges: Iterable[Iterable[str]]) -> list[str]:
    node_list = list(dict.fromkeys(str(node) for node in nodes))
    graph: dict[str, list[str]] = {node: [] for node in node_list}
    indegree: dict[str, int] = {node: 0 for node in node_list}
    for edge in edges:
        pair = list(edge)
        if len(pair) != 2:
            raise ValueError("each edge must contain two nodes")
        before, after = str(pair[0]), str(pair[1])
        for node in (before, after):
            if node not in graph:
                graph[node] = []
                indegree[node] = 0
                node_list.append(node)
        graph[before].append(after)
        indegree[after] += 1
    queue = deque(node for node in node_list if indegree[node] == 0)
    result: list[str] = []
    while queue:
        node = queue.popleft()
        result.append(node)
        for neighbor in graph[node]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)
    if len(result) != len(indegree):
        raise ValueError("dependency cycle detected")
    return result


def shortest_path(grid: list[str], start: Iterable[int], goal: Iterable[int]) -> list[list[int]]:
    if not grid or not grid[0]:
        raise ValueError("grid must not be empty")
    width = len(grid[0])
    if any(len(row) != width for row in grid):
        raise ValueError("grid must be rectangular")
    start_t = tuple(int(x) for x in start)
    goal_t = tuple(int(x) for x in goal)
    if len(start_t) != 2 or len(goal_t) != 2:
        raise ValueError("coordinates must have two integers")
    height = len(grid)

    def open_cell(point: tuple[int, int]) -> bool:
        row, col = point
        return 0 <= row < height and 0 <= col < width and grid[row][col] != "#"

    if not open_cell(start_t) or not open_cell(goal_t):
        raise ValueError("start and goal must be open cells")
    queue: deque[tuple[int, int]] = deque([start_t])
    parent: dict[tuple[int, int], tuple[int, int] | None] = {start_t: None}
    while queue:
        point = queue.popleft()
        if point == goal_t:
            break
        row, col = point
        for next_point in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
            if open_cell(next_point) and next_point not in parent:
                parent[next_point] = point
                queue.append(next_point)
    if goal_t not in parent:
        return []
    path: list[list[int]] = []
    current: tuple[int, int] | None = goal_t
    while current is not None:
        path.append([current[0], current[1]])
        current = parent[current]
    return list(reversed(path))


def normalize_text(text: str) -> str:
    return " ".join(text.casefold().split())


def json_transform(data: Any, operations: list[dict[str, Any]]) -> Any:
    value = copy.deepcopy(data)
    for operation in operations:
        name = operation.get("op")
        if name == "sort_unique":
            key = str(operation["key"])
            value[key] = sorted(set(value[key]))
        elif name == "rename":
            old, new = str(operation["from"]), str(operation["to"])
            value[new] = value.pop(old)
        elif name == "select":
            keys = [str(key) for key in operation["keys"]]
            value = {key: value[key] for key in keys if key in value}
        elif name == "count_words":
            text = str(operation.get("text", ""))
            value = dict(Counter(re.findall(r"[\w'-]+", text.casefold())))
        else:
            raise ValueError(f"unsupported transform: {name}")
    return value


def decompose_goal(goal: str) -> list[str]:
    goal = " ".join(goal.split()).strip()
    if not goal:
        raise ValueError("goal must not be empty")
    return [
        f"Define observable success criteria for: {goal}",
        "Inspect available context, constraints, tools, and prior attempts",
        "Choose the smallest reversible action likely to create evidence",
        "Execute the action and capture its result",
        "Test the result against the success criteria",
        "If the test fails, diagnose the cause and try a materially different approach",
        "Record reusable knowledge and the next unresolved sub-goal",
    ]


_ALLOWED_SKILL_IMPORTS = {
    "bisect",
    "collections",
    "dataclasses",
    "decimal",
    "fractions",
    "functools",
    "heapq",
    "itertools",
    "json",
    "math",
    "re",
    "statistics",
    "string",
    "typing",
}
_FORBIDDEN_SKILL_CALLS = {"open", "eval", "exec", "compile", "__import__", "input", "breakpoint"}


def validate_skill_source(source: str, path: Path) -> None:
    if len(source.encode("utf-8")) > MAX_SKILL_SOURCE_CHARS:
        raise SecurityError("skill source is too large")
    tree = ast.parse(source, filename=str(path))
    allowed_top_level = (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign, ast.FunctionDef)
    dangerous_names = {
        "open", "eval", "exec", "compile", "__import__", "input", "breakpoint",
        "globals", "locals", "vars", "dir", "getattr", "setattr", "delattr",
        "help", "exit", "quit",
    }
    for index, statement in enumerate(tree.body):
        if (
            index == 0
            and isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str)
        ):
            continue
        if not isinstance(statement, allowed_top_level):
            raise SecurityError(f"skill top-level statement is not allowed: {type(statement).__name__}")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in _ALLOWED_SKILL_IMPORTS:
                    raise SecurityError(f"skill import is not allowed: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")[0]
            if module not in _ALLOWED_SKILL_IMPORTS:
                raise SecurityError(f"skill import is not allowed: {node.module}")
        elif isinstance(node, ast.Name) and node.id in dangerous_names:
            raise SecurityError(f"skill name is not allowed: {node.id}")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise SecurityError("dunder attribute access is not allowed in skills")
        elif isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef, ast.With, ast.AsyncWith)):
            raise SecurityError(f"skill construct is not allowed: {type(node).__name__}")


def load_skills(root: Path = ROOT) -> list[Any]:
    directory = root / "skills"
    if not directory.exists():
        return []
    modules: list[Any] = []
    for path in sorted(directory.glob("*.py")):
        if path.name.startswith("_"):
            continue
        source = path.read_text(encoding="utf-8", errors="strict")
        validate_skill_source(source, path)
        spec = importlib.util.spec_from_file_location(f"j_skill_{path.stem}", path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if callable(getattr(module, "can_handle", None)) and callable(getattr(module, "solve", None)):
            modules.append(module)
    return modules


def solve_task(task: dict[str, Any], root: Path = ROOT) -> Any:
    kind = str(task.get("kind", ""))
    if kind == "arithmetic":
        return safe_arithmetic(str(task["expression"]))
    if kind == "topological_order":
        return topological_order(task.get("nodes", []), task.get("edges", []))
    if kind == "shortest_path":
        return shortest_path(task["grid"], task["start"], task["goal"])
    if kind == "normalize_text":
        return normalize_text(str(task["text"]))
    if kind == "json_transform":
        return json_transform(task.get("data"), task.get("operations", []))
    if kind == "decompose_goal":
        return decompose_goal(str(task["goal"]))
    errors: list[str] = []
    for skill in load_skills(root):
        try:
            if skill.can_handle(task):
                return skill.solve(copy.deepcopy(task))
        except Exception as exc:  # A broken plugin must not stop alternative plugins.
            errors.append(f"{getattr(skill, 'SKILL_NAME', skill.__name__)}: {type(exc).__name__}: {exc}")
    suffix = f" Plugin errors: {'; '.join(errors)}" if errors else ""
    raise UnsupportedTask(f"unsupported task kind: {kind}.{suffix}")


class OfflinePlanner:
    name = "offline-bootstrap"

    @staticmethod
    def _latest(history: list[dict[str, Any]], action: str) -> dict[str, Any] | None:
        for item in reversed(history):
            if item.get("decision", {}).get("action") == action:
                return item
        return None

    def decide(self, context: dict[str, Any]) -> Decision:
        history = context.get("history", [])
        completed = [item.get("decision", {}).get("action") for item in history]
        if "list_files" not in completed:
            return Decision("continue", "Inventory the repository before acting.", "list_files", {"limit": 200})
        if "read_file" not in completed and "README.md" in context.get("files", []):
            return Decision("continue", "Read the project contract and current status.", "read_file", {"path": "README.md"})
        if "run_tests" not in completed:
            return Decision("continue", "Establish a correctness baseline.", "run_tests", {})

        test_event = self._latest(history, "run_tests") or {}
        test_result = test_event.get("result", {})
        if int(test_result.get("returncode", 1)) != 0:
            if "search_text" not in completed:
                return Decision(
                    "continue",
                    "Tests failed; inspect explicit failure markers before changing strategy.",
                    "search_text",
                    {"query": "FAILED", "pattern": "reports/**/*"},
                    "Repair the first reproducible test failure",
                )
            return Decision(
                "blocked",
                "Credential-free diagnostics found a failing acceptance test and cannot safely invent a repair.",
                "remember",
                {"note": str(test_result.get("output", ""))[-4_000:]},
                "Repair the first reproducible test failure",
            )

        if "benchmark" not in completed:
            return Decision("continue", "Measure the current proxy capabilities.", "benchmark", {})
        benchmark_event = self._latest(history, "benchmark") or {}
        benchmark_result = benchmark_event.get("result", {})
        if int(benchmark_result.get("returncode", 1)) != 0:
            return Decision(
                "blocked",
                "The critical benchmark suite failed; preserve the evidence and try a different repair route.",
                "remember",
                {"note": str(benchmark_result.get("output", ""))[-4_000:]},
                "Repair the first critical benchmark failure",
            )

        if "write_file" not in completed:
            summary = {
                "provider": self.name,
                "goal": context.get("goal"),
                "claim": "bounded bootstrap validation passed; this is not evidence of human-level AGI",
                "tests": test_result,
                "benchmark": benchmark_result,
            }
            body = "# J offline iteration\n\n```json\n" + json.dumps(summary, ensure_ascii=False, indent=2) + "\n```\n"
            return Decision(
                "continue",
                "Persist transparent evidence instead of equating an internal score with AGI.",
                "write_file",
                {"path": "reports/offline-latest.md", "content": body},
            )
        return Decision(
            "done",
            "The credential-free bootstrap cycle passed its tests and critical proxy benchmarks.",
            "none",
            {},
            str(context.get("goal", "")),
        )


class OpenAIPlanner:
    name = "openai"

    def __init__(self, model: str = DEFAULT_MODEL):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("install the optional 'openai' dependency") from exc
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def decide(self, context: dict[str, Any]) -> Decision:
        system = (
            "You are J's bounded planning component. Improve general problem-solving toward the supplied goal, "
            "but never claim AGI from an internal score. Work only through the listed repository-confined tools. "
            "Do not request arbitrary shell execution. When blocked, propose and try a materially different route. "
            "Return one strict JSON object with keys status, summary, action, args, next_goal. "
            "status: continue|done|blocked. action: none|list_files|read_file|write_file|search_text|run_tests|benchmark|remember. "
            "Writes are limited to skills, tests/generated, docs, state, reports, and workspace. "
            "summary must be a concise reasoning summary, not private chain-of-thought."
        )
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
            ],
        )
        return Decision.from_mapping(extract_json(response.output_text))


class Agent:
    def __init__(self, root: Path = ROOT, provider: str = "auto"):
        self.sandbox = Sandbox(root)
        self.memory = MemoryStore(root / "state" / "memory.jsonl")
        self.provider_name = provider
        self.planner: Planner = self._make_planner(provider)

    @staticmethod
    def _make_planner(provider: str) -> Planner:
        if provider == "offline":
            return OfflinePlanner()
        if provider == "openai":
            return OpenAIPlanner()
        if provider != "auto":
            raise ValueError(f"unknown provider: {provider}")
        try:
            return OpenAIPlanner()
        except Exception:
            return OfflinePlanner()

    def run(self, goal: str, max_steps: int = DEFAULT_MAX_STEPS) -> dict[str, Any]:
        goal = " ".join(goal.split()).strip()
        if not goal:
            raise ValueError("goal must not be empty")
        history: list[dict[str, Any]] = []
        signatures: Counter[str] = Counter()
        for step in range(max(1, max_steps)):
            context = {
                "goal": goal,
                "step": step,
                "provider": self.planner.name,
                "files": self.sandbox.list_files(limit=200),
                "memory": self.memory.tail(20),
                "history": history[-8:],
                "tools": [
                    "list_files",
                    "read_file",
                    "write_file",
                    "search_text",
                    "run_tests",
                    "benchmark",
                    "remember",
                    "none",
                ],
            }
            try:
                decision = self.planner.decide(context)
            except Exception as exc:
                if not isinstance(self.planner, OfflinePlanner):
                    failure = {
                        "ts": time.time(),
                        "goal": goal,
                        "provider": self.planner.name,
                        "error": f"{type(exc).__name__}: {exc}",
                        "recovery": "switch_to_offline_bootstrap",
                    }
                    self.memory.append(failure)
                    history.append(failure)
                    self.planner = OfflinePlanner()
                    continue
                raise
            if decision.status == "done":
                event = {
                    "ts": time.time(),
                    "goal": goal,
                    "provider": self.planner.name,
                    "decision": asdict(decision),
                    "result": {"ok": True, "message": "planner marked this bounded iteration complete"},
                }
                self.memory.append(event)
                history.append(event)
                return {
                    "status": "done",
                    "provider": self.planner.name,
                    "goal": goal,
                    "steps": len(history),
                    "summary": decision.summary,
                }
            if decision.status == "blocked":
                decision = Decision(
                    status="continue",
                    summary=f"Blocked route detected; record it and attempt an alternative. {decision.summary}",
                    action="remember",
                    args={"note": decision.summary},
                    next_goal=decision.next_goal or f"Find a materially different approach to: {goal}",
                )
            signature = json.dumps(
                {"action": decision.action, "args": decision.args or {}, "goal": goal},
                ensure_ascii=False,
                sort_keys=True,
            )
            signatures[signature] += 1
            if signatures[signature] >= 3:
                decision = Decision(
                    status="continue",
                    summary="Repeated route detected; switch to repository inspection.",
                    action="search_text",
                    args={"query": "TODO", "pattern": "**/*"},
                    next_goal=f"Break the stalled loop while pursuing: {goal}",
                )
            try:
                result = self.sandbox.execute(decision.action, decision.args or {})
            except Exception as exc:
                result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
            event = {
                "ts": time.time(),
                "goal": goal,
                "provider": self.planner.name,
                "decision": asdict(decision),
                "result": result,
            }
            self.memory.append(event)
            history.append(event)
            if decision.next_goal:
                goal = decision.next_goal
        return {
            "status": "continue",
            "provider": self.planner.name,
            "goal": goal,
            "steps": len(history),
            "reason": "bounded step budget exhausted; persist state and continue in a later iteration",
        }


def doctor(root: Path = ROOT) -> dict[str, Any]:
    sandbox = Sandbox(root)
    return {
        "root": str(sandbox.root),
        "python": sys.version.split()[0],
        "openai_key_configured": bool(os.getenv("OPENAI_API_KEY")),
        "openai_sdk_available": importlib.util.find_spec("openai") is not None,
        "copilot_cli_available": shutil.which("copilot") is not None,
        "files": len(sandbox.list_files(limit=1_000)),
        "write_scope": list(ALLOWED_WRITE_PATHS),
        "protected_scope": list(PROTECTED_WRITE_PATHS),
    }


def benchmark_cli() -> int:
    from benchmarks import run_benchmarks

    report = run_benchmarks(ROOT)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["critical_passed"] else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="J: bounded general problem-solving research agent")
    parser.add_argument("--goal", help="goal for one bounded agent iteration")
    parser.add_argument("--provider", choices=["auto", "openai", "offline"], default="auto")
    parser.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS)
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--doctor", action="store_true")
    parser.add_argument("--solve-json", help="solve one JSON task")
    args = parser.parse_args(argv)

    if args.benchmark:
        return benchmark_cli()
    if args.doctor:
        print(json.dumps(doctor(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.solve_json:
        task = json.loads(args.solve_json)
        print(json.dumps({"result": solve_task(task)}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if not args.goal:
        parser.error("--goal is required unless --benchmark, --doctor, or --solve-json is used")
    result = Agent(ROOT, provider=args.provider).run(args.goal, max_steps=args.max_steps)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("status") == "done" else 2


if __name__ == "__main__":
    raise SystemExit(main())
