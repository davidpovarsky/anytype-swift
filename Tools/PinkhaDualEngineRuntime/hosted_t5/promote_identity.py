#!/usr/bin/env python3
"""Propose one product capability/reader identity promotion from actual receipts.

This source-only tool writes a fresh review packet. It never changes the App,
an existing controller, a ready flag, Git, a simulator, or an account. The final
tuple stays null: the root must separately review/promote the shared producer,
common receipt gate, Native23 reader and all actual new native artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

import profile


def reference(path):
    path = Path(path)
    profile.require(path.is_absolute() and path.is_file() and path.resolve() == path and not path.is_symlink(),
                    "Exact physical original input required")
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": profile.digest(path)}


def propose(args):
    output = args.output
    profile.require(output.is_absolute() and output.parent.resolve() == output.parent and not output.exists()
                    and not output.is_symlink(), "Exclusive fresh source proposal required")
    manifest_ref, assembly_ref, binary_ref = map(reference, (args.native_manifest, args.assembly_receipt, args.native_binary))
    assembly = profile.strict_json(args.assembly_receipt.read_bytes())
    profile.require(assembly["status"] == "PASS_ASSEMBLED_TWO_QUALIFIED_SLICES_NOT_APP_ACCEPTANCE"
        and assembly["sourceManifestSHA256"] == manifest_ref["sha256"]
        and assembly["runtimeIdentity"]["sourceManifestSHA256"] == manifest_ref["sha256"]
        and assembly["inputs"]["simulator"]["binarySHA256"] == binary_ref["sha256"],
        "Actual original qualified simulator/device assembly required for a promotion proposal")
    version = "pinkha-dual-runtime-v1-" + manifest_ref["sha256"]
    profile.require(assembly["fullAnyRuntimeVersion"] == version, "Original full native runtime identity differs")
    sources_path = Path(__file__).with_name("original_sources.json")
    profile.require(profile.digest(sources_path) == profile.MANIFEST_SHA256, "Current exact T5 original source manifest required")
    sources = profile.strict_json(sources_path.read_bytes())
    old = (args.source / profile.CAPABILITY).read_bytes()
    pin = sources["files"][profile.CAPABILITY]
    profile.require(len(old) == pin["bytes"] and hashlib.sha256(old).hexdigest() == pin["sha256"],
                    "Current product capability preimage differs; no blind identity replacement")
    expression = rb'(public static let unifiedRuntimeVersion\s*=\s*")([^"\n]+)(")'
    matches = list(re.finditer(expression, old))
    profile.require(len(matches) == 1, "One exact original unified capability declaration required")
    match = matches[0]; previous = match[2]
    profile.require(previous != version.encode(), "No source promotion is needed for identical native identity")
    after = old[:match.start(2)] + version.encode() + old[match.end(2):]
    inverse = after[:match.start(2)] + previous + after[match.start(2) + len(version):]
    profile.require(inverse == old, "Capability inverse must restore every original byte")
    proposed_sources = json.loads(json.dumps(sources))
    proposed_sources["sourceCommit"] = None
    proposed_sources["reviewedOriginalCommit"] = sources["sourceCommit"]
    proposed_sources["sourcePromotion"] = "UNPUBLISHED_REVIEW_PROPOSAL_NOT_NATIVE_OR_APP_ACCEPTANCE"
    proposed_sources["files"][profile.CAPABILITY] = {"bytes": len(after), "sha256": hashlib.sha256(after).hexdigest(),
        "gitBlob": hashlib.sha1(b"blob " + str(len(after)).encode() + b"\0" + after).hexdigest()}
    proposed_manifest = (json.dumps(proposed_sources, sort_keys=True, indent=2) + "\n").encode()
    new_manifest_sha = hashlib.sha256(proposed_manifest).hexdigest()
    current_profile = Path(__file__).with_name("profile.py").read_text()
    needle = 'MANIFEST_SHA256 = "' + profile.MANIFEST_SHA256 + '"'
    profile.require(current_profile.count(needle) == 1, "Exact current runtime manifest binding required")
    proposed_profile = current_profile.replace(needle, 'MANIFEST_SHA256 = "' + new_manifest_sha + '"')
    output.mkdir(mode=0o700)
    (output / "product-capability.before.swift").write_bytes(old)
    (output / "product-capability.proposal.swift").write_bytes(after)
    (output / "original_sources.proposal.json").write_bytes(proposed_manifest)
    (output / "profile.proposal.py").write_text(proposed_profile)
    evidence = {"schema": "pinkha-t5-product-native-promotion-proposal-v1", "readyForRuntime": False, "finalProducerTuple": None,
        "status": "REVIEW_REQUIRED_SOURCE_PROPOSAL_ONLY", "originalNativeManifest": manifest_ref, "originalAssembly": assembly_ref,
        "originalSimulatorBinary": binary_ref, "nativeRuntimeVersion": version,
        "capability": {"path": profile.CAPABILITY, "before": pin, "after": proposed_sources["files"][profile.CAPABILITY],
            "inverse": {"beforeLiteral": previous.decode(), "afterLiteral": version, "replacements": 1,
                        "wholeOriginalBytesRestored": True, "unrelatedCapabilitiesChanged": False}},
        "profileInverse": {"before": profile.MANIFEST_SHA256, "after": new_manifest_sha, "replacements": 1,
            "wholeOriginalBytesRestored": proposed_profile.replace('MANIFEST_SHA256 = "' + new_manifest_sha + '"', needle) == current_profile},
        "sharedDependenciesStillRequireRootPromotion": profile.DEPENDENCIES,
        "requiredNextEvidence": ["published final product commit/tree", "actual shared producer and common admission for the native tuple",
            "actual 57/10/2 compiler/source/FileList receipts", "selected hosted Node executable/version/backend",
            "fresh original T5 fixtures, core2, both R08 appearances and quote freshness", "ciphertext artifact readback and exact private receiver restore"],
        "runtimeOverridesInstalled": False, "oldFixturesAdmitted": False, "sourceEdited": False, "testsExecuted": 0}
    (output / "promotion-proposal.json").write_text(json.dumps(evidence, sort_keys=True, indent=2) + "\n")
    return {"status": evidence["status"], "proposalSHA256": profile.digest(output / "promotion-proposal.json"), "readyForRuntime": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "native-manifest", "assembly-receipt", "native-binary", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    print(json.dumps(propose(parser.parse_args()), sort_keys=True))


if __name__ == "__main__":
    main()
