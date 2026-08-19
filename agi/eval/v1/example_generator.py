"""Development-only deterministic fresh-task generator."""
import json, random, sys

req = json.loads(sys.stdin.read())
rng = random.Random(req["seed"])
a, b = rng.randint(10, 99), rng.randint(10, 99)
answer = str(a * b)
out = {
    "public": {"prompt": f"Return only the integer result of {a}*{b}.", "budget": {"wall_s": 10}, "development_only": True},
    "private": {"grader": {"type": "exact_match", "expected": answer}},
}
json.dump(out, sys.stdout)
