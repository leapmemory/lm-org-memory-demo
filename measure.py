"""How many memories does a person generate per day?

The number every org revenue estimate depends on, and the one number nobody
has measured. Reads a turns .jsonl (the demo corpus, or your own exported
history) and reports turns per speaker per active day.

One turn = one saved memory = one billed unit, so this is also the cost model.

Usage:
    python3 measure.py                          # the demo corpus
    python3 measure.py real/my_export.jsonl     # your own history
"""
import json
import os
import sys
import urllib.request
from collections import defaultdict

PRICE_PER_MEMORY = 0.05   # developer rate, USD. Recall and briefing are free.
WORKDAYS_PER_MONTH = 21


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


def api(method, path):
    req = urllib.request.Request(
        env("LM_API_URL") + path,
        headers={
            "Authorization": "Bearer " + env("LM_API_KEY"),
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


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "corpus/ridgeline_30.jsonl"
    turns = [json.loads(line) for line in open(path) if line.strip()]
    if not turns:
        sys.exit(f"{path} is empty")

    by_speaker = defaultdict(lambda: defaultdict(int))
    undated = 0
    for t in turns:
        speaker = t.get("speaker_id") or t.get("role") or "unknown"
        ts = t.get("ts")
        if not ts:
            undated += 1
            continue
        by_speaker[speaker][ts[:10]] += 1

    if not by_speaker:
        sys.exit("no turns carry a ts, cannot measure per-day rates")

    all_days = sorted({d for days in by_speaker.values() for d in days})
    print(f"\n{path}: {len(turns)} turns, {len(by_speaker)} speakers")
    print(f"span: {all_days[0]} to {all_days[-1]}, {len(all_days)} active days")
    if undated:
        print(f"note: {undated} turns had no ts and were skipped")

    print(f"\n{'speaker':<16}{'turns':>8}{'days':>8}{'per active day':>18}")
    rates = []
    for speaker in sorted(by_speaker, key=lambda s: -sum(by_speaker[s].values())):
        days = by_speaker[speaker]
        total = sum(days.values())
        rate = total / len(days)
        rates.append(rate)
        print(f"{speaker:<16}{total:>8}{len(days):>8}{rate:>18.1f}")

    avg = sum(rates) / len(rates)
    monthly_per_person = avg * WORKDAYS_PER_MONTH
    print(f"\nmemories per person per active day: {avg:.1f}")
    print(f"projected per person per month ({WORKDAYS_PER_MONTH} workdays): "
          f"{monthly_per_person:.0f}")
    print(f"cost per person per month at ${PRICE_PER_MEMORY:.2f}: "
          f"${monthly_per_person * PRICE_PER_MEMORY:.2f}")
    for people in (10, 50, 200):
        m = monthly_per_person * people
        print(f"  {people:>3} people: {m:>8.0f} memories/mo, "
              f"${m * PRICE_PER_MEMORY:>8.2f}/mo")

    if len(turns) < 200 or len(all_days) < 5:
        print("\nSMALL SAMPLE. This corpus is a demo, not a usage measurement.")
        print("Run this against real forwarded traffic for a number you can trust.")

    if os.path.exists(".demo_tenant"):
        t = open(".demo_tenant").read().strip()
        s = api("GET", f"/v1/tenants/{t}/turns/status")
        if s["success"]:
            d = s["data"]
            print(f"\ntenant {t}: {d['indexed']}/{d['total']} indexed, "
                  f"{d['failed']} failed")


if __name__ == "__main__":
    main()