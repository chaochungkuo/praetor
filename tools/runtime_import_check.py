import importlib.util
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workers" / "runtime"))


def main() -> int:
    spec = importlib.util.find_spec("praetor_runtime")
    if spec is None:
        raise SystemExit("praetor_runtime import failed")
    print("praetor_runtime import ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
