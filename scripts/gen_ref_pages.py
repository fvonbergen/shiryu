"""Universal pre-build script to auto-generate API reference Markdown files.

Strips top-level package names appropriately and constructs clean import paths
so mkdocstrings and autorefs can generate target anchors for cross-linking.
"""

# TODO: missing plugin gen-files (https://zensical.org/compatibility/plugins/)
# File could be removed when zensical plugin is available.

import argparse
import shutil
from pathlib import Path

SRC_DIR = Path("src")
REF_DIR = Path("docs/reference")
API_REF_DIR = Path("api-reference")


def should_skip(path: Path) -> bool:
    """Check if any parent directory or file in path starts with private prefixes."""
    for part in path.parts:
        if part.startswith(".") or part == "__pycache__":
            return True
        if part.startswith("_") and part != "__init__.py":
            return True
    return False


def _process_single_file(
    path: Path,
    src_dir: Path,
    ref_dir: Path,
    dry_run: bool,
    verbose: bool,
) -> tuple[str, str] | None:
    """Process a single Python file and return its module import path and relative doc path."""
    rel_path = path.relative_to(src_dir)
    parts = list(rel_path.with_suffix("").parts)
    is_init = parts[-1] == "__init__"

    if is_init:
        import_parts = parts[:-1]
        if not import_parts:
            return None
        module_import_path = ".".join(import_parts)
    else:
        module_import_path = ".".join(parts)

    doc_parts = parts[1:] if len(parts) > 1 else parts

    # ALWAYS map generated files inside api-reference/
    if is_init:
        doc_parts = doc_parts[:-1]
        target_rel_path = API_REF_DIR / (
            Path("index.md") if not doc_parts else Path(*doc_parts) / "index.md"
        )
    else:
        target_rel_path = API_REF_DIR / Path(*doc_parts).with_suffix(".md")

    doc_file = ref_dir / target_rel_path
    content = f"# {module_import_path}\n\n::: {module_import_path}\n"

    if verbose or dry_run:
        print(f"[GEN] {module_import_path} -> {doc_file}")

    if not dry_run:
        doc_file.parent.mkdir(parents=True, exist_ok=True)
        doc_file.write_text(content, encoding="utf-8")

    return module_import_path, target_rel_path.as_posix()


def _write_reference_index(generated_modules: dict[str, str], ref_dir: Path, dry_run: bool) -> None:
    """Generate the main API Reference Index Page inside reference/api-reference/index.md."""
    if not generated_modules:
        return

    index_file = ref_dir / API_REF_DIR / "index.md"
    index_lines = ["# API Modules Overview\n", "Auto-generated module references:\n"]

    for mod, rel_link in sorted(generated_modules.items()):
        # Strip leading 'api-reference/' so markdown links work relative to api-reference/index.md
        clean_link = rel_link.removeprefix(f"{API_REF_DIR}/")
        indent = "  " * (mod.count("."))
        index_lines.append(f"{indent}* [`{mod}`]({clean_link})")

    if not dry_run:
        index_file.parent.mkdir(parents=True, exist_ok=True)
        index_file.write_text("\n".join(index_lines) + "\n", encoding="utf-8")


def generate_reference_docs(
    *,
    src_dir: Path = SRC_DIR,
    ref_dir: Path = REF_DIR,
    dry_run: bool = False,
    verbose: bool = False,
) -> None:
    """Scan `src/` for Python modules and generate API Markdown files under api-reference/."""
    if not src_dir.exists():
        print(f"Error: Directory '{src_dir}' does not exist.")
        return

    py_files = [
        path for path in sorted(src_dir.rglob("*.py")) if not should_skip(path.relative_to(src_dir))
    ]

    api_ref_dir = ref_dir / API_REF_DIR
    if not dry_run:
        if api_ref_dir.exists():
            shutil.rmtree(api_ref_dir)
        api_ref_dir.mkdir(parents=True, exist_ok=True)

    generated_modules: dict[str, str] = {}

    for path in py_files:
        result = _process_single_file(path, src_dir, ref_dir, dry_run, verbose)
        if result:
            mod_path, doc_path = result
            generated_modules[mod_path] = doc_path

    _write_reference_index(generated_modules, ref_dir, dry_run)

    action = "Would generate" if dry_run else "Successfully generated"
    print(f"{action} reference docs for {len(generated_modules)} module(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate API reference markdown files.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate execution without writing files.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Print mapped files.")
    args = parser.parse_args()

    generate_reference_docs(dry_run=args.dry_run, verbose=args.verbose)

