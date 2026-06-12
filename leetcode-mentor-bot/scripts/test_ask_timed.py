"""Benchmark /ask latency."""

import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    payload = {"mode": "hint", "problem_slug": "two-sum"}
    data = json.dumps(payload).encode()

    for i in range(1, 3):
        req = urllib.request.Request(
            "http://127.0.0.1:8000/ask",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        start = time.perf_counter()
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
        elapsed = time.perf_counter() - start
        print(f"Request {i}: {elapsed:.2f}s — {len(result['answer'])} chars")


if __name__ == "__main__":
    main()
