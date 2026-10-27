# Contributing to the OpenAR Extension Hub

This repository is a static catalog. OpenAR reads `extensions.json` at a pinned
commit SHA and verifies each entry's sha256 before use. There is no server, no
account, and no install script to run here.

## Adding an entry

1. Host your extension in your own repository. This hub does not copy
   third-party repositories; `delivery` decides what an install resolves to:
   - `package` / `cli` — a pinned release artifact per platform;
   - `mcp-local` — a package whose MCP server command runs inside the
     installed tree;
   - `mcp-remote` — a registered connection; nothing is downloaded;
   - `bundled` — reserved for the OpenAR maintainers: a first-party extension
     whose code ships inside the app (Deep Research, Paper Search, Calendar,
     Deadlines, Craft Suite, Scientific Compute). Installing it from the Hub
     switches it on; nothing is downloaded, and uninstalling keeps its data.
     Its `version` must equal the version the app ships.

   The app's own sidebar features (Reminders, Knowledge Hub, Skill Hub,
   Research Outputs, Library, AI Coworkers) are not extensions and are never
   listed here.
2. Create `entries/extensions/<id>/entry.json` following
   `schemas/extension-entry.schema.json`. The required facts:
   - `id` — lowercase namespaced identity (e.g. `acme.calendar`), equal to
     the directory name, globally unique, never reused;
   - `authors` — the original creator(s), credited from the source repo's
     commits, license, or README. Adapting an extension for OpenAR is
     recorded in `adapters`, submitting it in `registrySubmitter`; neither
     grants authorship. `maintainers`, `contributors` and `categories` are
     optional;
   - `source` — public HTTPS repo URL, the extension's subdirectory, and an
     exact 40-hex commit SHA. `main`/`latest`/mutable tags are never accepted
     as a pin;
   - `assets` — for installable deliveries, one pinned HTTPS artifact per
     platform with sha256 and size;
   - `license` — SPDX id; the entry must state the license its content
     actually carries.
3. Run `python3 scripts/build-index.py` and commit the regenerated
   `extensions.json` together with your entry.
4. Open a PR. CI runs `scripts/validate.py` (read-only, no secrets, no
   install step; it never executes anything from your entry).

## Packaging a local asset

For `package`, `mcp-local` and `cli` deliveries, build the zip with
`python3 scripts/package-local.py <source-dir> --platforms macos,linux`.
The pin in `entry.json` is a sha256 over exact bytes, so the artifact must
be rebuildable byte-for-byte: the script fixes entry order, timestamps and
permissions instead of leaving them to your zip tool's defaults, keeps the
executable bit the install chain expects, refuses symlinks and special
files, and prints the sha256 with a ready-to-paste `assets` snippet.
Built zips are outputs — the script never repacks an existing `*.zip`, and
`--check <published.zip>` verifies a published artifact still reproduces
from the tree. Hosting the artifact is yours; this hub keeps only the pin.

## Remote MCP services

An `mcp-remote` entry registers a connection to a hosted MCP service; the
service stays on its owner's infrastructure. The `observed` block is a live
probe, not a promise: record the tools and resources a real handshake
returned, the server version it reported, and the date of the observation.
Metadata may be imported read-only from the official MCP Registry or the
service's own repository, but the observation must come from this hub's own
probe, and `source` still pins the upstream repository at an exact commit
SHA. When the service changes, re-probe and update the entry; an entry whose
observation has drifted is updated or deprecated, never quietly rewritten.
`python3 scripts/probe-remote.py [id…]` repeats the probe for every
`mcp-remote` entry and lists drift (tools added/removed, recorded resources
missing, server version); the `probe-remote` workflow runs it on demand.

## What review means

`review.status` records what a human looked at, and `reviewedRevision` pins
which revision that covered. `unreviewed` is not an accusation and `reviewed`
is not a guarantee; neither grants anything on a user's machine. Declarations
in an entry (capabilities, uiContributions, bindings) are claims the host
verifies at install and use time — declared is not detected, detected is not
verified.

## Updates and removal

A new upstream revision is a new `source.revision` plus a new `assets`/`mcp`
manifest; the index is regenerated in the same PR. Deprecation or a high-risk
marking changes `review.status` with a reason in the PR — entries and history
are never silently deleted, and upstream deletion never silently removes a
catalog record.
