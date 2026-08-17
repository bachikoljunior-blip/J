import argparse, json, os, subprocess, sys, time
from pathlib import Path
from openai import OpenAI

MODEL = os.getenv("J_MODEL", "gpt-5")
MEMORY = Path("memory.jsonl")
MAX_STEPS = int(os.getenv("J_MAX_STEPS", "20"))

SYSTEM = '''You are J, an autonomous generalist agent. Pursue the user's goal safely and efficiently. At each step return strict JSON with keys: status, thought_summary, action, args, result_assessment, next_goal. status is one of continue, done, blocked. action is one of shell, python, read, write, none. Prefer reversible actions. Never modify anything outside the current repository. If blocked, devise another approach before giving up.'''

def remember(event):
    with MEMORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

def load_memory(limit=30):
    if not MEMORY.exists(): return []
    lines = MEMORY.read_text(encoding="utf-8").splitlines()[-limit:]
    out=[]
    for x in lines:
        try: out.append(json.loads(x))
        except Exception: pass
    return out

def safe_path(p):
    root=Path.cwd().resolve(); q=(root/p).resolve()
    if root not in q.parents and q != root: raise ValueError("path escapes repository")
    return q

def execute(action, args):
    if action == "none": return "no-op"
    if action == "read": return safe_path(args["path"]).read_text(encoding="utf-8")[:12000]
    if action == "write":
        q=safe_path(args["path"]); q.parent.mkdir(parents=True, exist_ok=True); q.write_text(args.get("content", ""), encoding="utf-8"); return f"wrote {q}"
    if action == "python":
        cp=subprocess.run([sys.executable,"-c",args["code"]],cwd=Path.cwd(),capture_output=True,text=True,timeout=60); return (cp.stdout+cp.stderr)[-12000:]
    if action == "shell":
        cmd=args["cmd"]
        banned=["rm -rf /","mkfs","shutdown","reboot",":(){:|:&};:"]
        if any(x in cmd for x in banned): raise ValueError("unsafe command")
        cp=subprocess.run(cmd,shell=True,cwd=Path.cwd(),capture_output=True,text=True,timeout=120); return (cp.stdout+cp.stderr)[-12000:]
    raise ValueError(action)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--goal", required=True); ns=ap.parse_args()
    client=OpenAI()
    goal=ns.goal; history=[]
    for step in range(MAX_STEPS):
        payload={"goal":goal,"step":step,"memory":load_memory(),"history":history[-8:]}
        r=client.responses.create(model=MODEL,input=[{"role":"system","content":SYSTEM},{"role":"user","content":json.dumps(payload,ensure_ascii=False)}])
        text=r.output_text.strip()
        try: decision=json.loads(text)
        except Exception:
            decision={"status":"continue","thought_summary":"model returned non-JSON; recover","action":"none","args":{},"result_assessment":text[:1000],"next_goal":goal}
        if decision.get("status") == "done":
            remember({"goal":goal,"status":"done","decision":decision,"ts":time.time()}); print(json.dumps(decision,ensure_ascii=False,indent=2)); return
        if decision.get("status") == "blocked":
            decision["status"]="continue"; decision["next_goal"]="Find an alternative route to accomplish: "+goal
        try: result=execute(decision.get("action","none"), decision.get("args",{}))
        except Exception as e: result=f"ERROR: {type(e).__name__}: {e}"
        event={"goal":goal,"decision":decision,"result":result,"ts":time.time()}; remember(event); history.append(event)
        goal=decision.get("next_goal") or goal
    print(json.dumps({"status":"blocked","reason":"step limit reached","goal":goal},ensure_ascii=False,indent=2))

if __name__ == "__main__": main()
