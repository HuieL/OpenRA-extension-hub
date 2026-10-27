#!/usr/bin/env python3
"""Pre-flight a local package tree's extension.json against the hub's rules.

Authors previously only met the manifest admission rules when CI ran on an
opened PR; this runs the identical checker (`validate.check_manifest` —
imported, never forked) on a standalone tree, so violations surface before
anything is committed or packaged. With `--entry <entry.json>` the real
cross-checks against the catalog entry run too (version, mcp spec, hostApi,
entry mcp binding backing) — byte-for-byte the CI call, minus the checks that
need the hub checkout (entry path/source/asset rules).

Usage:
  python3 scripts/validate-package.py <package-dir | extension.json>
                                     [--entry <entry.json>]

Standard library only; reads two files, executes nothing.
"""

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import validate  # noqa: E402  (the CI checker, reused verbatim)

# Checks that need a real entry and are therefore only reported in CI (or
# with --entry); without an entry they would be tautologies.
ENTRY_SIDE_CHECKS = (
    "package manifest version must equal the entry version",
    "package manifest mcpServer must equal the entry mcp spec",
    "package manifest hostApi must equal the entry compat.hostApi",
    "entry mcp bindings must be backed by manifest actions",
    "entry integration must be L1 or higher for a package form page",
    "the entry declares delivery: mcp-local (hosted package trees)",
    "entry.json itself (paths, source, assets, review …) — CI validates it in the hub",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tree", type=pathlib.Path,
                        help="the package tree (extension.json at its root) or the manifest path itself")
    parser.add_argument("--entry", type=pathlib.Path,
                        help="an entry.json to run the real cross-checks against, exactly like CI")
    args = parser.parse_args()

    tree = args.tree
    if tree.name == "extension.json":
        tree = tree.parent
    manifest_path = tree / "extension.json"
    if not manifest_path.is_file():
        sys.exit(f"the package tree has no extension.json at its root: {tree}")
    raw = manifest_path.read_bytes()
    if len(raw) > validate.MAX_MANIFEST_BYTES:
        sys.exit("package extension.json exceeds the 64 KiB runtime cap")
    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as error:
        sys.exit(f"package extension.json is not valid JSON: {error}")
    if not isinstance(manifest, dict):
        sys.exit("package extension.json must be a JSON object")
    entry_id = manifest.get("id") if isinstance(manifest.get("id"), str) else "package"

    if args.entry:
        try:
            entry = json.loads(args.entry.read_bytes())
        except OSError as error:
            sys.exit(f"cannot read the entry: {error}")
        except json.JSONDecodeError as error:
            sys.exit(f"the entry is not valid JSON: {error}")
        if not isinstance(entry, dict):
            sys.exit("the entry must be a JSON object")
    else:
        # Standalone: synthesize the entry from the manifest so the shared
        # checker's manifest-side rules all run; only the entry-side rules
        # above are bypassed, and they are listed instead of silently passed.
        entry = {
            "version": manifest.get("version"),
            "delivery": "mcp-local",
            "integration": "L1",
            "compat": {"hostApi": manifest.get("hostApi")},
            "bindings": [],
        }
        if isinstance(manifest.get("mcpServer"), dict):
            entry["mcp"] = dict(manifest["mcpServer"])

    validate.check_manifest(entry, entry_id, manifest)
    if validate.errors:
        print("\n".join(validate.errors))
        sys.exit(1)
    if not args.entry:
        print("manifest rules pass (standalone); only CI or a later --entry can check:")
        for line in ENTRY_SIDE_CHECKS:
            print(f"  - {line}")
    else:
        print(f"manifest rules pass, cross-checked against {args.entry.name} (CI parity)")
    print(f"{manifest_path}: {len(raw)} bytes")


if __name__ == "__main__":
    main()
