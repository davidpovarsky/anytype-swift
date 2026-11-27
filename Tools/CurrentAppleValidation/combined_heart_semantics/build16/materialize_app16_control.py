#!/usr/bin/env python3
"""Freeze the reviewed App16 intake beside the unchanged original E/F controls.

This creates eight controller files; it never builds, installs, launches or tests
an application. The full original shared collector is retained byte-for-byte,
with one additive intake before main. The source-a089 host controller contains
the already-reviewed XCTest enumeration correction. Its only additional changes
are a freshness-only plan and an accurate focus-scope description.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import stat

ORIGINALS = {
    "combined_heart_observations_gateway.py": "425783c76858b542cb908e5d4c606e3d27b54d6e5bbc1e28a163cc18f13cf4de",
    "combined_heart_semantics_current.py": "1dcd02a4413b26c201e8a38772484eff48e448ae4398af2fd4ee1fc6a5675736",
    "combined_host_acceptance_app15.py": "a1176cbb2401f952c2c01de7b837ea5f02fe0afa5d036373100a5d0e4e024932",
    "combined_host_helper_pins_gateway.json": "8249955bd7bc2908d52e8fdf8470d1577f13731bf2bce7fc0c935aa3846c7e1d",
    "combined_t5_freshness_gateway.py": "d1fe4c88a3c2faeca9973f3a7a3f92d9d043546e766d2c223d21daba7b46d17e",
    "combined_t5_pending_gateway.py": "582152637956f07147121f4c63ba21b647ddae2d6951a19a9c33802179264ddd",
    "combined_t5_retry_gateway.py": "38aff6dc07bdf0183acd3a4ff3dda5bbd2e68abb3bc29f2bb50d4ad117755a86",
    "focus_lifecycle_profile.py": "c88f24e65d48efae13ee70f0fb831733035ff59b81ec92cc493e3b89eb434999",
}
CANONICAL_HOST = "dafbd64fa410ae804641757dc1480110a510699ca5b9fd7aaa37d3939321dba7"
FOCUS = "c495985b9afc278c13ec8900049f9835cee5fd74fc368e2e7b264ecf718c5812"
FRAGMENT = "c908a56ffad6ae08f40b65733db0b2d4f5140ec201847dde928c0d72ea4e6d78"
HOST_EDITS = (
    ('    "t5-native-ui-only": ("t5-native-ui",),\n',
     '    "t5-native-ui-only": ("t5-native-ui",),\n'
     '    "t5-remaining-freshness-only": ("t5-remaining-freshness",),\n'),
    ('"Affected UIKit19 methods including3 new visible-focus/refusal cases; no appUI/nativeACL/release credit"',
     'f"Affected UIKit {focus.METHOD_COUNT} methods/{focus.CASE_COUNT} cases; no app UI/native ACL/release credit"'),
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def read(path):
    require(stat.S_ISREG(path.lstat().st_mode), "Regular original input required: " + str(path))
    return path.read_bytes()


def definitions(value):
    source = value.decode("utf8")
    return [(node.name, ast.get_source_segment(source, node))
            for node in ast.parse(source).body if isinstance(node, (ast.FunctionDef, ast.ClassDef))]


def compose(originals, fragment, host, focus):
    require(set(originals) == set(ORIGINALS), "Complete original eight-file closure required")
    for name, value in originals.items():
        require(sha(value) == ORIGINALS[name], "Original control changed: " + name)
    require(sha(fragment) == FRAGMENT, "Reviewed additive App16 intake changed")
    require(sha(host) == CANONICAL_HOST, "Exact a089 host enumeration controller required")
    require(sha(focus) == FOCUS, "Exact 22-method/34-case profile required")
    original = originals["combined_heart_semantics_current.py"]
    marker = b"\ndef main():\n"
    require(original.count(marker) == 1, "Unique original main insertion point required")
    insertion = b"\n\n" + fragment.rstrip(b"\n") + b"\n\n"
    offset = original.index(marker)
    candidate = original[:offset] + insertion + original[offset:]
    require(candidate[:offset] + candidate[offset + len(insertion):] == original,
            "Additive shared collector cannot restore every original byte")
    previous = definitions(original)
    current = definitions(candidate)
    require(all(current.count(definition) == 1 for definition in previous),
            "Original execution/result/native/product definition changed")
    host_text = host.decode("utf8")
    for old, new in HOST_EDITS:
        require(host_text.count(old) == 1, "Unique reviewed host delta required")
        host_text = host_text.replace(old, new, 1)
    restored_host = host_text
    for old, new in reversed(HOST_EDITS):
        require(restored_host.count(new) == 1, "Unique inverse host delta required")
        restored_host = restored_host.replace(new, old, 1)
    require(restored_host.encode() == host, "Host inverse changed the canonical a089 controller")
    result = dict(originals)
    result["combined_heart_semantics_current.py"] = candidate
    result["combined_host_acceptance_app15.py"] = host_text.encode("utf8")
    result["focus_lifecycle_profile.py"] = focus
    for name, value in result.items():
        if name.endswith(".py"):
            compile(value, name, "exec")
    proof = {"status": "PASS_EXACT_ADDITIVE_APP16_CONTROL_NOT_APPLICATION_ACCEPTANCE",
             "protocol": "app16-shared-control-materialization-v1",
             "sourceCommit": "a089ff29a5c0a7e415aac800844505f099a5561d",
             "originalFiles": ORIGINALS, "files": {name: sha(value) for name, value in result.items()},
             "sharedInsertion": {"offset": offset, "bytes": len(insertion),
                                 "fragmentSHA256": sha(fragment), "inverseRestoresEveryOriginalByte": True,
                                 "unchangedOriginalDefinitions": [name for name, _ in previous]},
             "hostCanonicalSHA256": sha(host),
             "hostChanges": [{"old": old, "new": new, "count": 1} for old, new in HOST_EDITS],
             "hostInverseRestoresEveryCanonicalByte": True,
             "focusMethods": 22, "focusCases": 34,
             "nativeCalls": 0, "applicationBuilds": 0, "XCTestInvocations": 0,
             "historicalT5CallsRepeated": 0, "previousFailureEvidenceChanged": False}
    return result, proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-control", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package = Path(__file__).resolve().parent
    originals = {name: read(args.original_control / name) for name in ORIGINALS}
    host = read(args.source / "Tools/CurrentAppleValidation/combined_heart_semantics/build15/combined_host_acceptance_app15.py")
    values, proof = compose(originals, read(package / "app16_intake.py"), host,
                            read(package / "focus_lifecycle_profile.py"))
    require(args.output.is_absolute() and args.output.parent.resolve() == args.output.parent
            and not args.output.exists(), "Fresh unaliased output directory required")
    args.output.mkdir(mode=0o700)
    for name, value in values.items():
        (args.output / name).write_bytes(value)
    (args.output / "materialization.json").write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": proof["status"], "output": str(args.output), "files": proof["files"]}, sort_keys=True))


if __name__ == "__main__":
    main()
