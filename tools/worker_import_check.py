import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "worker"))

from praetor_worker.main import app  # noqa: E402


def main() -> int:
    routes = sorted(route.path for route in app.routes)
    print("praetor_worker import ok")
    print(f"routes={len(routes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
