"""Evaluator-controlled Unix-socket tool broker for isolated candidates.

Candidate containers keep IP networking disabled. They may connect only to this
AF_UNIX endpoint, whose allowed tools, request budget, timeouts and output sizes
are evaluator controlled. The protocol is newline-delimited JSON. Additional
handlers can be evaluator-owned isolated providers; their implementation and
credentials never cross the candidate boundary.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import socket
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

MAX_LINE_BYTES = 256 * 1024
MAX_RESULT_BYTES = 512 * 1024
ToolHandler = Callable[[Any, dict[str, Any]], Any]


class PolicyViolation(Exception):
    pass


def _safe_calc(expr: str) -> int | float:
    if not isinstance(expr, str) or len(expr) > 1000:
        raise PolicyViolation("calculator expression must be <=1000 chars")
    tree = ast.parse(expr, mode="eval")

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = ev(node.operand)
            return +value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)):
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Pow):
                if abs(right) > 12 or abs(left) > 10**12:
                    raise PolicyViolation("calculator exponent/magnitude limit")
                value = left ** right
            elif isinstance(node.op, ast.Add):
                value = left + right
            elif isinstance(node.op, ast.Sub):
                value = left - right
            elif isinstance(node.op, ast.Mult):
                value = left * right
            elif isinstance(node.op, ast.Div):
                value = left / right
            elif isinstance(node.op, ast.FloorDiv):
                value = left // right
            else:
                value = left % right
            if isinstance(value, complex) or abs(value) > 10**100:
                raise PolicyViolation("calculator result magnitude limit")
            return value
        raise PolicyViolation(f"calculator syntax not allowed: {type(node).__name__}")

    return ev(tree)


def builtin_calculator(args: Any, state: dict[str, Any]) -> Any:
    if not isinstance(args, dict) or set(args) != {"expression"}:
        raise PolicyViolation("calculator args must be {expression}")
    return {"value": _safe_calc(args["expression"])}


def builtin_kv_get(args: Any, state: dict[str, Any]) -> Any:
    if not isinstance(args, dict) or set(args) != {"key"} or not isinstance(args["key"], str):
        raise PolicyViolation("kv.get args must be {key:string}")
    return {"found": args["key"] in state, "value": state.get(args["key"])}


def builtin_kv_put(args: Any, state: dict[str, Any]) -> Any:
    if not isinstance(args, dict) or set(args) != {"key", "value"} or not isinstance(args["key"], str):
        raise PolicyViolation("kv.put args must be {key:string,value:any}")
    if len(args["key"]) > 200:
        raise PolicyViolation("kv key too long")
    encoded = json.dumps(args["value"], ensure_ascii=False)
    if len(encoded.encode()) > 64 * 1024:
        raise PolicyViolation("kv value too large")
    state[args["key"]] = args["value"]
    return {"stored": True}


BUILTINS: dict[str, ToolHandler] = {
    "calculator": builtin_calculator,
    "kv.get": builtin_kv_get,
    "kv.put": builtin_kv_put,
}


@dataclass
class BrokerPolicy:
    allowed_tools: set[str]
    max_requests: int = 100
    max_wall_s: float = 300.0
    max_result_bytes: int = MAX_RESULT_BYTES
    cost_per_call: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_public(cls, arena: dict, *, extra_tools: set[str] | None = None) -> "BrokerPolicy":
        cfg = (arena or {}).get("broker") or {}
        tools = cfg.get("tools", [])
        if not isinstance(tools, list) or not all(isinstance(x, str) for x in tools):
            raise ValueError("arena.broker.tools must be a list of strings")
        supported = set(BUILTINS) | set(extra_tools or set())
        unknown = sorted(set(tools) - supported)
        if unknown:
            raise ValueError(f"unsupported broker tools: {unknown}")
        max_requests = int(cfg.get("max_requests", 100))
        max_wall_s = float(cfg.get("max_wall_s", 300.0))
        max_result_bytes = int(cfg.get("max_result_bytes", MAX_RESULT_BYTES))
        raw_costs = cfg.get("cost_per_call") or {}
        if not isinstance(raw_costs, dict):
            raise ValueError("broker cost_per_call must be a mapping")
        costs: dict[str, float] = {}
        for name, raw in raw_costs.items():
            if name not in set(tools):
                raise ValueError(f"cost declared for unavailable tool {name}")
            value = float(raw)
            if value < 0 or value > 1_000_000:
                raise ValueError(f"invalid broker cost for {name}")
            costs[str(name)] = value
        if not (0 < max_requests <= 10_000):
            raise ValueError("broker max_requests outside (0,10000]")
        if not (0 < max_wall_s <= 86_400):
            raise ValueError("broker max_wall_s outside (0,86400]")
        if not (0 < max_result_bytes <= 10 * 1024 * 1024):
            raise ValueError("broker max_result_bytes outside allowed range")
        return cls(set(tools), max_requests, max_wall_s, max_result_bytes, costs)


@dataclass
class BrokerServer:
    socket_path: Path
    policy: BrokerPolicy
    handlers: dict[str, ToolHandler] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)
    _server: socket.socket | None = field(default=None, init=False, repr=False)
    _thread: threading.Thread | None = field(default=None, init=False, repr=False)
    _stop: threading.Event = field(default_factory=threading.Event, init=False, repr=False)
    _started: float = field(default=0.0, init=False, repr=False)
    _count: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        overlap = set(self.handlers) & set(BUILTINS)
        if overlap:
            raise ValueError(f"external handlers cannot replace built-ins: {sorted(overlap)}")
        missing = self.policy.allowed_tools - (set(BUILTINS) | set(self.handlers))
        if missing:
            raise ValueError(f"policy references missing handlers: {sorted(missing)}")

    def start(self) -> None:
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        if self.socket_path.exists() or self.socket_path.is_symlink():
            self.socket_path.unlink()
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(str(self.socket_path))
        os.chmod(self.socket_path, 0o666)
        srv.listen(16)
        srv.settimeout(0.2)
        self._server = srv
        self._started = time.monotonic()
        self._thread = threading.Thread(target=self._serve, name="agi-eval-broker", daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        if self._server is not None:
            try:
                self._server.close()
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=2)
        try:
            self.socket_path.unlink()
        except FileNotFoundError:
            pass

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def _log(self, *, request: Any, response: Any, violation: bool, elapsed_s: float, cost: float) -> None:
        payload = json.dumps({"request": request, "response": response}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.events.append({
            "seq": len(self.events),
            "tool": request.get("tool") if isinstance(request, dict) else None,
            "request_id": request.get("id") if isinstance(request, dict) else None,
            "violation": violation,
            "elapsed_s": elapsed_s,
            "cost": cost,
            "exchange_sha256": hashlib.sha256(payload.encode()).hexdigest(),
        })

    def _handle(self, req: Any) -> dict[str, Any]:
        started = time.monotonic()
        violation = False
        tool: str | None = None
        cost = 0.0
        try:
            if time.monotonic() - self._started > self.policy.max_wall_s:
                raise PolicyViolation("broker wall-clock budget exhausted")
            if self._count >= self.policy.max_requests:
                raise PolicyViolation("broker request budget exhausted")
            self._count += 1
            if not isinstance(req, dict) or not isinstance(req.get("id"), (str, int)) or not isinstance(req.get("tool"), str):
                raise PolicyViolation("request must include id and tool")
            tool = req["tool"]
            if tool not in self.policy.allowed_tools:
                raise PolicyViolation(f"tool not allowed: {tool}")
            handler = self.handlers.get(tool) or BUILTINS.get(tool)
            if handler is None:
                raise PolicyViolation(f"tool handler unavailable: {tool}")
            result = handler(req.get("args"), self.state)
            encoded = json.dumps(result, ensure_ascii=False).encode()
            if len(encoded) > self.policy.max_result_bytes:
                raise PolicyViolation("tool result exceeds output limit")
            cost = float(self.policy.cost_per_call.get(tool, 0.0))
            resp = {"id": req["id"], "ok": True, "result": result}
        except Exception as e:
            violation = isinstance(e, PolicyViolation)
            resp = {
                "id": req.get("id") if isinstance(req, dict) else None,
                "ok": False,
                "error": type(e).__name__,
                "detail": str(e),
            }
        self._log(request=req, response=resp, violation=violation, elapsed_s=time.monotonic() - started, cost=cost)
        return resp

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self._server.accept() if self._server is not None else (None, None)
            except (socket.timeout, OSError):
                continue
            if conn is None:
                continue
            with conn:
                f = conn.makefile("rwb")
                while not self._stop.is_set():
                    line = f.readline(MAX_LINE_BYTES + 1)
                    if not line:
                        break
                    if len(line) > MAX_LINE_BYTES:
                        resp = {"id": None, "ok": False, "error": "PolicyViolation", "detail": "request line too large"}
                    else:
                        try:
                            req = json.loads(line)
                        except json.JSONDecodeError:
                            req = {"id": None, "tool": None, "args": None}
                            resp = {"id": None, "ok": False, "error": "PolicyViolation", "detail": "invalid JSON"}
                            self._log(request=req, response=resp, violation=True, elapsed_s=0.0, cost=0.0)
                            f.write(json.dumps(resp).encode() + b"\n")
                            f.flush()
                            continue
                        resp = self._handle(req)
                    f.write(json.dumps(resp, ensure_ascii=False).encode() + b"\n")
                    f.flush()


def broker_call(socket_path: Path, request: dict[str, Any], timeout_s: float = 5.0) -> dict[str, Any]:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(timeout_s)
        s.connect(str(socket_path))
        s.sendall(json.dumps(request, ensure_ascii=False).encode() + b"\n")
        f = s.makefile("rb")
        line = f.readline(MAX_LINE_BYTES + 1)
        if not line:
            raise RuntimeError("broker closed without response")
        return json.loads(line)
