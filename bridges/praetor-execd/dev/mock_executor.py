#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    workdir = Path(os.environ["PRAETOR_HOST_WORKDIR"])
    task_spec = payload.get("task_spec", {})
    title = task_spec.get("title", "untitled")
    out = workdir / "mock-executor-output.txt"
    out.write_text(
        f"title={title}\nmission={os.environ.get('PRAETOR_MISSION_ID')}\n",
        encoding="utf-8",
    )
    print(f"mock executor wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
