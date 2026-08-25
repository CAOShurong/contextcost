#!/usr/bin/env python3
"""product_lock.py — independent lock for the product-dev agent track.

Deliberately separate from github-sources-program/scripts/loop_lock.py so the
product agent is never starved by the PR-main / identity agents that share the
main loop lock. Same heartbeat + stale-takeover contract.

Usage:
  python product_lock.py acquire   -> exit 0 if acquired, 2 if already held
  python product_lock.py release   -> release if holder
  python product_lock.py status    -> JSON status line
"""
import json
import os
import sys
import time

LOCK_PATH = r"E:\Codex\Scratch\product_lock.lock"
STALE_MIN = 12.0
HEARTBEAT_PATH = r"E:\Codex\Scratch\product_lock.heartbeat"


def _now():
    return time.time()


def _read():
    if not os.path.exists(LOCK_PATH):
        return None
    try:
        with open(LOCK_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def acquire():
    now = _now()
    cur = _read()
    if cur:
        age = (now - cur.get("heartbeat", 0)) / 60.0
        if age < STALE_MIN:
            # still alive — refuse
            print(json.dumps({"acquired": False, "holder_pid": cur.get("pid"),
                              "heartbeat_age_min": round(age, 1), "stale": False}))
            return 2
        # stale — take over
        took_from = cur.get("pid")
    else:
        took_from = None
    state = {
        "locked": True,
        "holder_pid": os.getpid(),
        "host": os.environ.get("COMPUTERNAME", "unknown"),
        "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "heartbeat": now,
        "took_over_from": took_from,
    }
    with open(LOCK_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f)
    print(json.dumps({"acquired": True, "took_over_from": took_from,
                      "heartbeat_age_min": 0.0, "stale": False}))
    return 0


def release():
    cur = _read()
    if cur and cur.get("holder_pid") == os.getpid():
        try:
            os.remove(LOCK_PATH)
        except OSError:
            pass
        print(json.dumps({"released": True, "pid": os.getpid()}))
        return 0
    print(json.dumps({"released": False, "holder_pid": cur.get("pid") if cur else None}))
    return 1


def status():
    cur = _read()
    if not cur:
        print(json.dumps({"locked": False}))
        return
    age = (_now() - cur.get("heartbeat", 0)) / 60.0
    print(json.dumps({"locked": True, "holder_pid": cur.get("pid"),
                      "heartbeat_age_min": round(age, 1),
                      "stale": age >= STALE_MIN,
                      "took_over_from": cur.get("took_over_from")}))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    rc = {"acquire": acquire, "release": release, "status": status}.get(cmd, status)()
    sys.exit(rc if isinstance(rc, int) else 0)
