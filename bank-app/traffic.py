"""Send random requests to the bank app so the graphs have something to show.

Run:  python traffic.py                  (targets http://127.0.0.1:5000)
      python traffic.py http://HOST:5000
Stop with Ctrl+C.
"""
import json
import random
import sys
import time
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"
NAMES = ["alice", "bob", "carol", "dave"]  # dave does not exist -> 404


def call(path, body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except urllib.error.URLError:
        return "down"


while True:
    action = random.choice(["balance", "balance", "deposit", "withdraw"])
    name = random.choice(NAMES)
    if action == "balance":
        status = call(f"/balance/{name}")
    else:
        status = call(f"/{action}", {"account": name, "amount": random.randint(10, 400)})
    print(action, name, status, flush=True)
    time.sleep(0.2)
