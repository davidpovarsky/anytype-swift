"""Bind the reviewed App16 producer to one root-approved source admission.

This adapter preserves the original producer's build/runtime/dependency/product
checks. It adds compiler-use evidence and keeps control source separate from the
compiled app source. Preparation alone never invokes Xcode.
"""
import argparse
import ast
import hashlib
import json
import os
import pathlib
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys


BASE_COMMIT = "204f8fbb25c3b21f419fc1a8818eb46ed492e561"
BASE_SHA256 = "9b1405ea44ba9cce3fca47a88127fc798fedab3d1b05f6e3728da3597d19929c"
SOURCE_ROOT = "/Users/m1/development/anytype-d-active-20261125/main14/source"
APP_DERIVED = "/Users/m1/development/anytype-d-active-20261125/main14/app-derived"
MANDATORY_NATIVE = (
    "AnyTypeTests/Pinkha/TextBlockFocusLifecycleTests.swift",
    "AnyTypeTests/Pinkha/TextViewLinkGestureArbitrationTests.swift",
    "AnyTypeTests/Pinkha/PinkhaMiniAppsNativePreparationTests.swift",
)


def w3_require(value, message):
    if not value:
        raise ValueError(message)


def w3_sha(path):
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def w3_write(path, value):
    path = pathlib.Path(path)
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def w3_file(path):
    path = pathlib.Path(path)
    w3_require(path.is_file() and not path.is_symlink(), "Expected an original regular file: " + str(path))
    return {"bytes": path.stat().st_size, "sha256": w3_sha(path)}


def w3_project_inventory(project):
    project = pathlib.Path(project)
    w3_require(project.is_dir() and not project.is_symlink(), "Generated project is not a physical directory")
    entries = {}
    for path in sorted(project.rglob("*")):
        w3_require(not path.is_symlink(), "Unexpected generated project symlink")
        mode = stat.S_IMODE(path.stat().st_mode)
        relative = str(path.relative_to(project))
        if path.is_file():
            entries[relative] = dict(kind="file", mode=mode, **w3_file(path))
        elif path.is_dir():
            entries[relative] = {"kind": "directory", "mode": mode}
        else:
            raise ValueError("Unexpected generated project node: " + relative)
    w3_require("project.pbxproj" in entries and
               "xcshareddata/xcschemes/PinkhaPrebuiltUI.xcscheme" in entries,
               "Generated UI project and exact scheme are required")
    return {"schema": "pinkha-generated-ui-project-inventory-v1", "root": str(project), "entries": entries}


def w3_sources(relative_paths, source_root, compiled_root, source_before):
    source_root, compiled_root = pathlib.Path(source_root), pathlib.Path(compiled_root)
    w3_require(relative_paths and len(relative_paths) == len(set(relative_paths)), "Selected source paths must be unique")
    rows = []
    for relative in relative_paths:
        path = pathlib.PurePosixPath(relative)
        w3_require(not path.is_absolute() and ".." not in path.parts and path.suffix == ".swift", "Invalid selected Swift source")
        expected = source_before["files"][relative]
        original, compiled = source_root / relative, compiled_root / relative
        w3_require(w3_file(original) == expected == w3_file(compiled), "Compiled source differs: " + relative)
        rows.append(dict(repositoryPath=relative, compiledPath=str(compiled), **expected))
    return rows


def w3_compiler_invocations(log, module, filelist):
    witnesses = []
    with pathlib.Path(log).open(errors="strict") as stream:
        for number, line in enumerate(stream, 1):
            if ".SwiftFileList" not in line or "swiftc" not in line:
                continue
            try:
                tokens = shlex.split(line)
            except ValueError:
                continue
            if not any(pathlib.Path(token).name == "swiftc" for token in tokens):
                continue
            names = [tokens[i + 1] for i, token in enumerate(tokens[:-1]) if token == "-module-name"]
            lists = [token[1:] for token in tokens if token.startswith("@")]
            if names == [module] and any(item.casefold() == str(filelist).casefold() for item in lists):
                witnesses.append({"lineNumber": number,
                                  "lineSHA256": hashlib.sha256(line.rstrip("\r\n").encode()).hexdigest(),
                                  "moduleName": module})
    w3_require(witnesses, "No actual swiftc invocation uses selected FileList in original build log")
    return witnesses


def w3_compiler_lists(derived, module, required_sources, log, evidence, phase):
    derived, evidence = pathlib.Path(derived), pathlib.Path(evidence)
    expected_paths = [row["compiledPath"] for row in required_sources]
    folded = [path.casefold() for path in expected_paths]
    w3_require(len(folded) == len(set(folded)), "Case-colliding source paths cannot qualify")
    inventory = []
    for path in sorted((derived / "Build/Intermediates.noindex").rglob("*SwiftFileList")):
        if not any(part.casefold() == (module + ".build").casefold() for part in path.parts):
            continue
        if not path.is_file() or path.is_symlink():
            continue
        lines = [line.strip().strip('"') for line in path.read_text().splitlines()]
        normalized = [line.casefold() for line in lines]
        if not all(normalized.count(item) == 1 for item in folded):
            continue
        # Case normalization is permitted only for the same actual APFS source.
        for expected, source_row in zip(expected_paths, required_sources):
            actual = pathlib.Path(lines[normalized.index(expected.casefold())])
            w3_require(actual.is_file() and actual.samefile(expected) and
                       w3_file(actual) == {key: source_row[key] for key in ("bytes", "sha256")},
                       "Compiler source path is not the exact selected source")
        witnesses = w3_compiler_invocations(log, module, path)
        retained = evidence / (phase + "-compiler-" + str(len(inventory)) + ".SwiftFileList")
        with retained.open("xb") as stream:
            stream.write(path.read_bytes())
        w3_require(w3_sha(retained) == w3_sha(path), "Original compiler input retention differs")
        inventory.append({"path": str(retained), "originalPath": str(path),
                          "sha256": w3_sha(path), "requiredSourcePaths": expected_paths,
                          "compilerInvocation": witnesses[0], "compilerInvocations": witnesses})
    w3_require(inventory, "Actual selected target compiler FileList is absent or incomplete")
    return inventory


def w3_native_proof():
    rows = w3_sources(WAVE3_ADMISSION["selectedNativeTestSources"], SOURCE, SOURCE, before)
    log = EVIDENCE / "app/original.log"
    proof = {"schema": "pinkha-exact-native-compiler-inputs-v1",
             "status": "PASS_EXACT_NATIVE_COMPILER_INPUTS_NOT_TEST_EXECUTION",
             "sourceCommit": EXPECTED, "requiredSources": rows,
             "buildLog": {"path": str(log), "sha256": w3_sha(log)},
             "actualCompilerFileLists": w3_compiler_lists(APP_DERIVED, "AnytypeTests", rows, log, EVIDENCE, "native"),
             "originalCompilerQualificationSHA256": w3_sha(EVIDENCE / "new-uikit-compiler-inputs.json"),
             "testsExecuted": 0}
    w3_write(EVIDENCE / "native-selected-compiler-inputs.json", proof)


def w3_ui_before(ui_source, project, selected):
    copy_path = EVIDENCE / "original-ui-copy.json"
    copy = json.loads(copy_path.read_text())
    w3_require(copy["generatorSHA256"] == WAVE3_ADMISSION["pins"]["uiGeneratorSHA256"], "UI generator changed")
    w3_require(copy["generatedProject"] == str(project), "Generated UI project identity changed")
    expected = {row["path"]: row["sha256"] for row in copy["copiedFiles"]}
    w3_require(len(expected) == len(copy["copiedFiles"]) and set(expected) == set(selected), "UI copied source inventory differs")
    for relative in selected:
        w3_require(w3_sha(SOURCE / relative) == expected[relative] == w3_sha(ui_source / relative),
                   "Original UI copy bytes differ before compilation")
    selected_swift = sorted(path for path in selected if path.endswith(".swift"))
    w3_require(set(WAVE3_ADMISSION["selectedUITestSources"]).issubset(selected_swift), "Selected UI sources are missing")
    rows = w3_sources(selected_swift, SOURCE, ui_source, before)
    inventory = w3_project_inventory(project)
    inventory_path = EVIDENCE / "generated-ui-project-before.json"
    w3_write(inventory_path, inventory)
    return {"requiredSources": rows, "copiedFiles": expected, "generatedProject": inventory,
            "originalUICopySHA256": w3_sha(copy_path),
            "generatedProjectBefore": {"path": str(inventory_path), "sha256": w3_sha(inventory_path)}}


def w3_ui_after(snapshot, ui_source, project):
    for relative, expected in snapshot["copiedFiles"].items():
        w3_require(w3_sha(SOURCE / relative) == expected == w3_sha(ui_source / relative),
                   "Original UI copy changed while building")
    rows = w3_sources([row["repositoryPath"] for row in snapshot["requiredSources"]], SOURCE, ui_source, before)
    w3_require(rows == snapshot["requiredSources"], "Compiled UI source bytes changed while building")
    inventory = w3_project_inventory(project)
    w3_require(inventory == snapshot["generatedProject"], "Generated project or scheme changed while building")
    inventory_path = EVIDENCE / "generated-ui-project-after.json"
    w3_write(inventory_path, inventory)
    copy_path = EVIDENCE / "original-ui-copy.json"
    w3_require(w3_sha(copy_path) == snapshot["originalUICopySHA256"], "UI copy receipt changed")
    log = EVIDENCE / "ui/original.log"
    proof = {"schema": "pinkha-exact-ui-compiler-inputs-v1",
             "status": "PASS_EXACT_UI_COPY_PROJECT_AND_COMPILER_INPUTS_NOT_TEST_EXECUTION",
             "sourceCommit": EXPECTED, "originalUICopySHA256": w3_sha(copy_path),
             "generatorSHA256": WAVE3_ADMISSION["pins"]["uiGeneratorSHA256"],
             "requiredSources": rows, "generatedProjectBefore": snapshot["generatedProjectBefore"],
             "generatedProjectAfter": {"path": str(inventory_path), "sha256": w3_sha(inventory_path)},
             "buildLog": {"path": str(log), "sha256": w3_sha(log)},
             "actualCompilerFileLists": w3_compiler_lists(ROOT / "ui-derived", "PinkhaStage1AcceptanceUITests", rows, log, EVIDENCE, "ui"),
             "testsExecuted": 0}
    w3_write(EVIDENCE / "ui-compiled-inputs.json", proof)


def w3_final_bindings():
    w3_control_admission()
    return {"originalUICopySHA256": w3_sha(EVIDENCE / "original-ui-copy.json"),
            "uiCompilationProof": {"path": str(EVIDENCE / "ui-compiled-inputs.json"),
                                   "sha256": w3_sha(EVIDENCE / "ui-compiled-inputs.json")},
            "nativeCompilationProof": {"path": str(EVIDENCE / "native-selected-compiler-inputs.json"),
                                       "sha256": w3_sha(EVIDENCE / "native-selected-compiler-inputs.json")},
            "sourceBeforeSHA256": w3_sha(EVIDENCE / "source-before.json"),
            "sourceAfterSHA256": w3_sha(EVIDENCE / "source-after.json"),
            "controlAdmission": WAVE3_CONTROL}


def w3_control_admission():
    manifest = WAVE3_CONTROL["admission"]
    w3_require(w3_sha(manifest["path"]) == manifest["sha256"], "Root build admission changed")
    retention = WAVE3_CONTROL["originalRetention"]
    w3_require(w3_sha(retention["path"]) == retention["sha256"], "Original preservation receipt changed")
    w3_require(json.loads(pathlib.Path(manifest["path"]).read_text()) == WAVE3_ADMISSION,
               "Root build admission content differs")


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require_digest(value, name):
    if not isinstance(value, str) or re.fullmatch("[0-9a-f]{64}", value) is None:
        raise ValueError("An exact SHA256 is required for " + name)


def load_admission(path, expected_digest, accepted_source):
    require_digest(expected_digest, "root admission")
    if digest(path) != expected_digest:
        raise ValueError("Root-approved admission bytes differ")
    data = json.loads(Path(path).read_text())
    if data["schema"] != "pinkha-root-frozen-build-admission-v1" or data["readyForBuild"] is not True:
        raise ValueError("A finalized build admission is required")
    if re.fullmatch("[0-9a-f]{40}", accepted_source) is None or data["appSourceSHA"] != accepted_source:
        raise ValueError("An exact root-approved app source is required")
    if data["sourceRoot"] != SOURCE_ROOT or data["appDerived"] != APP_DERIVED:
        raise ValueError("This controller reuses only the reviewed physical source and App DerivedData")
    root = Path(data["buildRoot"])
    if root.parent != Path(SOURCE_ROOT).parent.parent or not root.name.startswith("main16-wave3-"):
        raise ValueError("A separate Wave3 build root is required")
    for key, value in data["pins"].items():
        require_digest(value, key)
    for key in ("sourceStaging", "cacheQualification", "originalRetention"):
        require_digest(data[key]["sha256"], key)
    for key in ("selectedNativeTestSources", "selectedUITestSources"):
        values = data[key]
        if not values or len(values) != len(set(values)) or any(not p.endswith(".swift") or ".." in Path(p).parts or Path(p).is_absolute() for p in values):
            raise ValueError("Complete unique selected test source paths are required")
    if not set(MANDATORY_NATIVE).issubset(data["selectedNativeTestSources"]):
        raise ValueError("Original focus and MiniApps native compiler checks must remain")
    if not {"PinkhaStage1Acceptance/Tests/PinkhaT5NativeAcceptanceUITests.swift",
            "PinkhaStage1Acceptance/Tests/MiniAppsNativeAcceptanceUITests.swift"}.issubset(data["selectedUITestSources"]):
        raise ValueError("T5 and MiniApps UI sources must be selected")
    return data


def function_source(source, name):
    node = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == name)
    return ast.get_source_segment(source, node)


def expand_controller(base, admission, admission_path, admission_digest, adapter_digest):
    if hashlib.sha256(base.encode()).hexdigest() != BASE_SHA256:
        raise ValueError("The reviewed 204f8fbb producer bytes differ")
    candidate, changes = base, []

    def replace(old, new, count=None):
        nonlocal candidate
        actual = candidate.count(old)
        if actual == 0 or (count is not None and actual != count):
            raise ValueError("Reviewed producer structure changed: " + old[:100])
        if old == new:
            return
        candidate = candidate.replace(old, new)
        changes.append({"old": old, "new": new, "count": actual})

    replace('ROOT=pathlib.Path("/Users/m1/development/anytype-d-active-20261125/main16-wave2-20261127")',
            "ROOT=pathlib.Path(" + repr(admission["buildRoot"]) + ")", 1)
    replace("EXPECTED=sys.argv[1]", "EXPECTED=" + repr(admission["appSourceSHA"]), 1)
    replace('assert EXPECTED=="a089ff29a5c0a7e415aac800844505f099a5561d"',
            "assert EXPECTED==" + repr(admission["appSourceSHA"]), 1)
    replace('ROOT/"native-materialization-8ac"', "pathlib.Path(" + repr(admission["nativeMaterializationRoot"]) + ")")
    replace('ROOT/"native-materialization-8ac/receipt.json"', "pathlib.Path(" + repr(admission["nativeMaterializationRoot"] + "/receipt.json") + ")")
    replace('ROOT/"native-materialization-8ac/framework-files.json"', "pathlib.Path(" + repr(admission["nativeMaterializationRoot"] + "/framework-files.json") + ")")
    replace('ROOT/"source-staging1/receipt.json"', "pathlib.Path(" + repr(admission["sourceStaging"]["path"]) + ")")
    replace('ROOT/"cache-requalification1/receipt.json"', "pathlib.Path(" + repr(admission["cacheQualification"]["path"]) + ")")
    replacements = {
        "306c0cabcf39c6de55470d642cf5b9e6e9176d73351966330b90cf333b9359b0": "runtimeIdentityHelperSHA256",
        "8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b": "nativeSourceManifestSHA256",
        "946fe141ee4fa1c1fa8ceafc9060d9d9eedb0d546360140eadaf5ecf1f264f9b": "simulatorReceiptSHA256",
        "efb1df9248d52f4ff69eb08e9a1ce9eeaed58b3b746960d86907fe7fc85fd903": "simulatorCommandSHA256",
        "c5237b26fe0a1ab7fe3c373aed50a34a0a6f65c306ed47918b4e4b54a9245208": "deviceReceiptSHA256",
        "fc251187ea1be539d41501da7b4e00ae2a249662684c1a5c6069235dacaee546": "deviceCommandSHA256",
        "c9c90e3a12868bcedf5f0a4f116c4dc1c388bdcddd0e9f0170c047684c500231": "nativeAssemblyReceiptSHA256",
        "fa999a27c00bfb572cf91ddd65b30e1b7618827c75631f0ee0546748c83f7dbf": "nativeFrameworkInventorySHA256",
        "e22368e522ac795253935b0a31e39d1b36bd9043ef2ed1014845927914527ccd": "packageResolvedSHA256",
        "b5b2ce165c1217140fcddd9289f6f496acb2e7fbd41ccd82fb3bc0a368002150": "sdkMaterializationReceiptSHA256",
        "f94079de9eeb9e2e869f02bd1dda93fcd272e3191b2417ca4b4657cae5dc6763": "nativeSimulatorBinarySHA256",
        "7bf69636b42875aa7dd0fa39c11393e02e6760ef502cf68ef47b740f3bd066c0": "uiGeneratorSHA256",
        "8834541f5a47da80b460ecb96b20c930813b743d94f285fc1efba8a93f65ee4d": "page154UITestSHA256",
    }
    for old, key in replacements.items():
        replace(old, admission["pins"][key])
    replace("ed896be868e973f0bdd704612b641547f51b15509805d4d66b7461be88507d21", admission["sourceStaging"]["sha256"])
    replace("26b16e0bb4266f6f15bd445f70a4032f027c36ca6ec6c255b2e6f9608f7f7245", admission["cacheQualification"]["sha256"])
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", admission["nativeBuildDate"]) is None:
        raise ValueError("Original native build date is required")
    replace('qualify_application(manifest,"2026-11-26",', "qualify_application(manifest," + repr(admission["nativeBuildDate"]) + ",", 1)
    # Keep the original focused compiler assertion and additionally prove every
    # selected native source against the actual command that used its FileList.
    replace(' verify_new_test_compiler_inputs()\n', ' verify_new_test_compiler_inputs()\n w3_native_proof()\n', 1)
    replace(' uiresult=run_phase("ui",ui)\n', ' ui_snapshot=w3_ui_before(ui_source,ui_project,selected)\n uiresult=run_phase("ui",ui)\n w3_ui_after(ui_snapshot,ui_source,ui_project)\n', 1)
    marker = '"completeProductsInventory":{"path":str(EVIDENCE/"products-all.json"),"sha256":sha(EVIDENCE/"products-all.json"),"entries":sum(len(v["entries"]) for v in inventories.values())}})'
    replace(marker, marker[:-2] + ',**w3_final_bindings()})', 1)
    control = {"schema": "pinkha-root-build-control-binding-v1", "appSourceSHA": admission["appSourceSHA"],
               "admission": {"path": str(admission_path), "sha256": admission_digest},
               "adapterSHA256": adapter_digest, "originalProducerCommit": BASE_COMMIT,
               "originalProducerSHA256": BASE_SHA256,
               "originalRetention": admission["originalRetention"]}
    helper_source = Path(__file__).read_text()
    helpers = [ast.get_source_segment(helper_source, node) for node in ast.parse(helper_source).body
               if isinstance(node, ast.FunctionDef) and node.name.startswith("w3_")]
    addition = "\nimport shlex,stat\nWAVE3_ADMISSION=" + repr(admission) + "\nWAVE3_CONTROL=" + repr(control) + "\n\n" + "\n\n".join(helpers) + "\n\n"
    replace("\ntry:\n EVIDENCE.mkdir(exist_ok=False)", addition + "try:\n w3_control_admission()\n EVIDENCE.mkdir(exist_ok=False)", 1)
    # Prove that each structural edit is reversible without touching a single
    # unrelated original byte. Pins are explicit admitted input substitutions.
    inverse = candidate
    for change in reversed(changes):
        if inverse.count(change["new"]) != change["count"]:
            raise ValueError("Ambiguous reviewed producer inverse")
        inverse = inverse.replace(change["new"], change["old"])
    if inverse != base:
        raise ValueError("Producer edits did not restore original bytes")
    for name in ("run_phase", "source_state"):
        if function_source(candidate, name) != function_source(base, name):
            raise ValueError("Original producer function changed: " + name)
    compile(candidate, "<root-bound-original-producer>", "exec")
    return candidate, {"schema": "pinkha-root-producer-byte-inverse-v1", "originalCommit": BASE_COMMIT,
                       "originalSHA256": BASE_SHA256, "adapterSHA256": adapter_digest,
                       "admissionSHA256": admission_digest, "appSourceSHA": admission["appSourceSHA"],
                       "candidateSHA256": hashlib.sha256(candidate.encode()).hexdigest(),
                       "inverseRestoresEveryOriginalByte": True,
                       "byteIdenticalFunctions": ["run_phase", "source_state"], "changes": changes,
                       "builds": 0, "tests": 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--admission-sha256", required=True)
    parser.add_argument("--accepted-source", required=True)
    parser.add_argument("--original-producer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    data = load_admission(args.admission, args.admission_sha256, args.accepted_source)
    source, delta = expand_controller(args.original_producer.read_text(), data, args.admission,
                                      args.admission_sha256, digest(__file__))
    # All preparation outputs are new; a previous failed/finished attempt is
    # immutable. The actual producer separately refuses an existing build root.
    args.output.mkdir(parents=False, exist_ok=False)
    candidate = args.output / "root-approved-original-producer.py"
    candidate.write_text(source)
    (args.output / "byte-inverse-delta.json").write_text(json.dumps(delta, indent=2, sort_keys=True) + "\n")
    if not args.execute:
        print(json.dumps({"status": "PREPARED_NOT_BUILT", "controller": str(candidate),
                          "sha256": digest(candidate), "appSourceSHA": data["appSourceSHA"]}))
        return 0
    # Root must supply exact same admission/source for execution. No automatic
    # resource queue is started, and no other owner's process is signalled.
    if digest(args.admission) != args.admission_sha256:
        raise ValueError("Root admission changed during preparation")
    result = subprocess.run([sys.executable, "-B", str(candidate), data["appSourceSHA"]], check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
