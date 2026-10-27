#!/usr/bin/env python3
"""Selftest for scripts/package-local.py (EH09 打包 verb): determinism, the
runtime unpack contract, and --check's two verdicts. Standard library only;
CI runs exactly this with no secrets and no install step."""

import json
import pathlib
import subprocess
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PACKER = ROOT / "scripts" / "package-local.py"


def run(*argv):
    return subprocess.run([sys.executable, str(PACKER), *argv], capture_output=True, text=True)


def tree(directory, executable=False):
    package = directory / "package"
    (package / "server").mkdir(parents=True)
    (package / "extension.json").write_text(json.dumps({
        "id": "acme.sample", "version": "1.0.0",
        "mcpServer": {"transport": "stdio", "command": ["server/run.sh"], "version": "1.0.0"},
        "bindings": [], "hostApi": 1,
    }))
    (package / "LICENSE").write_text("MIT\n")
    (package / "server" / "run.sh").write_text("#!/bin/sh\nexit 0\n")
    mode = package / "server" / "run.sh"
    mode.chmod(0o755 if executable else 0o644)
    return package


def main():
    with tempfile.TemporaryDirectory() as work:
        work = pathlib.Path(work)
        source = tree(work)
        first, second = run(str(source)), run(str(source))
        assert first.returncode == 0, first.stderr
        # Determinism: the same tree packs to the same bytes twice.
        assert first.stdout.split("\n")[0] == second.stdout.split("\n")[0], "two packs differ"
        blob = (source / "acme.sample-1.0.0.zip").read_bytes()
        # The runtime unpack contract: extension.json at the root, regular
        # files only, unix mode with the executable bit carried.
        with zipfile.ZipFile(__import__("io").BytesIO(blob)) as archive:
            names = archive.namelist()
            assert "extension.json" in names, names
            assert names == sorted(names), names
            assert archive.getinfo("server/run.sh").external_attr >> 16 & 0o100644 == 0o100644
            assert archive.getinfo("extension.json").date_time[:3] == (1980, 1, 1), "timestamps are fixed"
        # --check reproduces a just-packed artifact and refuses a mutated one.
        published = source / "acme.sample-1.0.0.zip"
        ok = run(str(source), "--check", str(published))
        assert ok.returncode == 0, ok.stderr
        (source / "LICENSE").write_text("Apache-2.0\n")
        drifted = run(str(source), "--check", str(published))
        assert drifted.returncode != 0, "a mutated tree must not reproduce the pin"
        assert "LICENSE" in drifted.stdout, drifted.stdout
        # A tree without extension.json is refused before anything is written.
        empty = work / "empty"
        empty.mkdir()
        refused = run(str(empty))
        assert refused.returncode != 0 and "extension.json" in refused.stderr, refused.stderr + refused.stdout
        # Symlinks are refused.
        linked = tree(work / "linked2", executable=True)
        (linked / "oat").symlink_to(linked / "LICENSE")
        refused = run(str(linked))
        assert refused.returncode != 0 and "symlink" in refused.stderr, refused.stderr
        # The executable bit is preserved end to end when set.
        executable_tree = tree(work / "exec", executable=True)
        packed = run(str(executable_tree))
        assert packed.returncode == 0, packed.stderr
        with zipfile.ZipFile(executable_tree / "acme.sample-1.0.0.zip") as archive:
            assert archive.getinfo("server/run.sh").external_attr >> 16 & 0o111
    print("package-local selftest: all checks passed")


if __name__ == "__main__":
    main()
