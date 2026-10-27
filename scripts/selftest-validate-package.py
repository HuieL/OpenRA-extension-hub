#!/usr/bin/env python3
"""Selftest for scripts/validate-package.py (EH09 验证 verb): the pre-flight
runs the CI checker on a standalone tree, both verdicts agree with CI, and the
entry cross-checks really bind. Standard library only; CI runs exactly this."""

import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PRE = ROOT / "scripts" / "validate-package.py"
ECHO = ROOT / "entries" / "extensions" / "hub.mcp-echo"
PACKAGE, ENTRY = ECHO / "package", ECHO / "entry.json"


def run(*argv):
    return subprocess.run([sys.executable, str(PRE), *argv], capture_output=True, text=True)


def mutate(work, name, change_manifest=None, change_entry=None):
    tree = work / name
    tree.mkdir()
    manifest = json.loads((PACKAGE / "extension.json").read_text())
    entry = json.loads(ENTRY.read_text())
    if change_manifest:
        change_manifest(manifest)
    if change_entry:
        change_entry(entry)
    (tree / "extension.json").write_text(json.dumps(manifest))
    entry_path = work / f"{name}.entry.json"
    entry_path.write_text(json.dumps(entry))
    return tree, entry_path


def main():
    with tempfile.TemporaryDirectory() as work:
        work = pathlib.Path(work)
        # Agreement with CI's own verdict on the untouched entry.
        assert run(str(PACKAGE)).returncode == 0
        assert run(str(PACKAGE), "--entry", str(ENTRY)).returncode == 0
        # Standalone mode names the checks it cannot run instead of passing them silently.
        standalone = run(str(PACKAGE))
        assert "standalone" in standalone.stdout and "compat.hostApi" in standalone.stdout
        # The real cross-checks bind with --entry (same messages CI prints).
        for name, change in [
            ("version", lambda m: m.update(version="1.0.99")),
            ("hostApi", lambda m: m.update(hostApi=2)),
        ]:
            tree, entry_path = mutate(work, f"drift-{name}", change_manifest=change)
            out = run(str(tree), "--entry", str(entry_path))
            assert out.returncode != 0 and "equal the entry" in out.stdout, out.stdout + out.stderr
        # Manifest-side rules run standalone too (reserved namespace, page, title).
        for name, change, message in [
            ("reserved", lambda m: m.update(id="openra.echo"), "openra.* namespace"),
            ("page", lambda m: m.pop("page"), "page"),
            ("title", lambda m: m.update(title="x" * 200), "title"),
        ]:
            tree, entry_path = mutate(work, f"bad-{name}", change_manifest=change)
            out = run(str(tree))
            assert out.returncode != 0 and message in out.stdout, out.stdout + out.stderr
        # A manifest passed as the path itself resolves to its package tree.
        assert run(str(PACKAGE / "extension.json"), "--entry", str(ENTRY)).returncode == 0
    print("validate-package selftest: all checks passed")


if __name__ == "__main__":
    main()
