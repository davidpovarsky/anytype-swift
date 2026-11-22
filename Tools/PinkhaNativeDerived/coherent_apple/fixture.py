"""Derive an explicit non-shipping iOS fixture without changing native assertions."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re

import contract

ORIGINAL_DIRECTORY = "Tools/PinkhaNativeDerived/coherent_read/account"
ORIGINALS = {"native_signed_revocation_base_test.go", "coherent_authority_account_test.go"}
ASSERTIONS = {"NoError", "Equal", "NotEqual", "True", "False", "Len", "Empty", "NotEmpty", "NotNil", "Nil", "Same", "LessOrEqual", "Contains"}
BRIDGE = "coherent_apple_fixture_bridge.go"
PREFIX = "//go:build " + contract.FIXTURE_TAG + "\n\n"


def transformed(original_name, raw):
    text = raw.decode("utf8")
    contract.require(text.startswith("package service\n") and text.endswith("\n"), "Unexpected fixture source format")
    contract.require(text.count('\t"testing"\n') == 1
                     and text.count('\t"github.com/stretchr/testify/require"\n') == 1,
                     "Original fixture assertion imports changed")
    used = set(re.findall(r"\brequire\.(\w+)\(", text))
    contract.require(used <= ASSERTIONS and used, "Unreviewed assertion in native fixture")
    text = text.replace('\t"testing"\n', "").replace('\t"github.com/stretchr/testify/require"\n', "")
    text = text.replace("*testing.T", "*coherentAppleT").replace("require.", "coherentAppleRequire.")
    if original_name == "coherent_authority_account_test.go":
        old = "func TestCoherentNativeReadsAfterSignedRevocation(t *coherentAppleT) {"
        contract.require(text.count(old) == 1, "Original account method changed")
        text = text.replace(old, "func runCoherentAppleNativeReadsAfterSignedRevocation(t *coherentAppleT) {")
    else:
        old = "\t\tcoherentAppleRequire.NoError(t, proto.Unmarshal(call(data), response))\n"
        contract.require(text.count(old) == 1, "Original native raw-call seam changed")
        text = text.replace(old, "\t\twire := call(data)\n"
            "\t\tcoherentAppleRequire.NoError(t, proto.Unmarshal(wire, response))\n"
            "\t\tcoherentAppleRecordRPCReply(name, wire)\n")
    contract.require("testing." not in text and "require." not in text, "Unconverted assertion or test harness")
    return (PREFIX + text).encode()


def source_files(control, original_hashes):
    contract.require(set(original_hashes) == ORIGINALS, "Unexpected original fixture closure")
    values = {}
    for name in sorted(ORIGINALS):
        path = control / ORIGINAL_DIRECTORY / name
        contract.require(contract.digest(path) == original_hashes[name], "Proven original assertion changed: " + name)
        output = "coherent_apple_" + name.removesuffix("_test.go") + ".go"
        values[output] = transformed(name, path.read_bytes())
    bridge = (contract.HERE / "fixture_bridge.go").read_bytes()
    contract.require(bridge.startswith(PREFIX.encode()) and b"func PinkhaCoherentAppleAuthorityFixture(" in bridge,
                     "Bridge must be explicitly test-tagged")
    values[BRIDGE] = bridge
    hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in values.items()}
    identity = hashlib.sha256()
    for name, raw in sorted(values.items()):
        identity.update(name.encode() + b"\0" + raw)
    return values, hashes, identity.hexdigest()


def materialize(control, heart, original_hashes):
    values, hashes, identity = source_files(control, original_hashes)
    directory = heart / "clientlibrary/service"
    for name in values:
        contract.require(not (directory / name).exists(), "Fixture must not overwrite native source")
    for name, raw in values.items():
        (directory / name).write_bytes(raw)
    return hashes, identity


def remove_owned(heart, hashes):
    for name, expected in hashes.items():
        target = heart / "clientlibrary/service" / name
        contract.require(contract.digest(target) == expected, "Fixture changed before cleanup")
        target.unlink()
