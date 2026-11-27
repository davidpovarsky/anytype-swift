#!/usr/bin/env python3
"""Prepare the actual Properties state model for a narrowly scoped Linux test.

No execution, network, native service, fake dependency or product admission.
The output omits only SwiftUI availability/import lines and the document-bound
native convenience constructors. The state machine and typed dependencies stay
unchanged. The original Apple source remains the shipping source.
"""
from pathlib import Path
import argparse
import hashlib
import json


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def prepare(inputs, output, variant):
    model_name = "AnyNativePropertyPresentation" + (".original" if variant == "baseline" else "") + ".swift"
    original_model = (inputs / model_name).read_bytes()
    original_tests = (inputs / "AnyNativePropertyPresentationTests.swift").read_bytes()
    model = original_model.decode()
    removals = []

    def replace_once(old, new, reason):
        nonlocal model
        if model.count(old) != 1:
            raise ValueError("Expected exact single source span: " + reason)
        model = model.replace(old, new, 1)
        removals.append({"reason": reason, "old": old, "new": new})

    replace_once("#if canImport(SwiftUI)\nimport Observation\nimport SwiftUI\n", "import Observation\n",
                 "Expose actual Foundation/Observation state model to Linux without pretending SwiftUI exists")
    if not model.endswith("}\n#endif\n"):
        raise ValueError("Unexpected outer SwiftUI scope")
    model = model[:-len("#endif\n")]
    removals.append({"reason": "Remove only the matching outer availability end", "old": "#endif\n", "new": ""})
    start = model.index("    static func native(document: AnyDocumentPresentation,")
    end = model.index("\n}\n\n@MainActor @Observable", start)
    replace_once(model[start:end], "", "Native document/session factory remains Apple-only and is not exercised by the injected typed-operation component test")
    start = model.index("    public init(document: AnyDocumentPresentation, store: AnyNativePropertyStore?)")
    end = model.index("    init(store: AnyNativePropertyStore, operations: AnyNativePropertyPresentationOperations)", start)
    replace_once(model[start:end], "", "Remove only public document convenience initialization; preserve actual internal typed-operation initializer")

    tests = original_tests.decode()
    prefix = "#if canImport(SwiftUI)\n"
    if not tests.startswith(prefix) or not tests.endswith("#endif\n"):
        raise ValueError("Unexpected test availability scope")
    tests = tests[len(prefix):-len("#endif\n")]
    error_enum = (inputs / "AnyUIErrorText.exact.swift").read_bytes()
    error_header = b"import Foundation\nimport PinkhaAnyEngine\nimport PinkhaAnyHost\nimport PinkhaKit\n\n"
    files = {
        "Sources/PinkhaAnyUI/AnyNativePropertyPresentation.swift": model.encode(),
        "Sources/PinkhaAnyUI/AnyUIErrorText.swift": error_header + error_enum,
        "Tests/PinkhaAnyUITests/AnyNativePropertyPresentationTests.swift": tests.encode(),
    }
    for relative, raw in files.items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    proof = {
        "schema": "pinkha.wave2.properties.linux-component-envelope.v1",
        "variant": variant,
        "shippingModelSHA256": sha(original_model),
        "shippingTestsSHA256": sha(original_tests),
        "unchangedProductionErrorEnumSHA256": sha(error_enum),
        "modelEnvelopeChanges": removals,
        "testsEnvelopeChanges": ["Removed only outer canImport(SwiftUI) guard"],
        "outputs": {name: {"bytes": len(raw), "sha256": sha(raw)} for name, raw in files.items()},
        "nativeServiceCalls": 0,
        "appleCompilationClaimed": False,
        "uiOrNativeAcceptanceClaimed": False,
        "scope": "Actual Foundation/Observation presentation model with complete original typed Engine/Host/Integration/Kit dependencies; suspended typed transport fixtures are component evidence only",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / (variant + "-component-envelope.json")).write_text(json.dumps(proof, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"variant": variant, "output": str(output), "outputs": proof["outputs"]}, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--variant", choices=("baseline", "fixed"), required=True)
    args = parser.parse_args()
    prepare(args.inputs, args.output, args.variant)
