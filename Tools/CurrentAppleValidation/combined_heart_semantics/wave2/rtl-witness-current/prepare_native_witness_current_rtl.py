#!/usr/bin/env python3
"""Pair the unchanged native witness with the exact f16a RTL source successor."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

ORIGINAL_WITNESS = "aaa408805488d0d15646569359d698527f58bfa597ad82177ab6c06a6986e4dd"
ORIGINAL_RTL = "80ebc56005110ee78615322f56b876b5b6fd4fae23975b86d249ae05ebcac8ea"
CURRENT_RTL = "f16a16071fadf66ca0b1cd8a0583e41aadf7439e567a7c51daf72d56ad83885c"
EXTRACTED_FUNCTIONS = ("sha", "_pinned_bytes", "source_contract")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def declarations(text):
    return {node.name: ast.get_source_segment(text, node)
            for node in ast.parse(text).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-witness", type=Path, required=True)
    parser.add_argument("--original-rtl", type=Path, required=True)
    parser.add_argument("--current-rtl", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "A new separate output is required")
    original = args.original_witness.read_bytes()
    old_rtl, current_rtl = args.original_rtl.read_bytes(), args.current_rtl.read_bytes()
    require(sha(original) == ORIGINAL_WITNESS and sha(old_rtl) == ORIGINAL_RTL
            and sha(current_rtl) == CURRENT_RTL, "Exact original witness and reviewed RTL pair required")
    text = original.decode()
    require(text.count(ORIGINAL_RTL) == 1 and CURRENT_RTL not in text,
            "Exactly one original complete RTL validator pin required")
    candidate = text.replace(ORIGINAL_RTL, CURRENT_RTL, 1)
    require(candidate.replace(CURRENT_RTL, ORIGINAL_RTL, 1).encode() == original,
            "Complete original witness inverse failed")
    require(declarations(candidate) == declarations(text), "A native witness declaration changed")
    old_functions, current_functions = declarations(old_rtl.decode()), declarations(current_rtl.decode())
    require(all(old_functions[name] == current_functions[name] for name in EXTRACTED_FUNCTIONS),
            "An extracted original compiler-witness function changed")
    proof = {
        "schema": "pinkha-native-witness-current-rtl-source-successor-v1",
        "status": "SOURCE_REVIEW_REQUIRED_RUNTIME_NOT_ADMITTED",
        "materializerSHA256": sha(Path(__file__).read_bytes()),
        "originalWitnessSHA256": ORIGINAL_WITNESS,
        "candidateWitnessSHA256": sha(candidate.encode()),
        "originalRTLProfileSHA256": ORIGINAL_RTL,
        "candidateRTLProfileSHA256": CURRENT_RTL,
        "exactLiteralEdits": [{"before": ORIGINAL_RTL, "after": CURRENT_RTL}],
        "completeOriginalWitnessRestored": True,
        "allOriginalNativeWitnessDeclarationsUnchanged": True,
        "exactExtractedFunctionSHA256": {name: sha(old_functions[name].encode()) for name in EXTRACTED_FUNCTIONS},
        "allThreeExtractedRTLFunctionsByteIdentical": True,
        "originalSelectedSourceAndCompilerProofRequirementsUnchanged": True,
        "futureSourceFreeze": None, "actualProducerReceipt": None, "actualSharedAdmission": None,
        "readyForExecution": False, "testsExecuted": 0, "controlsRerun": 0,
        "compilerInvocations": 0, "nativeCalls": 0,
    }
    args.output.mkdir(parents=True)
    (args.output / "native_compiler_witness.py").write_text(candidate)
    (args.output / "source-inverse.json").write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps(proof, sort_keys=True))


if __name__ == "__main__":
    main()
