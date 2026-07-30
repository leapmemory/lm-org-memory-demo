import json
import os
import sys
import urllib.request

def env(key):
    if os.path.exists(".env"):
        for line in open(".env"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    val = os.environ.get(key)
    if not val:
        sys.exit(f"missing {key}, copy .env.example to .env and fill it")
    return val

def api(method, path, body=None):
    req = urllib.request.Request(
        env("LM_API_URL") + path,
        data=json.dumps(body).encode() if body else None,
        headers={
            "Authorization": "Bearer " + env("LM_API_KEY"),
            "Content-Type": "application/json",
            "User-Agent": "lm-org-memory-demo/1.0",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            sys.exit(f"http {e.code}, non-json body:\n{raw[:500]}")

def tenant():
    if not os.path.exists(".demo_tenant"):
        sys.exit("no .demo_tenant, run create_org.py first")
    return open(".demo_tenant").read().strip()

def main():
    if len(sys.argv) < 2:
        sys.exit('usage: python3 ask.py "why did we choose postgres?"')
    query = sys.argv[1]
    r = api("POST", f"/v1/tenants/{tenant()}/recall", {"query": query})
    if not r["success"]:
        sys.exit(f"{r['code']}: {r['message']}")
    d = r["data"]

    print(f"\nQ: {query}\n")
    if d["facts"]:
        print("what the company knows:")
        for f in d["facts"][:5]:
            print(f"  - {f['sentence']}")
    if d["chunks"]:
        print("\nwho said it, word for word:")
        for c in d["chunks"][:3]:
            print(f"  [{c['speaker_id']}] {c['content']}")
    if not d["facts"] and not d["chunks"]:
        print("no memories found")

if __name__ == "__main__":
    main()