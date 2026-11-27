"""Admit a new MiniApps consumer from its actual build receipt and exact files.

This module does not reuse or modify historical fixed-source controllers.
The caller supplies a reviewed input-contract SHA256; every reference is read
again from original bytes. An admitted build is not an accepted application.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import stat
import subprocess

SCHEMA = "pinkha.miniapps.receipt-input/1"
BUILD_STATUS = "PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
REQUIRED_INPUTS = {"nativeSourceManifestSHA256", "nativeSHA256", "lockSHA256", "sdkReceiptSHA256"}
REQUIRED_PIN_SOURCES = {"Tools/Hanlin/source.json", "Tools/MiniApps/producer.json"}
REQUIRED_PRODUCT_SOURCES = {
    "Anytype/Sources/Pinkha/MiniApps/PinkhaMiniAppsCoordinator.swift",
    "Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinCore/PinkhaMiniAppsReturnQueue.swift",
    "AnyTypeTests/Pinkha/PinkhaMiniAppsNativePreparationTests.swift",
    "PinkhaStage1Acceptance/Tests/MiniAppsNativeAcceptanceUITests.swift",
}
REQUIRED_CONTROLS = {
    "Tools/MiniApps/receipt_admission.py", "Tools/MiniApps/run_receipt_acceptance.py",
    "Tools/MiniApps/file_acceptance.py", "Tools/MiniApps/isolation_acceptance.py",
    "Tools/MiniApps/local_producer.py", "Tools/MiniApps/local_producer_source.py",
    "Tools/MiniApps/simulator_entitlements.py", "Tools/MiniApps/consumer_runtime_boundary.py",
    "Tools/MiniApps/owned_commands.py", "Tools/AnyEnginePort/native_ui_transition_contract.py",
}
METHODS = (
    ("prepare", "AnytypeTests", "PinkhaMiniAppsNativePreparationTests/prepareMiniAppsDocument", 600),
    ("return-ui", "PinkhaStage1AcceptanceUITests", "MiniAppsNativeAcceptanceUITests/testNativeEditorPickerTextStudioReturnAndColdReopen", 600),
    ("replay-ui", "PinkhaStage1AcceptanceUITests", "MiniAppsNativeAcceptanceUITests/testDuplicateCallbackDoesNotInsertAgain", 600),
    ("native-readback", "AnytypeTests", "PinkhaMiniAppsNativePreparationTests/verifyReturnedNativeDocument", 600),
    ("native-adapter", "AnytypeTests", "PinkhaMiniAppsNativePreparationTests/applySelectedTextAndPreserveNewerNativeContent", 600),
    ("native-file-ui", "PinkhaStage1AcceptanceUITests", "MiniAppsNativeAcceptanceUITests/testNativeFilesRoundTripColdReopenCancelAndReplay", 720),
    ("isolation-ui", "PinkhaStage1AcceptanceUITests", "MiniAppsNativeAcceptanceUITests/testPendingReturnsRespectEngineAndAccountAcrossColdReopen", 1620),
    ("isolation-native", "AnytypeTests", "PinkhaMiniAppsNativePreparationTests/verifyEngineAccountIsolationNativeHeartReadback", 600),
)


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical(path, *, directory=False):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(),
            "A canonical existing original path is required: " + str(path))
    require(path.is_dir() if directory else path.is_file(), "Wrong original path kind: " + str(path))
    return path


def relative(path):
    require(isinstance(path, str) and path and "\\" not in path, "Invalid relative path")
    value = PurePosixPath(path)
    require(not value.is_absolute() and all(p not in {"", ".", ".."} for p in value.parts)
            and str(value) == path, "Unsafe or noncanonical relative path: " + path)
    return path


def read_ref(reference, *, limit=64 * 1024**2):
    require(isinstance(reference, dict) and set(reference) == {"path", "sha256"},
            "An exact path/SHA256 original reference is required")
    require(re.fullmatch(r"[a-f0-9]{64}", reference["sha256"]) is not None, "Invalid SHA256 reference")
    path = canonical(reference["path"])
    require(path.stat().st_size <= limit and sha256(path) == reference["sha256"],
            "Original referenced bytes changed: " + str(path))
    return path.read_bytes()


def json_ref(reference):
    return json.loads(read_ref(reference))


def make_ref(path):
    path = canonical(path)
    return {"path": str(path), "sha256": sha256(path)}


def inventory(root):
    """Same complete file/symlink shape as the original products-all producer."""
    root = canonical(root, directory=True)
    rows = []
    for directory, folders, files in os.walk(root, followlinks=False):
        base = Path(directory)
        for name in sorted(folders + files):
            path = base / name
            rel = path.relative_to(root).as_posix()
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                require(path.resolve(strict=True).is_relative_to(root),
                        "Product symlink escapes its original closure: " + rel)
                rows.append({"path": rel, "kind": "symlink", "target": os.readlink(path)})
            elif stat.S_ISREG(mode):
                rows.append({"path": rel, "kind": "file", "bytes": path.stat().st_size, "sha256": sha256(path)})
            elif not stat.S_ISDIR(mode):
                raise ValueError("Unexpected product file kind: " + rel)
    return sorted(rows, key=lambda row: row["path"])


def verify_inventory(root, expected):
    require(isinstance(expected, list) and expected, "Empty actual product inventory")
    paths = [relative(row["path"]) for row in expected]
    require(len(paths) == len(set(paths)), "Duplicate product inventory entry")
    require(inventory(root) == sorted(expected, key=lambda row: row["path"]),
            "Actual product inventory differs from its original producer: " + str(root))



def git_source(root, commit):
    """Read original Git identity and files omitted by the build's suffix filter."""
    environment = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    def command(*args, data=None):
        result = subprocess.run(["git", "-C", str(root), *args], input=data,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=environment, check=True)
        return result.stdout
    identity = command("rev-parse", "HEAD", "HEAD^{tree}").decode().splitlines()
    require(len(identity) == 2, "Original Git identity is incomplete")
    tree = command("ls-tree", "-r", "-z", commit, "--", *sorted(REQUIRED_PIN_SOURCES), "PinkhaStage1Acceptance")
    objects = []
    for row in tree.split(b"\0"):
        if not row:
            continue
        metadata, raw_name = row.split(b"\t", 1)
        mode, kind, oid = metadata.decode().split()
        name = relative(raw_name.decode())
        require(kind == "blob" and mode in {"100644", "100755"}, "Original pinned input is not a regular Git blob")
        objects.append((name, oid))
    data = command("cat-file", "--batch", data="".join(oid + "\n" for _, oid in objects).encode())
    offset, files = 0, {}
    for name, oid in objects:
        end = data.index(b"\n", offset)
        actual_oid, kind, length = data[offset:end].decode().split()
        length = int(length)
        offset = end + 1
        raw = data[offset:offset + length]
        require(actual_oid == oid and kind == "blob" and len(raw) == length
                and data[offset + length:offset + length + 1] == b"\n", "Original Git input stream differs")
        offset += length + 1
        files[name] = {"bytes": length, "sha256": hashlib.sha256(raw).hexdigest()}
    require(offset == len(data), "Extra original Git input bytes")
    return {"commit": identity[0], "tree": identity[1], "status": command("status", "--porcelain").decode(),
            "files": files}


def verify_source(source, *, required=REQUIRED_PRODUCT_SOURCES):
    require(re.fullmatch(r"[a-f0-9]{40}", source["commit"]) is not None
            and re.fullmatch(r"[a-f0-9]{40}", source["tree"]) is not None, "Invalid exact source identity")
    before, after = read_ref(source["before"]), read_ref(source["after"])
    require(before == after, "Original before/after source observations differ")
    observed = json.loads(before)
    require(observed["commit"] == source["commit"] and observed["tree"] == source["tree"],
            "Source observation is for a different commit/tree")
    rows = observed["files"]
    require(isinstance(rows, dict) and required.issubset(rows), "Missing compiled acceptance source closure")
    root = canonical(source["root"], directory=True)
    actual = git_source(root, source["commit"])
    require(actual["commit"] == source["commit"] and actual["tree"] == source["tree"]
            and actual["status"] == observed["status"] == "", "Original Git source identity or clean state changed")
    require(REQUIRED_PIN_SOURCES.issubset(actual["files"]), "Original companion/SDK Git pins are missing")
    for name, row in actual["files"].items():
        path = canonical(root / relative(name))
        require(path.stat().st_size == row["bytes"] and sha256(path) == row["sha256"],
                "Actual pinned/copy input differs from original Git source: " + name)
    for name, row in rows.items():
        path = canonical(root / relative(name))
        require(path.is_relative_to(root) and path.stat().st_size == row["bytes"]
                and sha256(path) == row["sha256"], "Observed source changed: " + name)
    return dict(observed, gitSupplementalFiles=actual["files"])


def verify_controls(controls):
    value = json_ref(controls["manifest"])
    require(value.get("commit") == controls["commit"]
            and re.fullmatch(r"[a-f0-9]{40}", controls["commit"]) is not None,
            "Controller source commit differs")
    root = canonical(controls["root"], directory=True)
    files = value.get("files")
    require(isinstance(files, dict) and REQUIRED_CONTROLS.issubset(files),
            "Incomplete original controller/helper source closure")
    for name, row in files.items():
        path = canonical(root / relative(name))
        require(path.is_relative_to(root) and path.stat().st_size == row["bytes"]
                and sha256(path) == row["sha256"], "Controller/helper bytes changed: " + name)
    # Include every Python helper under Tools, including transitive imports.
    present = {p.relative_to(root).as_posix() for p in (root / "Tools").rglob("*.py") if p.is_file()}
    require(present == set(files), "An unbound Python helper exists or a bound helper is missing")
    return value



def verify_project_inventory(reference):
    value = json_ref(reference)
    require(value.get("schema") == "pinkha-generated-ui-project-inventory-v1",
            "Unknown generated UI project inventory")
    root = canonical(value["root"], directory=True)
    actual = {}
    for directory, folders, files in os.walk(root, followlinks=False):
        for name in sorted(folders + files):
            path = Path(directory) / name
            require(not path.is_symlink(), "Generated UI project contains a symlink")
            mode = path.stat().st_mode
            row = {"mode": stat.S_IMODE(mode)}
            if stat.S_ISREG(mode):
                row.update(kind="file", bytes=path.stat().st_size, sha256=sha256(path))
            else:
                require(stat.S_ISDIR(mode), "Unsupported generated project file kind")
                row.update(kind="directory")
            actual[path.relative_to(root).as_posix()] = row
    require(actual == value["entries"] and "project.pbxproj" in actual
            and "xcshareddata/xcschemes/PinkhaPrebuiltUI.xcscheme" in actual,
            "Actual generated project differs from its compiler input inventory")
    return value


def verify_compilation(contract, build, observed):
    source = contract["source"]
    source_root = canonical(source["root"], directory=True)
    copied_ref = contract["build"]["originalUICopy"]
    copied = json_ref(copied_ref)
    require(copied_ref["sha256"] == build["originalUICopySHA256"],
            "Original UI copy receipt is not bound by the producer")
    generator = contract["build"]["uiGenerator"]
    read_ref(generator)
    require(generator["sha256"] == copied["generatorSHA256"],
            "Original UI project generator bytes differ")
    copy_rows = copied["copiedFiles"]
    copy_paths = [relative(row["path"]) for row in copy_rows]
    expected_copy = {name for name in observed["gitSupplementalFiles"] if name.startswith("PinkhaStage1Acceptance/")}
    require(expected_copy and len(copy_paths) == len(set(copy_paths)) and set(copy_paths) == expected_copy,
            "The original UI copy receipt does not cover every original tracked UI file")

    for label, schema, status in (
        ("ui", "pinkha-exact-ui-compiler-inputs-v1",
         "PASS_EXACT_UI_COPY_PROJECT_AND_COMPILER_INPUTS_NOT_TEST_EXECUTION"),
        ("native", "pinkha-exact-native-compiler-inputs-v1",
         "PASS_EXACT_NATIVE_COMPILER_INPUTS_NOT_TEST_EXECUTION"),
    ):
        reference = contract["build"][label + "CompilationProof"]
        require(reference == build[label + "CompilationProof"],
                "Compiler proof is not the exact original producer reference")
        proof = json_ref(reference)
        require(proof.get("schema") == schema and proof.get("status") == status
                and proof.get("sourceCommit") == source["commit"] and proof.get("testsExecuted") == 0,
                "Foreign or incomplete compiler input proof")
        if label == "ui":
            require(proof["originalUICopySHA256"] == copied_ref["sha256"]
                    and proof["generatorSHA256"] == generator["sha256"],
                    "UI compiler proof refers to a different copy/generator")
            before = verify_project_inventory(proof["generatedProjectBefore"])
            after = verify_project_inventory(proof["generatedProjectAfter"])
            require(before == after and before["root"] == copied["generatedProject"],
                    "Generated project changed during actual compilation")
            project = canonical(before["root"], directory=True)
            require(str(project) in build["ui"]["argv"], "UI build command does not use this generated project")
            compiled_root = project.parent.parent
            for row in copy_rows:
                original = observed["gitSupplementalFiles"][row["path"]]
                path = canonical(compiled_root / row["path"])
                require(row["sha256"] == original["sha256"] == sha256(path)
                        and path.stat().st_size == original["bytes"],
                        "Actual original UI copy differs from its selected source: " + row["path"])
            expected = {name for name in expected_copy if name.endswith(".swift")}
        else:
            compiled_root = source_root
            expected = {"AnyTypeTests/Pinkha/PinkhaMiniAppsNativePreparationTests.swift"}

        rows = proof["requiredSources"]
        names = [relative(row["repositoryPath"]) for row in rows]
        require(rows and len(names) == len(set(names)) and expected.issubset(names),
                "Required actual acceptance source is absent or duplicated")
        if label == "ui":
            require(set(names) == expected, "UI compiler proof does not cover every copied Swift source")
        else:
            require(all(name.startswith("AnyTypeTests/") and name.endswith(".swift") for name in names),
                    "A foreign source was admitted as a native test compiler input")
        compiled_paths = set()
        for row in rows:
            name = row["repositoryPath"]
            original = observed["files"][name]
            path = canonical(row["compiledPath"])
            require(path == compiled_root / name and row["bytes"] == original["bytes"] == path.stat().st_size
                    and row["sha256"] == original["sha256"] == sha256(path),
                    "Actually compiled source differs from selected source: " + name)
            compiled_paths.add(str(path))
        file_lists = proof["actualCompilerFileLists"]
        require(isinstance(file_lists, list) and file_lists, "No original compiler file list")
        seen_lists, occurrences = set(), Counter()
        original_log_ref = contract["build"]["logs"]["ui" if label == "ui" else "app"]
        require(proof["buildLog"] == original_log_ref, "Compiler proof refers to a different build log")
        compiler_lines = read_ref(original_log_ref, limit=512 * 1024**2).splitlines()
        expected_module = "PinkhaStage1AcceptanceUITests" if label == "ui" else "AnytypeTests"
        for row in file_lists:
            reference = {"path": row["path"], "sha256": row["sha256"]}
            raw = read_ref(reference)
            original_path = row["originalPath"]
            invocation = row["compilerInvocation"]
            number = invocation["lineNumber"]
            require(isinstance(original_path, str) and Path(original_path).is_absolute()
                    and original_path.endswith(".SwiftFileList")
                    and original_path not in seen_lists and type(number) is int
                    and 1 <= number <= len(compiler_lines),
                    "Compiler file list is duplicated or its actual command is absent")
            seen_lists.add(original_path)
            line = compiler_lines[number - 1]
            tokens = shlex.split(line.decode("utf-8"))
            require(hashlib.sha256(line).hexdigest() == invocation["lineSHA256"]
                    and invocation["moduleName"] == expected_module
                    and any(Path(token).name == "swiftc" for token in tokens)
                    and any(tokens[index:index + 2] == ["-module-name", expected_module]
                            for index in range(len(tokens) - 1))
                    and any(token.startswith("@") and token[1:].casefold() == original_path.casefold()
                            and (token[1:] == original_path or
                                 (Path(token[1:]).is_file() and Path(original_path).is_file()
                                  and Path(token[1:]).samefile(original_path)))
                            for token in tokens),
                    "Original compiler command did not compile the selected test target/file list")
            listed = []
            for line in raw.decode("utf-8").splitlines():
                if line.strip():
                    parts = shlex.split(line)
                    require(len(parts) == 1, "Ambiguous original compiler file list line")
                    listed.append(parts[0])
            require(len({path.casefold() for path in compiled_paths}) == len(compiled_paths),
                    "Case-colliding selected source paths")
            selected = []
            for expected_path in compiled_paths:
                matches = [path for path in listed if path.casefold() == expected_path.casefold()]
                require(len(matches) == 1, "Required source is missing or duplicated in actual compiler file list")
                actual_path = canonical(matches[0])
                require(actual_path.samefile(expected_path) and sha256(actual_path) == sha256(expected_path),
                        "Actual compiler input is a different file, not an APFS case alias")
                selected.append(expected_path)
            require(len(row["requiredSourcePaths"]) == len(set(row["requiredSourcePaths"]))
                    and set(row["requiredSourcePaths"]) == set(selected),
                    "Declared compiler source selection differs from original file list")
            occurrences.update(selected)
        require(set(occurrences) == compiled_paths and all(count == len(file_lists) for count in occurrences.values()),
                "Required selected source did not occur exactly once per actual compiler input list")
    return copied


def verify_build(contract, observed=None):
    build = json_ref(contract["build"]["receipt"])
    source = contract["source"]
    observed = observed if observed is not None else verify_source(source)
    require(build.get("sourceBeforeSHA256") == source["before"]["sha256"]
            and build.get("sourceAfterSHA256") == source["after"]["sha256"],
            "Source observations are not bound by the actual producer")
    require(build.get("status") == BUILD_STATUS and build.get("sourceCommit") == source["commit"]
            and build.get("sourceUnchanged") is True and build.get("testsExecuted") == 0,
            "No complete unchanged-source app/UI build with explicit no-test status")
    producer = contract["build"]["producer"]
    read_ref(producer)
    require(producer["sha256"] == build["controllerSHA256"], "Actually executed producer bytes differ")
    assembly_ref = contract["build"]["assembly"]
    assembly = json_ref(assembly_ref)
    require(assembly_ref["sha256"] == build["assemblyReceiptSHA256"]
            and assembly.get("status") == "PASS_ASSEMBLED_TWO_QUALIFIED_SLICES_NOT_APP_ACCEPTANCE"
            and assembly["sourceManifestSHA256"] == build["inputs"]["nativeSourceManifestSHA256"]
            and assembly["runtimeIdentity"]["sourceManifestSHA256"] == assembly["sourceManifestSHA256"]
            and {"any", "heart", "sdk", "sync"}.issubset(assembly["runtimeIdentity"]["sourcePins"]),
            "Actual qualified native assembly source/receipt differs")
    control = build["controlAdmission"]
    root_admission = json_ref(control["admission"])
    read_ref(control["originalRetention"])
    require(control.get("schema") == "pinkha-root-build-control-binding-v1"
            and control.get("appSourceSHA") == source["commit"]
            and control.get("originalProducerCommit") == "204f8fbb25c3b21f419fc1a8818eb46ed492e561"
            and control.get("originalProducerSHA256") == "9b1405ea44ba9cce3fca47a88127fc798fedab3d1b05f6e3728da3597d19929c"
            and root_admission.get("schema") == "pinkha-root-frozen-build-admission-v1"
            and root_admission.get("readyForBuild") is True
            and root_admission["appSourceSHA"] == source["commit"]
            and root_admission["sourceRoot"] == source["root"]
            and root_admission["originalRetention"] == control["originalRetention"],
            "The original producer is not bound to the root's frozen source admission")
    for original_key, root_key in (
        ("nativeSourceManifestSHA256", "nativeSourceManifestSHA256"),
        ("lockSHA256", "packageResolvedSHA256"),
        ("sdkReceiptSHA256", "sdkMaterializationReceiptSHA256"),
        ("nativeSHA256", "nativeSimulatorBinarySHA256"),
    ):
        require(build["inputs"][original_key] == root_admission["pins"][root_key],
                "A native/SDK input differs from the root's frozen source admission")
    require(assembly_ref["sha256"] == root_admission["pins"]["nativeAssemblyReceiptSHA256"]
            and contract["build"]["uiGenerator"]["sha256"] == root_admission["pins"]["uiGeneratorSHA256"],
            "Assembly or UI generator differs from the root's frozen source admission")
    for key, input_key in (("sourceStaging", "stagingReceiptSHA256"),
                           ("cacheQualification", "cacheRequalificationReceiptSHA256")):
        read_ref(root_admission[key])
        require(root_admission[key]["sha256"] == build["inputs"][input_key],
                "Original staging/cache observation is not the admitted build input")
    native_proof = json_ref(build["nativeCompilationProof"])
    require(set(root_admission["selectedNativeTestSources"]) ==
            {row["repositoryPath"] for row in native_proof["requiredSources"]},
            "A root-selected native test source is absent from actual compiler proof")
    ui_proof = json_ref(build["uiCompilationProof"])
    require(set(root_admission["selectedUITestSources"]).issubset(
            {row["repositoryPath"] for row in ui_proof["requiredSources"]}),
            "A root-selected UI test source is absent from actual compiler proof")
    references = contract["build"]["inputs"]
    original_inputs = build["inputs"]
    required = {key for key in original_inputs if key.endswith("SHA256")}
    require(REQUIRED_INPUTS.issubset(required) and set(references) == required,
            "Every original native/lock/SDK input digest must have its exact original file")
    for key, reference in references.items():
        # Large native archives are hashed by streaming, not loaded into memory.
        path = canonical(reference["path"])
        require(reference["sha256"] == original_inputs[key] == sha256(path),
                "Actual original build input differs: " + key)
    for name in ("app", "ui"):
        step = build[name]
        require(step.get("sourceCommit") == source["commit"] and step.get("exitCode") == 0
                and str(step.get("status", "")).startswith("PASS") and not step.get("cleanupErrors"),
                "Original app/UI command did not succeed cleanly for this source: " + name)
        log_ref = contract["build"]["logs"][name]
        log = read_ref(log_ref, limit=512 * 1024**2)
        require(log_ref["sha256"] == step["logSHA256"] and len(log) == step["logBytes"],
                "Actual compiler log differs: " + name)
        require(any(Path(str(arg)).name == "xcodebuild" for arg in step["argv"])
                and any(arg in {"build", "build-for-testing"} for arg in step["argv"])
                and (b"** TEST BUILD SUCCEEDED **" in log or b"** BUILD SUCCEEDED **" in log),
                "Missing original successful Xcode build command/output: " + name)
    verify_compilation(contract, build, observed)
    return build


def admit(path, expected_sha256):
    path = canonical(path)
    require(sha256(path) == expected_sha256, "Reviewed acceptance contract changed")
    contract = json.loads(path.read_bytes())
    require(contract.get("schema") == SCHEMA, "Unsupported receipt input schema")
    source = verify_source(contract["source"])
    controls = verify_controls(contract["controls"])
    build = verify_build(contract, source)
    products_ref = contract["build"]["products"]
    products = json_ref(products_ref)
    complete = build["completeProductsInventory"]
    require(complete["path"] == products_ref["path"] and complete["sha256"] == products_ref["sha256"]
            and type(complete["entries"]) is int
            and complete["entries"] == sum(len(value["entries"]) for value in products.values()),
            "Full product inventory is not the exact original producer inventory")
    require(set(products) == {"app-derived", "ui-derived"}, "Original app/UI products are both required")
    for record in products.values():
        verify_inventory(record["base"], record["entries"])
    for label, item in contract["descriptors"].items():
        require(label in {"app", "ui"} and item["slot"] == label + "-derived",
                "Unexpected actual descriptor mapping")
        require(any(row["path"] == relative(item["path"]) and row["kind"] == "file"
                    for row in products[item["slot"]]["entries"]), "Unrecorded actual Xcode test descriptor")
    require(set(contract["descriptors"]) == {"app", "ui"}, "Both original descriptors are required")
    dependencies = contract["dependencyEvidence"]
    require(set(dependencies) == {"Hanlin", "Heart", "Any", "TorahInspectorKit"},
            "Exact source/pin evidence is required for both engines and both shared SDKs")
    for name, references in dependencies.items():
        require(isinstance(references, list) and references, "Missing dependency evidence: " + name)
        for reference in references:
            read_ref(reference, limit=128 * 1024**2)
    require(contract["runtime"]["family"] in {"ipad", "iphone"}
            and contract["runtime"]["architecture"] == "arm64"
            and contract["runtime"]["version"].split(".")[0] == "27",
            "The actual native tests require a declared OS27 arm64 device family")
    commands = {tuple(item["argv"]) for item in contract["toolchain"]}
    require(commands == {("xcodebuild", "-version"), ("xcrun", "swift", "--version"),
                         ("xcrun", "--sdk", "iphonesimulator", "--show-sdk-build-version")}
            and len(contract["toolchain"]) == 3, "Three exact original Apple toolchain observations required")
    for item in contract["toolchain"]:
        read_ref(item["original"])
    return contract, {"status": "ADMITTED_ORIGINAL_BUILD_NOT_APPLICATION_ACCEPTANCE",
                      "contractSHA256": expected_sha256, "sourceCommit": source["commit"],
                      "sourceTree": source["tree"], "controllerCommit": controls["commit"],
                      "productCounts": {key: len(value["entries"]) for key, value in products.items()},
                      "inputs": build["inputs"], "methods": [m[2] for m in METHODS],
                      "physicalDevice": "NOT_RUN", "testMethodsExecuted": 0}, products
