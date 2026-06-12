"""Test /ask endpoint with Groq API."""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    payload = {"mode": "hint", "problem_slug": "two-sum"}
    req = urllib.request.Request(
        "http://127.0.0.1:8000/ask",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        print(f"FAILED status={exc.code}")
        print(exc.read().decode())
        sys.exit(1)

    print("SUCCESS - Groq /ask response:")
    print(f"  mode:   {data['mode']}")
    print(f"  problem: {data['problem_title']} ({data['problem_slug']})")
    print(f"  sources: {data['sources']}")
    print()
    print("  answer:")
    print(data["answer"])


if __name__ == "__main__":
    main()
