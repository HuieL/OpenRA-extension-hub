#!/usr/bin/env python3
"""Deterministically package a local extension tree into the pinned asset zip.

An entry's installable deliveries (`package`, `mcp-local`) pin one artifact
per platform by sha256, so the zip an author uploads must be rebuildable
byte-for-byte: this script fixes everything a default zip writer leaves to
chance (entry order, timestamps, permissions). It also enforces the runtime
unpack contract the OpenAR host checks at install time: `extension.json` at
the archive root, regular files only, and the executable bit carried in the
unix mode so installed scripts stay runnable. Zero dependencies beyond the
standard library; read the source directory, write one zip, execute nothing.

Usage:
  python3 scripts/package-local.py <source-dir> [--platforms macos,linux]
                                    [--out <dir>] [--check <existing.zip>]

`--check` repacks the tree and compares against a published zip, reporting
the first divergence (entry set, order, or contents) — a rebuilt artifact
that hashes differently fails the entry's pinned sha256.
"""

import argparse
import hashlib
import json
import pathlib
import sys
import zipfile

# ZIP epoch: the earliest timestamp the format can store, so no author's
# clock ever changes a byte.
FIXED_DATE = (1980, 1, 1, 0, 0, 0)
MAX_ASSET_BYTES = 512 * 1024 * 1024


def source_files(root):
    """The tree's files, zip-name order. Built artifacts (`*.zip`) are
    outputs of this script, never sources; symlinks and special files are
    refused — the runtime unpacker accepts regular files only."""
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            sys.exit(f"refusing symlink in the package tree: {path}")
        if path.is_dir():
            continue
        if path.suffix == ".zip":
            continue
        if not path.is_file():
            sys.exit(f"refusing non-regular file in the package tree: {path}")
        files.append(path)
    return files


def pack(root, files):
    """Zip bytes for the tree: sorted names, fixed timestamps, regular-file
    mode with the owner-executable bit preserved."""
    buffer = __import__("io").BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(), FIXED_DATE)
            info.create_system = 3  # unix
            mode = 0o100755 if path.stat().st_mode & 0o111 else 0o100644
            info.external_attr = mode << 16
            archive.writestr(info, path.read_bytes())
    return buffer.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=pathlib.Path, help="the unpacked package tree (with extension.json at its root)")
    parser.add_argument("--platforms", default="macos,linux", help="platforms for the assets snippet (default: macos,linux)")
    parser.add_argument("--out", type=pathlib.Path, help="output directory (default: the source directory)")
    parser.add_argument("--check", type=pathlib.Path, help="an existing zip to compare a fresh pack against")
    args = parser.parse_args()

    root = args.source.resolve()
    manifest = root / "extension.json"
    if not manifest.is_file():
        sys.exit("the source tree has no extension.json at its root")
    document = json.loads(manifest.read_bytes())
    entry_id, version = document.get("id"), document.get("version")
    if not isinstance(entry_id, str) or not isinstance(version, str):
        sys.exit("extension.json carries no usable id/version")

    files = source_files(root)
    if not files:
        sys.exit("the source tree is empty")
    total = sum(path.stat().st_size for path in files)
    if total > MAX_ASSET_BYTES:
        sys.exit(f"tree is {total} bytes; the runtime budget is {MAX_ASSET_BYTES}")
    blob = pack(root, files)
    digest = hashlib.sha256(blob).hexdigest()

    if args.check:
        existing = args.check.read_bytes()
        if blob == existing:
            print(f"{args.check.name}: reproduced byte-for-byte (sha256 {digest[:12]}…)")
            return
        with zipfile.ZipFile(__import__("io").BytesIO(existing)) as old:
            old_names, new_names = old.namelist(), [p.relative_to(root).as_posix() for p in files]
            if old_names != new_names:
                print(f"entry set/order differs:\n  existing {old_names}\n  rebuilt  {new_names}")
            else:
                for name, path in zip(new_names, files):
                    if old.read(name) != path.read_bytes():
                        print(f"first differing entry: {name}")
                        break
        sys.exit(f"{args.check.name}: a rebuild does not reproduce it")

    out_dir = args.out or root
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{entry_id}-{version}.zip"
    if target.exists() and target.read_bytes() != blob:
        sys.exit(f"{target.name} already exists with different bytes; move it aside or pass --check")
    target.write_bytes(blob)

    platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]
    snippet = {"assets": [
        {"platform": platform, "url": f"…/entries/extensions/{entry_id}/package/{target.name}",
         "sha256": digest, "bytes": len(blob)}
        for platform in platforms]}
    print(f"{target.name}: {len(blob)} bytes, sha256 {digest}")
    print("entries/extensions/%s/package/%s" % (entry_id, target.name))
    print("assets snippet (fill the pinned revision into the URL):")
    print(json.dumps(snippet, indent=2))


if __name__ == "__main__":
    main()
