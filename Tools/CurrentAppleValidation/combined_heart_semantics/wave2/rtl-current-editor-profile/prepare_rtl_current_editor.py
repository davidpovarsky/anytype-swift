#!/usr/bin/env python3
"""Qualify one fixed RTL profile source-pin successor; no runtime admission."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

ORIGINAL_PROFILE = "80ebc56005110ee78615322f56b876b5b6fd4fae23975b86d249ae05ebcac8ea"
OLD_EDITOR = "e25deb24f68be376fc3bd55a9b3f97fd755949c104bcec16f3368ce679c4733a"
CURRENT_EDITOR = "8b461efe44868904b826da7b601c1537fd1c164705f861b15920143a556caac5"
CURRENT_COMMIT = "3559f6010d1ae837d12e4eda9fd7cbcb40870a3d"
CURRENT_SOURCES = {
    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeEditor.swift": CURRENT_EDITOR,
    "Anytype/Sources/Pinkha/RTL/PinkhaTextBlockLeadingMarkerAdapter.swift": "45c659a2923733421c9760d95dbe5b1560d1aa7b3123813ab93f86c2d313d38c",
    "Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/Stylers/TextBlockLeadingView.swift": "2f2bf0a7bd83c6deccf0f9efc531950dca3fb739eea012a949d559e98c0468cd",
    "AnyTypeTests/Pinkha/PinkhaTextBlockLeadingMarkerTests.swift": "dafd3d25b80cfdec01f5b47f70adc59d52d03db36ac9a673b70059e46637ac21",
    "AnyTypeTests/Pinkha/AnyNativeEmptyParagraphDirectionTests.swift": "656ab17484da23139005fb84a36376802f23c5fdf66c9766c7860a895c27e999",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def definitions(text):
    return {node.name: ast.dump(node, include_attributes=False)
            for node in ast.parse(text).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-profile", type=Path, required=True)
    parser.add_argument("--source-readback", type=Path, required=True)
    parser.add_argument("--styled-inverse", type=Path, required=True)
    parser.add_argument("--hanlin-inverse", type=Path, required=True)
    parser.add_argument("--typography-inverse", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "A new output directory is required")
    original = args.original_profile.read_bytes()
    require(sha(original) == ORIGINAL_PROFILE, "Original complete RTL profile changed")
    original_text = original.decode()
    require(original_text.count(OLD_EDITOR) == 1 and CURRENT_EDITOR not in original_text,
            "Expected exactly one original full-editor pin")
    candidate = original_text.replace(OLD_EDITOR, CURRENT_EDITOR, 1)
    require(candidate.replace(CURRENT_EDITOR, OLD_EDITOR, 1).encode() == original,
            "Whole original profile inverse failed")
    require(definitions(candidate) == definitions(original_text), "An original RTL helper declaration changed")
    original_ast, candidate_ast = ast.parse(original_text), ast.parse(candidate)
    def assignments(tree):
        return {tuple(ast.dump(target, include_attributes=False) for target in node.targets): ast.dump(node.value, include_attributes=False)
                for node in tree.body if isinstance(node, ast.Assign)}
    before, after = assignments(original_ast), assignments(candidate_ast)
    changed = [key for key in before if before[key] != after[key]]
    require(set(before) == set(after) and changed == [("Name(id='PRODUCT_SOURCES', ctx=Store())",)],
            "Any assignment other than the one product-source map changed")
    readback = json.loads(args.source_readback.read_bytes())
    require(readback["repository"] == "davidpovarsky/anytype-swift" and readback["commit"] == CURRENT_COMMIT,
            "Unexpected observed source commit")
    require(len(readback["files"]) == len(CURRENT_SOURCES)
            and {row["path"] for row in readback["files"]} == set(CURRENT_SOURCES), "Current source inventory differs")
    checked = []
    editor = None
    for row in readback["files"]:
        require(row["encoding"] == "utf-8", "UTF-8 source required")
        data = row["content"].encode()
        require(sha(data) == CURRENT_SOURCES[row["path"]], "Current source differs: " + row["path"])
        git_blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        require(git_blob == row["gitBlob"], "Primary Git source blob differs")
        checked.append({"path": row["path"], "sha256": sha(data), "gitBlob": git_blob, "bytes": len(data)})
        if row["path"].endswith("/AnyNativeEditor.swift"):
            editor = data.decode()
    styled = json.loads(args.styled_inverse.read_bytes())
    hook = json.loads(args.hanlin_inverse.read_bytes())
    typography = json.loads(args.typography_inverse.read_bytes())
    chain = [
        {"sourceCommit": "7380a797d13b279b6d19e43ade7af1929089b8ef", "name": "styled-observation",
         "beforeSHA256": "c0c045570318f03ac38633e3b48dd6602506b748e0866594ba2f434a523bd4f8", "afterSHA256": CURRENT_EDITOR,
         "edits": [{"before": item["old"], "after": item["new"]} for item in styled["changes"]]},
        {"sourceCommit": "dfbb481102226e5484b5b8e4dd730661f9b03d14", "name": "native-Hanlin-entry",
         "beforeSHA256": "4b7a6feaa4557a63183789549ae9fe498ef2d988f0b7516f39947891a3c1dd3a",
         "afterSHA256": "c0c045570318f03ac38633e3b48dd6602506b748e0866594ba2f434a523bd4f8",
         "edits": [{"before": hook["oldCall"], "after": hook["newCall"]}]},
        {"sourceCommit": "33e31c64ca9e35e258a4d64cfe8690b08a6cbc39", "name": "original-design-typography",
         "beforeSHA256": "26a3876cab8926445449c07542d5ebdda01e6eaf33ee0cc27fd03d072540ec61",
         "afterSHA256": "4b7a6feaa4557a63183789549ae9fe498ef2d988f0b7516f39947891a3c1dd3a",
         "edits": [{"before": item["old"], "after": item["new"]}
                   for key in ("exactChanges", "reviewCorrectionChanges", "bodyWeightCorrectionChanges")
                   for item in typography[key]]},
        {"sourceCommit": "dc582ba3239d6dcb66dbe1f7098b95349e4289f9", "name": "shared-block-catalog-menu",
         "beforeSHA256": OLD_EDITOR,
         "afterSHA256": "26a3876cab8926445449c07542d5ebdda01e6eaf33ee0cc27fd03d072540ec61",
         "edits": [{"before": "                Task { await presentation?.addParagraph(before: id) }\n            }\n        ])",
                    "after": "                Task { await presentation?.addParagraph(before: id) }\n            },\n            AnyNativeBlockCreationMenu.before(id, presentation: presentation)\n        ])"}]},
    ]
    restored = editor
    for stage in chain:
        require(sha(restored.encode()) == stage["afterSHA256"], "Editor stage input differs: " + stage["name"])
        for change in reversed(stage["edits"]):
            require(restored.count(change["after"]) == 1, "Unique editor inverse missing: " + stage["name"])
            restored = restored.replace(change["after"], change["before"], 1)
        require(sha(restored.encode()) == stage["beforeSHA256"], "Complete editor inverse differs: " + stage["name"])
    require(sha(restored.encode()) == OLD_EDITOR, "Original RTL editor source was not restored")
    inverse = {"schema": "pinkha-rtl-current-editor-source-inverse-v1", "profileOriginalSHA256": ORIGINAL_PROFILE,
               "profileCandidateSHA256": sha(candidate.encode()),
               "profileEdits": [{"before": OLD_EDITOR, "after": CURRENT_EDITOR}],
               "editorInverseChain": chain, "originalCompleteEditorRestoredSHA256": sha(restored.encode()),
               "allOriginalRTLFunctionsClassesAndTestInventoriesUnchanged": True}
    receipt = {
        "schema": "pinkha-rtl-current-editor-source-qualification-v1", "status": "SOURCE_ONLY_NOT_RUNTIME_ADMISSION",
        "observedSourceCommit": CURRENT_COMMIT, "sourceRows": checked,
        "sourceReadbackSHA256": sha(args.source_readback.read_bytes()),
        "materializerSHA256": sha(Path(__file__).read_bytes()),
        "profileOriginalSHA256": ORIGINAL_PROFILE, "profileCandidateSHA256": sha(candidate.encode()),
        "sourceInverseSHA256": sha((json.dumps(inverse, indent=2) + "\n").encode()),
        "profileLiteralChanges": 1, "originalHelperDefinitionsUnchanged": len(definitions(candidate)),
        "originalEditorSourceRestoredThroughPublishedTranches": 4,
        "declaredMethodsUnchanged": 6, "declaredCasesUnchanged": 10,
        "originalCompilerWitnessEnumerationCaseValidatorsUnchanged": True,
        "actualProducerReceipt": None, "actualSharedAdmission": None, "futureSourceFreeze": None,
        "readyForExecution": False, "appleInvocations": 0, "compilerInvocations": 0,
        "nativeCalls": 0, "XCTestMethodsExecuted": 0, "originalPortableControlsRerun": 0,
    }
    args.output.mkdir(parents=True)
    (args.output / "rtl_hosted_profile.py").write_text(candidate)
    for name, value in (("source-inverse.json", inverse), ("source-qualification.json", receipt)):
        (args.output / name).write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
