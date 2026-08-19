import json, sys
req = json.load(sys.stdin)
prompt = str(req.get("prompt", ""))
marker = "Return token:"
answer = prompt.split(marker, 1)[1].strip() if marker in prompt else ""
json.dump({"answer": answer}, sys.stdout)
