#!/usr/bin/env python3
"""Reuse the ten actual Kit methods from 44969141133; never run Swift here."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

import run_packages as gate

PROOF = "docs/validation/20261122-related-read-mac-observed"
OLD_PROOF = "docs/validation/20261122-related-read-package-controls"
SOURCE = "f6d565064462d73300e66861c8113dd6e6a085a9"
ZIP = "24dfdf81711cba9abd3af48c036790db700f725077d933eb083fa21357851969"


def git_digest(root, name):
    return hashlib.sha256(subprocess.check_output(["git", "-C", str(root), "show", "HEAD:" + name])).hexdigest()


def function_source(path, name):
    text = path.read_text(encoding="utf-8")
    matches = [node for node in ast.walk(ast.parse(text))
               if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name]
    gate.require(len(matches) == 1, "one preserved function required: " + name)
    return ast.get_source_segment(text, matches[0])


def admit_controls(root):
    proof = root / PROOF
    current = gate.read_json(proof / "parser-controls.json")
    gate.require(current["status"] == "PASS_SIXTEEN_AFFECTED_PARSER_CONTROLS", "parser controls not qualified")
    for name, expected in current["sourceSHA256"].items():
        gate.require(git_digest(root, name) == expected, "parser control source differs: " + name)
    names = []
    for attempt in current["attempts"]:
        log = proof / attempt["log"]
        gate.require(gate.digest(log) == attempt["sha256"], "original parser control log differs")
        text = log.read_text(encoding="utf-8")
        for name in attempt["passedMethods"]:
            gate.require(text.count(name + " (test_packages.RelatedReadPackageControls." + name + ") ... ok") == 1,
                         "missing named parser control pass")
            names.append(name)
    gate.require(len(names) == len(set(names)) == 16, "parser control coverage differs")

    old = gate.read_json(root / OLD_PROOF / "evidence.json")
    gate.require(old["status"] == "PASS_NEW_PARSER_11_AND_PROCESS_5_CONTROLS", "original controller proof differs")
    for name in ("run_packages.py", "test_packages.py"):
        gate.require(gate.digest(proof / "before" / name) == old["sourceSHA256"]["Tools/RelatedReadAuthority/" + name],
                     "original controller source differs")
    for name in ("run_command", "require", "digest", "validate_host"):
        gate.require(function_source(proof / "before/run_packages.py", name)
                     == function_source(root / "Tools/RelatedReadAuthority/run_packages.py", name),
                     "retained process/host control implementation changed: " + name)
    name = "testWrongDestinationOrXcodeDoesNotCountAsAppleProof"
    gate.require(function_source(proof / "before/test_packages.py", name)
                 == function_source(root / "Tools/RelatedReadAuthority/test_packages.py", name),
                 "retained host control changed")
    for name in ("test_process_ownership.py", "Fixtures/kit-test-profile.json"):
        gate.require(git_digest(root, "Tools/RelatedReadAuthority/" + name)
                     == old["sourceSHA256"]["Tools/RelatedReadAuthority/" + name], "retained source differs")
    for name, expected in (("original-tool-output.log", old["parserControls"]["originalToolLogSHA256"]),
                           ("original-process-controls.log", old["processControls"]["logSHA256"])):
        gate.require(gate.digest(root / OLD_PROOF / name) == expected, "retained control log differs")
    for name, expected in old["processControls"]["existingHelperGitBlobsAt816e3748d5499e7f5a64783506057c4dca0d83d3"].items():
        gate.require(gate.git(root, "rev-parse", "HEAD:Tools/PinkhaSimulatorGate/" + name) == expected,
                     "retained owned-process helper differs: " + name)
    return dict(status="SOURCE_BOUND_CONTROLS_REUSED", affectedParserControls=16,
                unchangedHostControls=1, unchangedProcessControls=5, controlsRerun=0)


def admit(root, kit):
    proof = root / PROOF
    manifest = gate.read_json(proof / "MANIFEST.json")
    gate.require((manifest["runID"], manifest["jobID"], manifest["sourceCommit"], manifest["artifactID"],
                  manifest["artifactZipSHA256"], manifest["originalWorkflowConclusion"])
                 == (44969141133, 137044839873, SOURCE, 14732218185, ZIP, "failure"),
                 "original producer/artifact identity differs")
    actual_files = {str(p.relative_to(proof)) for p in (proof / "original").rglob("*") if p.is_file()}
    gate.require(actual_files == set(manifest["originalFilesSHA256"]), "original artifact inventory differs")
    for name, expected in manifest["originalFilesSHA256"].items():
        gate.require(gate.digest(proof / name) == expected, "original artifact bytes changed: " + name)
    original = proof / "original/related-read-authority/kit-related-current-access"
    receipt = gate.read_json(original / "receipt.json")
    gate.require(receipt["status"] == "FAIL"
                 and receipt["error"] == "ValueError: missing, duplicate or unexpected actual argument",
                 "original failed qualification must remain unchanged")
    gate.require(receipt["appSourceCommit"] == SOURCE and receipt["kitCommit"] == gate.KIT
                 and receipt["actualKitCheckout"]["commit"] == gate.KIT,
                 "original source checkout differs")
    gate.require(receipt["contractSHA256"] == gate.digest(root / gate.CONTRACT), "original selection contract changed")
    gate.validate_host(receipt["platform"]["system"], receipt["platform"]["architecture"], receipt["xcodeVersion"])
    gate.require(receipt["swiftVersion"].startswith("Apple Swift version 6.4 "), "unreviewed producer Swift format")
    for key, stem in (("resolution", "resolve"), ("execution", "original-test")):
        execution = receipt[key]
        command = gate.read_json(original / (stem + ".command.json"))
        gate.require(execution["returncode"] == command["return_code"] == 0
                     and execution["ownedGroupQuiescence"]["status"] == "PASS"
                     and execution["ownedGroupQuiescence"]["live_members"] == 0,
                     "original process/cleanup did not finish cleanly")
        gate.require(gate.digest(original / (stem + ".command.json")) == execution["originalCommandSHA256"]
                     and gate.digest(original / (stem + ".log")) == execution["logSHA256"],
                     "original command/log binding differs")
    gate.exact_source(kit, gate.KIT)
    _, all_methods = gate.load_profile(root, "kit-related-current-access", kit)
    current = gate.inspect_sources(kit, all_methods)
    gate.require({name: git_digest(kit, name) for name in current} == receipt["sourceSHA256"],
                 "retained Kit Git source differs")
    retained = [m for m in all_methods if not m.top_level]
    pending = [m for m in all_methods if m.top_level]
    methods = gate.qualify_stream(original / "original-events.jsonl", retained, original / "original-test.log")
    gate.require((len(methods), sum(m["actualCases"] for m in methods), len(pending)) == (10, 12, 5),
                 "retained versus pending coverage differs")
    return dict(status="PASS_REQUALIFIED_ORIGINAL_TEN_KIT_METHODS", sourceRunID=44969141133,
                sourceCommit=SOURCE, kitCommit=gate.KIT, originalWorkflowConclusion="failure",
                originalReceiptPreserved=True, originalPostQualificationSourceGuard="NOT_REACHED",
                currentKitGitBlobsMatchOriginalPreExecutionHashes=True,
                actualMethods=10, actualArgumentCases=12, productTestsRerun=0, methods=methods,
                pendingMethods=[m.key for m in pending], pendingMethodsAccepted=False,
                originalEventsSHA256=gate.digest(original / "original-events.jsonl"),
                originalLogSHA256=gate.digest(original / "original-test.log"),
                originalArtifactSHA256=ZIP)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--kit-root", type=Path, required=True)
    args = parser.parse_args()
    root, kit = args.root.resolve(), args.kit_root.resolve()
    gate.exact_source(root, args.source_sha)
    controls = admit_controls(root)
    receipt = admit(root, kit)
    gate.exact_source(root, args.source_sha)
    gate.exact_source(kit, gate.KIT)
    output = root / "build/related-read-authority/kit-original-ten"
    output.mkdir(parents=True, exist_ok=False)
    receipt.update(consumerSourceCommit=args.source_sha, controls=controls)
    (output / "reuse.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ("status", "actualMethods", "actualArgumentCases", "productTestsRerun")}))


if __name__ == "__main__":
    main()
