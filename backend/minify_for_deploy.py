"""
Minifies vercel_dist/ into vercel_dist_min/ for a much smaller deploy
payload: strips comments (automatic, since the `ast` module never retains
them) and genuine docstrings (Module/ClassDef/FunctionDef/AsyncFunctionDef
first-statement bare string literals), then regenerates source with
ast.unparse(). This is a real parse->transform->unparse round trip, not
regex text-mangling, so it can't accidentally corrupt a string literal that
merely *looks* like a docstring (e.g. the HTML/text email template bodies
in core_bundle.py, which are f-string *values* assigned to a variable, not
bare first-statement expressions, so the transformer never touches them).

Non-.py files (vercel.json, requirements.txt) are copied byte-for-byte.
Every output .py file is py_compile-checked before this script exits.
"""
import ast
import pathlib
import py_compile
import shutil

SRC = pathlib.Path(__file__).parent / "vercel_dist"
DST = pathlib.Path(__file__).parent / "vercel_dist_min"


class DocstringStripper(ast.NodeTransformer):
    def _strip(self, node):
        self.generic_visit(node)
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            node.body = node.body[1:] or [ast.Pass()]
        return node

    visit_Module = _strip
    visit_ClassDef = _strip
    visit_FunctionDef = _strip
    visit_AsyncFunctionDef = _strip


def minify_py(src_path: pathlib.Path) -> str:
    source = src_path.read_text()
    tree = ast.parse(source, filename=str(src_path))
    tree = DocstringStripper().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def main():
    if DST.exists():
        shutil.rmtree(DST)
    total_before = total_after = 0
    for src_path in sorted(SRC.rglob("*")):
        if src_path.is_dir():
            continue
        rel = src_path.relative_to(SRC)
        dst_path = DST / rel
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        before = src_path.stat().st_size
        if src_path.suffix == ".py":
            minified = minify_py(src_path)
            dst_path.write_text(minified)
            after = len(minified.encode())
        else:
            shutil.copyfile(src_path, dst_path)
            after = before
        total_before += before
        total_after += after
        print(f"{rel}: {before} -> {after} bytes")
    print(f"TOTAL: {total_before} -> {total_after} bytes")

    # Safety check: every emitted .py file must still compile.
    failures = []
    for py_path in DST.rglob("*.py"):
        try:
            py_compile.compile(str(py_path), doraise=True)
        except py_compile.PyCompileError as exc:
            failures.append((py_path, str(exc)))
    if failures:
        for path, err in failures:
            print(f"COMPILE FAILURE: {path}\n{err}")
        raise SystemExit(f"{len(failures)} file(s) failed to compile after minification")
    print("All minified files compiled successfully.")


if __name__ == "__main__":
    main()
