#!/usr/bin/env python3
"""Negative self-tests: each mutation of a valid entry must be rejected.

Not run by CI; run locally (python3 scripts/selftest-negative.py) before
changing scripts/validate.py. Each case mutates one fact of a known-good
entry and asserts the validator records at least one error for it.
"""

import copy
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("validate", HERE / "validate.py")
validate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate)

HEX64 = "a" * 64
SHA40 = "0" * 40


def base_entry() -> dict:
    return {
        "schemaVersion": 1,
        "id": "example.mcp-local",
        "kind": "extension",
        "name": "Echo MCP",
        "summary": "Local stdio echo MCP fixture.",
        "authors": [{"name": "Example Author", "github": "example-author"}],
        "source": {
            "repo": "https://github.com/example/echo-mcp",
            "path": ".",
            "revision": SHA40,
        },
        "version": "0.1.0",
        "license": "Apache-2.0",
        "review": {"status": "unreviewed"},
        "compat": {
            "minHost": "0.3.0",
            "hostApi": {"min": 1, "max": 2},
            "platforms": ["macos", "linux"],
        },
        "delivery": "mcp-local",
        "integration": "L1",
        "bindings": [
            {
                "kind": "mcp",
                "tool": "echo",
                "inputSchemaDigest": HEX64,
                "outputSchemaDigest": HEX64,
            }
        ],
        "assets": [
            {
                "platform": "macos-arm64",
                "url": "https://github.com/example/echo-mcp/releases/download/v0.1.0/echo-macos.tar.gz",
                "sha256": "b" * 64,
                "bytes": 1024,
            }
        ],
        "mcp": {
            "transport": "stdio",
            "command": ["bin/echo-server", "--port", "8080"],
            "version": "0.1.0",
            "env": [],
        },
    }


def run_checks(entry: dict) -> list[str]:
    validate.errors = []
    if validate.check_common(entry, entry.get("id", "?")):
        validate.check_source(entry, entry["id"])
        validate.check_review(entry, entry["id"])
        validate.check_compat(entry, entry["id"])
        validate.check_declaration(entry, entry["id"])
        validate.check_bindings(entry, entry["id"])
        validate.check_assets(entry, entry["id"])
        validate.check_mcp(entry, entry["id"])
    return list(validate.errors)


def base_manifest() -> dict:
    return {
        "id": "example.mcp-local",
        "title": "Echo MCP",
        "version": "0.1.0",
        "kind": "mcp",
        "mcpServer": {
            "command": ["bin/echo-server", "--port", "8080"],
            "version": "0.1.0",
            "env": [],
            "transport": "stdio",
        },
        "hostApi": {"min": 1, "max": 2},
        "scopes": [{"kind": "personal"}],
        "page": {"form": "echo"},
        "configSchema": {
            "type": "object", "properties": {}, "additionalProperties": False
        },
        "capabilities": ["cli.invoke"],
        "actions": [
            {
                "id": "echo",
                "binding": {
                    "kind": "mcp",
                    "tool": "echo",
                    "inputSchemaDigest": HEX64,
                    "outputSchemaDigest": HEX64,
                },
                "sideEffect": "read",
                "inputSchema": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                    "additionalProperties": False,
                },
                "outputSchema": {
                    "type": "object",
                    "properties": {
                        "echo": {
                            "type": "object",
                            "properties": {"text": {"type": "string"}},
                            "additionalProperties": False,
                        }
                    },
                    "required": ["echo"],
                    "additionalProperties": False,
                },
            }
        ],
    }


def run_manifest_checks(entry: dict, manifest: dict) -> list[str]:
    validate.errors = []
    validate.check_manifest(entry, entry.get("id", "?"), manifest)
    return list(validate.errors)


CASES = []


def case(name):
    def register(fn):
        CASES.append((name, fn))
        return fn
    return register


@case("shell metacharacter in command word")
def _(e, m):
    e["mcp"]["command"] = ["bin/echo-server", "--port; rm -rf /"]


@case("absolute path as command[0]")
def _(e, m):
    e["mcp"]["command"] = ["/usr/bin/env", "python"]


@case("host binary (no slash) as command[0]")
def _(e, m):
    e["mcp"]["command"] = ["python", "server.py"]


@case("parent-directory component in command")
def _(e, m):
    e["mcp"]["command"] = ["../escape/server"]


@case("pipe in command argument")
def _(e, m):
    e["mcp"]["command"] = ["bin/echo-server", "8080|sh"]


@case("mcp binding missing inputSchemaDigest")
def _(e, m):
    del e["bindings"][0]["inputSchemaDigest"]


@case("asset url with userinfo credentials")
def _(e, m):
    e["assets"][0]["url"] = "https://token:secret@github.com/example/echo-mcp/echo.tar.gz"


@case("asset url on a private-network host")
def _(e, m):
    e["assets"][0]["url"] = "https://10.0.0.1/echo.tar.gz"


@case("mutable revision instead of commit SHA")
def _(e, m):
    e["source"]["revision"] = "main"


@case("bundled delivery (built-ins are not listed)")
def _(e, m):
    e["delivery"] = "bundled"


@case("uppercase id")
def _(e, m):
    e["id"] = "Example.Mcp-Local"


@case("reserved openra.* namespace")
def _(e, m):
    e["id"] = "openra.echo"


@case("unpinned cli binding version")
def _(e, m):
    e["bindings"] = [
        {"kind": "cli", "adapter": "ripgrep", "version": "latest", "hash": HEX64}
    ]


@case("mcp spec on a package delivery")
def _(e, m):
    e["delivery"] = "package"


@case("reviewed status without reviewedRevision")
def _(e, m):
    e["review"] = {"status": "reviewed"}


@case("missing authors")
def _(e, m):
    del e["authors"]


@case("empty authors list")
def _(e, m):
    e["authors"] = []


@case("env name outside the [A-Za-z0-9_] charset")
def _(e, m):
    e["mcp"]["env"] = [{"name": "API-KEY", "credentialRef": "echo/api-key"}]


@case("duplicate env names")
def _(e, m):
    e["mcp"]["env"] = [
        {"name": "API_KEY", "credentialRef": "echo/api-key"},
        {"name": "API_KEY", "credentialRef": "echo/other"},
    ]


@case("registrySubmitter with an @ prefix")
def _(e, m):
    e["registrySubmitter"] = "@example-author"


@case("inline = value in a command word")
def _(e, m):
    e["mcp"]["command"] = ["bin/echo-server", "--token=sk-live-123"]


@case("asset url on an alibaba metadata host")
def _(e, m):
    e["assets"][0]["url"] = "https://100.100.100.200/latest/meta-data/echo.tar.gz"


@case("asset url on an aws ipv6 metadata host")
def _(e, m):
    e["assets"][0]["url"] = "https://[fd00:ec2::254]/latest/meta-data/echo.tar.gz"


@case("asset url on a single-label domain")
def _(e, m):
    e["assets"][0]["url"] = "https://intranet/echo.tar.gz"


@case("cli binding adapter outside the identifier charset")
def _(e, m):
    e["bindings"] = [
        {"kind": "cli", "adapter": "ripgrep adapter", "version": "14.1.0", "hash": HEX64}
    ]


@case("mcp binding tool outside the plain-word charset")
def _(e, m):
    e["bindings"] = [
        {"kind": "mcp", "tool": "echo tool", "inputSchemaDigest": HEX64}
    ]


@case("mcp-local version outside the plain-word charset")
def _(e, m):
    e["mcp"]["version"] = "0.1.0 (nightly)"


@case("package manifest outputSchema without additionalProperties (the 1.0.0 bug)")
def _(e, m):
    del m["actions"][0]["outputSchema"]["additionalProperties"]


@case("package manifest id in the openra.* namespace")
def _(e, m):
    m["id"] = "openra.mcp-echo"


@case("L0 entry declaring a package form page")
def _(e, m):
    e["integration"] = "L0"


@case("integration L3 is not open")
def _(e, m):
    e["integration"] = "L3"


@case("ordinary MCP server claiming the L2 UI contract")
def _(e, m):
    e["integration"] = "L2"


@case("L0 entry declaring ui contributions")
def _(e, m):
    e["integration"] = "L0"
    e["uiContributions"] = ["commands"]


@case("L1 entry declaring a main-page contribution")
def _(e, m):
    e["uiContributions"] = ["main-page"]


@case("package manifest version drift from the entry")
def _(e, m):
    m["version"] = "0.2.0"


@case("package manifest capabilities beyond cli.invoke")
def _(e, m):
    m["capabilities"] = ["cli.invoke", "scratchpad.read"]


@case("package manifest summary (runtime-reserved field)")
def _(e, m):
    m["summary"] = "catalog copy lives in the entry"


@case("entry mcp binding with no manifest action backing")
def _(e, m):
    e["bindings"][0]["tool"] = "other"


@case("package manifest mcpServer command drift")
def _(e, m):
    m["mcpServer"]["command"] = ["bin/other-server"]


@case("package manifest hostApi drift")
def _(e, m):
    m["hostApi"] = 1


@case("package manifest page form outside the action ids")
def _(e, m):
    m["page"] = {"form": "nope"}


@case("package manifest schema property name outside the identifier charset")
def _(e, m):
    schema = m["actions"][0]["inputSchema"]
    schema["properties"]["bad.name"] = {"type": "string"}


@case("package manifest permissive configSchema")
def _(e, m):
    m["configSchema"]["additionalProperties"] = True


@case("package manifest required key not among the properties")
def _(e, m):
    schema = m["actions"][0]["inputSchema"]
    schema["required"] = ["text", "missing"]



@case("package manifest missing required title")
def _(e, m):
    del m["title"]


@case("package manifest null title")
def _(e, m):
    m["title"] = None


@case("package manifest title exceeds 160 UTF-8 bytes")
def _(e, m):
    m["title"] = "研" * 54


@case("package manifest title exceeds 160 ASCII bytes")
def _(e, m):
    m["title"] = "x" * 161


@case("package manifest title contains an unpaired surrogate")
def _(e, m):
    m["title"] = "\ud800"


def main() -> None:
    # The unmutated fixtures must pass every check.
    clean = run_checks(base_entry())
    if clean:
        print("FAIL: base entry does not validate cleanly:")
        print("\n".join(clean))
        sys.exit(1)
    clean = run_manifest_checks(base_entry(), base_manifest())
    if clean:
        print("FAIL: base manifest does not validate cleanly:")
        print("\n".join(clean))
        sys.exit(1)

    # The runtime definition-id grammar allows underscores in segments.
    underscored = base_entry()
    underscored["id"] = "example.mcp_echo"
    errors = run_checks(underscored)
    if errors:
        print("FAIL: underscore id segment must be accepted:")
        print("\n".join(errors))
        sys.exit(1)

    # The runtime title cap counts UTF-8 bytes, not Unicode code points.
    for title in ("x" * 160, "研" * 53 + "x"):
        manifest = base_manifest()
        manifest["title"] = title
        assert not run_manifest_checks(base_entry(), manifest), "exactly 160 UTF-8 bytes must pass"

    failures = 0
    for name, mutate in CASES:
        entry = base_entry()
        manifest = base_manifest()
        mutate(entry, manifest)
        errors = run_checks(entry) + run_manifest_checks(entry, manifest)
        if errors:
            print(f"ok   {name} -> {errors[0]}")
        else:
            print(f"FAIL {name} -> accepted")
            failures += 1
    if failures:
        print(f"{failures} negative case(s) were accepted")
        sys.exit(1)
    print(f"OK: {len(CASES)} negative cases rejected, base entry and manifest clean")


if __name__ == "__main__":
    main()
