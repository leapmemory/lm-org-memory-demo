"""The forwarder. This is the file you copy.

Your app already receives messages: a Slack event, a webhook, a chat UI, a
support ticket. Wherever that happens, forward each message to LM as a turn
with the speaker's id. That is the whole integration.

Two calls in (turns, briefing), one call out (recall). No memory logic lives
in your code.

Run it here to add memories live:

    python3 forward.py
    mike: we are moving the search index to opensearch next quarter
    sarah: Northwind asked for SSO again on today's call

Then ask about it:

    python3 ask.py "what did mike say about search?"

Or pipe a file of the same "speaker: message" lines:

    cat notes.txt | python3 forward.py
"""

import json
import os
import sys
import urllib.request


# ─── The part you copy ────────────────────────────────────────────

def save_turn(tenant_id, speaker_id, content, role="user"):
    """Save one message to the company's memory.

    speaker_id is the whole trick: it is what makes "who decided this, and
    why" answerable months later. Use a stable id per person (the Slack user
    id, the email local part, your own user id), not a display name.

    Returns immediately. Extraction runs in the background, so this never
    blocks the conversation your user is having.
    """
    return api("POST", f"/v1/tenants/{tenant_id}/turns", {
        "role": role,
        "speaker_id": speaker_id,
        "content": content,
    })


# ─── Demo plumbing below ──────────────────────────────────────────

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


def parse(line):
    """'mike: we chose postgres' -> ('mike', 'we chose postgres')"""
    if ":" not in line:
        return None, None
    speaker, content = line.split(":", 1)
    speaker = speaker.strip().lower()
    content = content.strip()
    if not speaker or not content or " " in speaker:
        return None, None
    return speaker, content


def main():
    t = tenant()
    interactive = sys.stdin.isatty()
    if interactive:
        print(f"forwarding into {t}. format: speaker: message. ctrl-d to stop.\n")

    saved = 0
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        speaker, content = parse(line)
        if speaker is None:
            print("  skipped, expected 'speaker: message'")
            continue

        r = save_turn(t, speaker, content)
        if not r["success"]:
            sys.exit(f"{r['code']}: {r['message']}")
        saved += 1
        if interactive:
            print(f"  saved as {speaker}, digesting in the background\n")

    print(f"\n{saved} turn(s) forwarded into {t}")
    if saved and interactive:
        print("give it a few seconds, then: python3 ask.py \"...\"")


if __name__ == "__main__":
    main()