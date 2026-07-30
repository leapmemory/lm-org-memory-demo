import json
import os
import sys
import time
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
    path = sys.argv[1] if len(sys.argv) > 1 else "corpus/ridgeline_30.jsonl"
    t = tenant()
    turns = [json.loads(line) for line in open(path) if line.strip()]
    print(f"importing {len(turns)} turns into {t}")

    for i in range(0, len(turns), 100):
        batch = turns[i:i + 100]
        r = api("POST", f"/v1/tenants/{t}/turns/batch", {"turns": batch})
        if not r["success"]:
            sys.exit(f"{r['code']}: {r['message']}")
        print(f"  batch {i // 100 + 1}: {r['data']['count']} accepted")

    print("digesting", end="", flush=True)
    while True:
        s = api("GET", f"/v1/tenants/{t}/turns/status")["data"]
        if s["indexed"] == s["total"]:
            print(f"\ndone: {s['indexed']}/{s['total']} indexed")
            break
        if s["failed"] > 0 and s["pending"] == 0:
            sys.exit(f"\n{s['failed']} turns failed: {s['failed_ids']}")
        print(".", end="", flush=True)
        time.sleep(3)

if __name__ == "__main__":
    main()