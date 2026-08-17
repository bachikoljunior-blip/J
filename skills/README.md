# Skills

A generated skill is one `.py` file with:

```python
SKILL_NAME = "example"

def can_handle(task):
    return task.get("kind") == "example"

def solve(task):
    return {"answer": task.get("value")}
```

J validates the source before loading it. Skills may use only the allowlisted standard-library modules in `j_agent.py`; core files and fixed tests remain protected.
