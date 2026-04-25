import pathlib
import py_compile


ROOT = pathlib.Path(__file__).resolve().parents[1]


def compile_tree(root: pathlib.Path) -> None:
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        py_compile.compile(str(path), doraise=True)


def main() -> int:
    compile_tree(ROOT / "apps" / "api" / "praetor_api")
    compile_tree(ROOT / "bridges" / "praetor-execd" / "praetor_execd")
    compile_tree(ROOT / "workers" / "runtime" / "praetor_runtime")
    print("py_compile ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
