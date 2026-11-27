"""Compile the original two-source Native23 UI runner after the shared App.

This is a separate compiler receipt, never a runtime profile or fixture.  The
original App/Stage1 producer and receipts are inputs and remain unchanged.  The
closed Native23 controller is not configured or executed: only its exact pure
swiftc witness and original project/argv declarations are reused.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import re
import shlex
import shutil
import subprocess
import sys
import time
from types import SimpleNamespace

sys.dont_write_bytecode = True
PREFIX = "Tools/PinkhaDualEngineRuntime/hosted_shared_build/"
CONTRACT_NAME = "native23_build_contract.json"
CONTRACT_SHA256 = "dc228b291736fa472c852232e09e79e27a70720ff235a762512ba4337b7d77e0"
TARGET = "PinkhaAnyNativeUITests"
PHASE = "native23-ui"
LOCK = "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
SDK_MARKER = "Dependencies/Hanlin/.pinkha-source.json"
NATIVE_BINARY = "Dependencies/Middleware/Lib.xcframework/ios-arm64-simulator/Lib.framework/Lib"


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def regular(path):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path and path.is_file()
            and not path.is_symlink(), "Physical original regular input required: " + str(path))
    return {"bytes": path.stat().st_size, "sha256": sha(path)}


def ref(path):
    row = regular(path)
    return {"path": str(path), **row}


def write(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def error(value):
    return {"type": type(value).__name__, "message": str(value)}


def contract():
    path = Path(__file__).with_name(CONTRACT_NAME).resolve()
    require(regular(path)["sha256"] == CONTRACT_SHA256, "Exact reviewed Native23 build contract required")
    value = json.loads(path.read_bytes())
    require(value["schema"] == "pinkha-original-native23-ui-compiler-contract-v1"
            and value["runtimeAdmission"] is False and value["testsExecuted"] == 0
            and len(value["sourcePathPins"]) == 28 and len(value["swiftSources"]) == 2
            and len(value["declaredOriginalLaunchMethods"]) == 26
            and len(value["declaredOriginalHistoryMethods"]) == 1,
            "Fixed original two-source compiler scope changed")
    return value


def declared_plan():
    value = contract()
    return {"schema": "pinkha-native23-ui-only-build-plan-v1", "contractSHA256": CONTRACT_SHA256,
            "target": TARGET, "swiftSources": value["swiftSources"],
            "resourcePolicy": value["resourcePolicy"], "runtimeAdmission": False,
            "testsExecuted": 0, "applicationBuildTargetsInThisPhase": 0, "nativeLibraryBuildsInThisPhase": 0}


def source_rows(source, value):
    expected = dict(value["sourcePathPins"])
    for key in ("originalCompilerProfile", "originalProjection", "originalDescriptorHelper", "originalUIBuilder"):
        expected[value[key]["path"]] = value[key]["sha256"]
    rows = {}
    for relative, digest in sorted(expected.items()):
        row = regular(source / relative)
        require(row["sha256"] == digest, "Original Native23 source differs: " + relative)
        rows[relative] = row
    for relative, expected_row in value["swiftSources"].items():
        require(rows[relative] == expected_row, "Complete original Swift source differs")
    return rows


def preflight(owner, args, root, plan, control, source):
    """Fail before the shared build if the separate, fixed UI contract is absent."""
    value = contract()
    require(plan.get("native23Compiler") == declared_plan(), "Exact root-admitted Native23 compiler plan required")
    require(Path(__file__).resolve() == control / PREFIX / "native23_build.py",
            "Native23 compiler helper must be in the actual control checkout")
    original = owner.command(["git", "--no-replace-objects", "-C", str(control), "show",
                              plan["controlCommit"] + ":" + PREFIX + CONTRACT_NAME])
    require(original == (control / PREFIX / CONTRACT_NAME).read_bytes(), "Executed contract differs from its Git blob")
    require(owner.source_identity(source, plan["appSourceSHA"], plan["appSourceTree"])["status"] == "",
            "Clean common source required")
    rows = source_rows(source, value)
    for key in ("originalSupervisor", "originalLifecycle"):
        item = value[key]
        require(regular(control / item["path"])["sha256"] == item["sha256"], "Original supervision closure differs")
    output = root / "native23-ui"
    require(not output.exists() and not output.is_symlink(), "Fresh disjoint Native23 compiler output required")
    result = {"schema": "pinkha-native23-compiler-inputs-v1", "status": "PASS_SOURCE_INPUTS_NOT_COMPILED",
              "sourceCommit": plan["appSourceSHA"], "sourceTree": plan["appSourceTree"],
              "contract": ref(control / PREFIX / CONTRACT_NAME), "helper": ref(Path(__file__).resolve()),
              "rootPlan": ref(Path(args.plan)), "sourceInputs": rows, "output": str(output),
              "resourcePolicy": value["resourcePolicy"], "testsExecuted": 0, "runtimeAdmission": False}
    write(root / "native23-source-intake.json", result)
    return result


def original_module(path, digest, name):
    require(regular(path)["sha256"] == digest and name not in sys.modules,
            "Original module differs or an imported name is occupied")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def original_functions(path, digest, names, namespace):
    require(regular(path)["sha256"] == digest, "Original declaration source changed")
    source = path.read_text()
    nodes = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name in names]
    require(len(nodes) == len(names) and {node.name for node in nodes} == set(names), "Exact original functions missing")
    proof = []
    for node in nodes:
        raw = ast.get_source_segment(source, node).encode()
        proof.append({"name": node.name, "lineStart": node.lineno, "lineEnd": node.end_lineno,
                      "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    # No original top-level build, closed profile gate or fixture loader executes.
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return {"source": ref(path), "declarations": proof}


def projected_source(source, output, value, lifecycle):
    item = value["originalProjection"]
    module = original_module(source / item["path"], item["sha256"], "native23_exact_project_projection")
    require(module.PROJECT_NAME == value["projectName"] and module.SCHEME_NAME == value["scheme"]
            and module.TARGET == TARGET, "Original UI-only target identity differs")
    project, inverse = module.project_bytes((source / "NativeApp/AnyNative.xcodeproj/project.pbxproj").read_bytes())
    scheme = module.scheme_bytes((source / "NativeApp/AnyNative.xcodeproj/xcshareddata/xcschemes/PinkhaAnyNativeApp.xcscheme").read_bytes())
    files = {module.PROJECT_NAME + "/project.pbxproj": project,
             module.PROJECT_NAME + "/xcshareddata/xcschemes/" + module.SCHEME_NAME + ".xcscheme": scheme}
    for relative in value["swiftSources"]:
        files["UITests/" + Path(relative).name] = (source / relative).read_bytes()
    directory = output / "source"
    directory.mkdir(mode=0o700)
    for relative, raw in files.items():
        path = directory / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        require(path.read_bytes() == raw, "Original Native23 generated copy differs")
    state = lifecycle.inventory(directory)
    write(output / "evidence/generated-inputs-before.json", state)
    write(output / "evidence/projection.json", {"originalGenerator": ref(source / item["path"]),
          "exactOriginalProjectProjection": inverse, "originalSchemeSHA256": module.SCHEME_SHA,
          "generatedSchemeSHA256": hashlib.sha256(scheme).hexdigest(), "sourceFiles": value["swiftSources"],
          "applicationBuildTargets": 0, "targetDependencies": 0, "packageReferences": 0,
          "testsExecuted": 0, "runtimeAdmission": False})
    return module, directory / module.PROJECT_NAME, state


def original_argv(source, output, project, projection, value):
    item = value["originalUIBuilder"]
    path = source / item["path"]
    require(regular(path)["sha256"] == item["sha256"], "Original Native23 build declaration changed")
    text = path.read_text()
    main = [node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name == "main"]
    require(len(main) == 1, "Original builder main declaration missing")
    nodes = [node for node in ast.walk(main[0]) if isinstance(node, ast.Assign)
             and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
             and node.targets[0].id == "argv" and isinstance(node.value, ast.List)
             and len(node.value.elts) > 2 and all(isinstance(e, ast.Constant) for e in node.value.elts[:2])
             and [e.value for e in node.value.elts[:2]] == ["xcodebuild", "build-for-testing"]]
    require(len(nodes) == 1, "One original UI-only compiler argv declaration required")
    raw = ast.get_source_segment(text, nodes[0]).encode()
    namespace = {"str": str, "project": project, "projection": projection, "output": output}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    argv = namespace["argv"]
    require(argv[argv.index("-derivedDataPath") + 1] == str(output / "derived")
            and argv[argv.index("-resultBundlePath") + 1] == str(output / "Build.xcresult")
            and argv[argv.index("-scheme") + 1] == value["scheme"]
            and argv[argv.index("-destination") + 1] == "generic/platform=iOS Simulator"
            and argv[argv.index("-jobs") + 1] == str(value["resourcePolicy"]["jobs"]),
            "Original fixed UI-only compiler arguments differ")
    return argv, {"source": ref(path), "lineStart": nodes[0].lineno, "lineEnd": nodes[0].end_lineno,
                  "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


class PhaseCustody:
    """Observe one real Popen while retaining the original supervisor unchanged.

    An evidence-write exception inside the old supervisor must still drain its
    actual child.  Positive absence is latched; unresolved ownership prohibits
    post-build subprocesses.  This wrapper never signals a historical PID.
    """
    def __init__(self, lifecycle, directory, source):
        self.lifecycle = lifecycle.Commands(directory, source)
        self.process = None
        self.observation = None
        self.closed = False
        self.cleanup = {"cleanupErrors": [], "termination": []}

    def popen(self, *args, **kwargs):
        require(self.process is None and kwargs.get("start_new_session") is True,
                "Exactly one newly owned Native23 compiler is permitted")
        process = subprocess.Popen(*args, **kwargs)
        self.process = process
        return process

    def _terminate_owned_process(self, process, outcome):
        require(process is self.process and not self.closed, "Only the unreleased original child may be drained")
        return self.lifecycle._terminate_owned_process(process, outcome)

    def _observe_exited_group(self, pgid):
        require(self.process is not None and pgid == self.process.pid, "Only the actual owned compiler group is observed")
        if self.closed:
            return self.observation
        observed = self.lifecycle._observe_exited_group(pgid)
        self.observation = observed
        self.closed = observed["status"] == "ABSENT_ESRCH"
        return observed

    def require_closed(self):
        require(self.process is None or self.closed, "Native23 ownership unresolved; no further subprocesses are admitted")

    def readonly_run(self, *args, **kwargs):
        self.require_closed()
        return subprocess.run(*args, **kwargs)

    def finish(self):
        if self.process is not None and not self.closed:
            try:
                self._terminate_owned_process(self.process, self.cleanup)
            except BaseException as exc:
                self.cleanup["cleanupErrors"].append({"phase": "emergency-owned-drain", **error(exc)})
            try:
                self.process.wait(timeout=1)
            except BaseException as exc:
                self.cleanup["cleanupErrors"].append({"phase": "emergency-owned-reap", **error(exc)})
            try:
                self._observe_exited_group(self.process.pid)
            except BaseException as exc:
                self.cleanup["cleanupErrors"].append({"phase": "emergency-owned-observation", **error(exc)})
        return {"pid": self.process.pid if self.process is not None else None,
                "status": "NOT_SPAWNED" if self.process is None else "ABSENT_ESRCH" if self.closed else "UNRESOLVED",
                "observation": self.observation, **self.cleanup}


def supervisor(owner, control, source, root, output, plan, value, lifecycle, custody, environment):
    policy = value["resourcePolicy"]
    env = dict(environment, DEVELOPER_DIR=owner.DEVELOPER, PYTHONDONTWRITEBYTECODE="1",
               PINKHA_ANY_NATIVE_ARTIFACT="verified-unified-v1", PINKHA_NATIVE_T2_AUTHORIZED_READ_V1="1")
    namespace = {"pathlib": __import__("pathlib"), "os": os, "json": json, "time": time,
                 "hashlib": hashlib, "shutil": shutil, "subprocess": SimpleNamespace(
                     Popen=custody.popen, run=custody.readonly_run, STDOUT=subprocess.STDOUT),
                 "SOURCE": source, "ROOT": root, "EVIDENCE": output / "evidence",
                 "EXPECTED": plan["appSourceSHA"], "FLOOR": policy["emergencyFloorBytes"],
                 "PHASE_GROWTH": {PHASE: policy["phaseGrowthAllowanceBytes"]},
                 "CONCURRENT_GROWTH": policy["concurrentGrowthAllowanceBytes"],
                 "LIFECYCLE": custody, "ENV": env}
    item = value["originalSupervisor"]
    proof = original_functions(control / item["path"], item["sha256"], item["extractedFunctions"], namespace)
    write(output / "evidence/original-supervisor-declarations.json", proof)
    return namespace


def original_product_inventory(root, receipt, lifecycle):
    path = root / "build16/products-all.json"
    require(ref(path)["sha256"] == receipt["completeProductsInventory"]["sha256"]
            and receipt["completeProductsInventory"]["path"] == str(path), "Original complete App/Stage1 inventory differs")
    expected = json.loads(path.read_bytes())
    require(set(expected) == {"app-derived", "ui-derived"}, "Original two product roots changed")
    actual = {}
    for name, slot in expected.items():
        directory = root / name / "Build/Products"
        require(slot["base"] == str(directory), "Original product root must stay at its real producer path")
        inventory = lifecycle.inventory(directory)
        rows = []
        for relative, row in inventory.items():
            if row["kind"] == "file":
                rows.append({"path": relative, **{k: row[k] for k in ("kind", "bytes", "sha256")}})
            elif row["kind"] == "symlink":
                rows.append({"path": relative, "kind": "symlink", "target": row["target"]})
        require(rows == slot["entries"], "Actual original App/Stage1 products changed")
        actual[name] = {"base": str(directory), "entries": inventory}
    require(receipt["completeProductsInventory"]["entries"] == sum(len(x["entries"]) for x in expected.values()),
            "Original product inventory count differs")
    return actual


def parent_receipts(owner, root, plan, source, lifecycle):
    paths = [root / "hosted-receipt.json", root / "build16/receipt.json",
             root / "root-derived-build-admission.json", root / "source-staging.json",
             root / "build16/source-before.json", root / "build16/source-after.json",
             root / "build16/products-all.json", root / "native-transport-receipt.json"]
    references = {str(path.relative_to(root)): ref(path) for path in paths}
    hosted, build, admission, staging = (json.loads(path.read_bytes()) for path in paths[:4])
    require(hosted["status"] == "PASS_HOSTED_ORIGINAL_APP_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
            and hosted["originalBuildReceipt"] == owner.ref(paths[1])
            and hosted["appSourceSHA"] == plan["appSourceSHA"] and hosted["testsExecuted"] == 0,
            "Original shared hosted App/Stage1 receipt required")
    require(build["status"] == "PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
            and build["sourceCommit"] == plan["appSourceSHA"] and build["sourceUnchanged"] is True
            and build["testsExecuted"] == 0, "Original shared App/Stage1 compiler did not pass")
    for name in ("app", "ui"):
        phase = build[name]
        require(phase["status"] == "PASS_BUILD_EXIT_0" and phase["exitCode"] == 0
                and phase["ownedProcessGroup"] == "ABSENT_ESRCH" and not phase["cleanupErrors"],
                "Prior original compiler process ownership is not closed")
    require(admission["sourceRoot"] == str(source) and admission["buildRoot"] == str(root)
            and admission["appSourceSHA"] == staging["sourceCommit"] == plan["appSourceSHA"]
            and admission["pins"] == plan["pins"] and admission["readyForBuild"] is True
            and staging["nativeQualification"]["nativeSourceManifestSHA256"] == plan["pins"]["nativeSourceManifestSHA256"],
            "Actual same-source native/SDK producer admission differs")
    require(paths[4].read_bytes() == paths[5].read_bytes(), "Original complete source snapshots differ")
    for key, relative, input_key in (("packageResolvedSHA256", LOCK, "lockSHA256"),
                                   ("sdkMaterializationReceiptSHA256", SDK_MARKER, "sdkReceiptSHA256"),
                                   ("nativeSimulatorBinarySHA256", NATIVE_BINARY, "nativeSHA256")):
        require(regular(source / relative)["sha256"] == plan["pins"][key] == build["inputs"][input_key],
                "Actual compiled native/SDK/lock input changed")
    require(build["inputs"]["nativeSourceManifestSHA256"] == plan["pins"]["nativeSourceManifestSHA256"],
            "The admitted original native source identity differs")
    return references, build, original_product_inventory(root, build, lifecycle)


def compiler_proof(source, output, value, phase, lifecycle):
    item = value["originalCompilerProfile"]
    namespace = {"require": require, "Path": Path, "shlex": shlex}
    functions = original_functions(source / item["path"], item["sha256"], item["extractedFunctions"], namespace)
    expected = {str(output / "source/UITests" / Path(relative).name): row
                for relative, row in value["swiftSources"].items()}
    require(all(regular(Path(path)) == row for path, row in expected.items()), "Compiled original Swift bytes changed")
    log = output / "evidence" / PHASE / "original.log"
    require(sha(log) == phase["logSHA256"] and log.stat().st_size == phase["logBytes"], "Actual original compiler log differs")
    lists = []
    retained_root = output / "evidence/original-compiler-file-lists"
    retained_root.mkdir()
    for path in sorted((output / "derived/Build/Intermediates.noindex").rglob("*.SwiftFileList")):
        if not any(part.casefold() == "pinkhaanynativeuitests.build" for part in path.parts):
            continue
        original = regular(path)
        raw = path.read_bytes()
        lines = [line.strip('"') for line in raw.decode().splitlines() if line]
        require(set(lines) == set(expected) and len(lines) == len(expected), "Exactly the original two Swift inputs must compile")
        require(all(regular(Path(line)) == expected[line] for line in lines), "Actual compiler source bytes differ")
        witnesses = namespace["compiler_invocations"](lifecycle, log, path)
        retained = retained_root / (str(len(lists)) + ".SwiftFileList")
        with retained.open("xb") as stream:
            stream.write(raw)
        require(regular(retained) == original, "Retained original compiler list differs")
        lists.append({"originalPath": str(path), "retained": ref(retained),
                      "sourcePaths": lines, "compilerInvocations": witnesses})
    require(lists, "Actual original Native23 swiftc/FileList evidence is absent")
    proof = {"schema": "pinkha-original-native23-swiftc-inputs-v1",
             "status": "PASS_EXACT_TWO_ORIGINAL_SWIFT_COMPILER_INPUTS_NOT_TEST_EXECUTION",
             "originalCompilerWitness": functions, "buildLog": ref(log),
             "compiledSources": expected, "actualCompilerFileLists": lists,
             "declaredLaunchMethods": value["declaredOriginalLaunchMethods"],
             "declaredHistoryMethods": value["declaredOriginalHistoryMethods"],
             "compiledMethodEnumerationExecuted": False, "testsExecuted": 0, "runtimeAdmission": False}
    write(output / "evidence/compiler-inputs.json", proof)
    return proof


def descriptor_proof(source, products, value):
    descriptors = sorted(products.glob("*.xctestrun"))
    require(len(descriptors) == 1, "One real original Native23 xctestrun is required")
    descriptor = descriptors[0]
    regular(descriptor)
    data = plistlib.loads(descriptor.read_bytes())
    require(isinstance(data, dict) and set(data) == {"__xctestrun_metadata__", TARGET}
            and isinstance(data["__xctestrun_metadata__"], dict)
            and type(data["__xctestrun_metadata__"].get("FormatVersion")) is int
            and data["__xctestrun_metadata__"]["FormatVersion"] == 1,
            "Original single UI-only v1 descriptor required")
    target = data[TARGET]
    require(isinstance(target, dict) and target.get("IsUITestBundle") is True and target.get("UITargetAppPath", "") == ""
            and target.get("UITargetAppBundleIdentifier", "") == ""
            and target.get("OnlyTestIdentifiers", []) == [] and target.get("SkipTestIdentifiers", []) == []
            and isinstance(target.get("DependentProductPaths", []), list)
            and not any(key in group for group in (target, data["__xctestrun_metadata__"])
                        for key in ("TestPlans", "TestConfigurations", "TestPlanName")),
            "The compiled runner may not bind another App or filter its original methods")
    item = value["originalDescriptorHelper"]
    namespace = {"require": require, "PurePosixPath": PurePosixPath}
    original = original_functions(source / item["path"], item["sha256"], item["extractedFunctions"], namespace)
    path = namespace["product_path"]
    host = path(target.get("TestHostPath"), products)
    bundle = path(target.get("TestBundlePath"), products, host_path=host)
    require(host.name == TARGET + "-Runner.app" and bundle == host / "PlugIns" / (TARGET + ".xctest")
            and host.is_dir() and bundle.is_dir(), "Actual original runner/test bundle missing")
    for raw in target.get("DependentProductPaths", []):
        dependency = path(raw, products, host_path=host)
        require(dependency == host or dependency == bundle or dependency.is_relative_to(host),
                "UI-only descriptor contains a foreign dependent product")
    binaries = []
    for directory, executable in ((host, TARGET + "-Runner"), (bundle, TARGET)):
        info = plistlib.loads((directory / "Info.plist").read_bytes())
        require(info.get("CFBundleExecutable") == executable, "Original compiled executable identity differs")
        binaries.append(ref(directory / executable))
    return {"descriptor": ref(descriptor), "target": TARGET, "originalProductPathHelper": original,
            "testHostPath": str(host), "testBundlePath": str(bundle), "executables": binaries,
            "runtimeAppBindingAdded": False, "compiledMethodEnumerationExecuted": False}


def finish_record(custody, record, evidence, primary):
    """Close only the actual child and preserve the first failure through writes."""
    try:
        observed = custody.finish()
        record["ownedCompilerCustody"] = observed
        if observed["status"] == "UNRESOLVED" or observed["cleanupErrors"]:
            raise RuntimeError("Original Native23 compiler ownership is not safely closed")
    except BaseException as cleanup_error:
        record.setdefault("finalizationErrors", []).append(error(cleanup_error))
        if primary is None:
            primary = cleanup_error
        else:
            primary.add_note("Native23 owned cleanup also failed: " + repr(cleanup_error))
    if primary is not None:
        record["status"] = "FAIL_OR_NOT_RUN"
        record.setdefault("firstFailure", error(primary))
    record["finished"] = time.time()
    try:
        write(evidence / "receipt.json", record)
    except BaseException as receipt_error:
        if primary is None:
            primary = receipt_error
        else:
            primary.add_note("Native23 final receipt also failed: " + repr(receipt_error))
    return primary


def build(owner, args, root, plan, control, source, environment, intake):
    """Called once, only after the actual original App and Stage1 compile PASS."""
    value = contract()
    require(plan.get("native23Compiler") == declared_plan()
            and json.loads((root / "native23-source-intake.json").read_bytes()) == intake
            and source_rows(source, value) == intake["sourceInputs"], "Native23 preflight changed")
    item = value["originalLifecycle"]
    lifecycle = original_module(control / item["path"], item["sha256"], "native23_original_owned_lifecycle")
    parents, parent_build, products_before = parent_receipts(owner, root, plan, source, lifecycle)
    output = root / "native23-ui"
    output.mkdir(mode=0o700, exist_ok=False)
    evidence = output / "evidence"
    evidence.mkdir(mode=0o700)
    record = {"schema": "pinkha-hosted-native23-ui-build-v1", "status": "FAIL_OR_NOT_RUN",
              "sourceCommit": plan["appSourceSHA"], "sourceTree": plan["appSourceTree"],
              "controlCommit": plan["controlCommit"], "contract": ref(control / PREFIX / CONTRACT_NAME),
              "helper": ref(Path(__file__).resolve()), "owner": ref(control / PREFIX / "run.py"),
              "rootPlan": ref(Path(args.plan)), "originalSharedBuild": parents,
              "inputPins": plan["pins"], "nativeSourceManifestSHA256": plan["pins"]["nativeSourceManifestSHA256"],
              "resourcePolicy": value["resourcePolicy"], "started": time.time(),
              "testsExecuted": 0, "runtimeAdmission": False, "applicationBuildTargetsInThisPhase": 0,
              "nativeLibraryBuildsInThisPhase": 0, "releaseArchive": False, "testFlightUploaded": False}
    custody = PhaseCustody(lifecycle, evidence / "owned-lifecycle", source)
    primary = None
    try:
        write(evidence / "original-shared-products-before.json", products_before)
        projection, project, generated = projected_source(source, output, value, lifecycle)
        argv, declaration = original_argv(source, output, project, projection, value)
        write(evidence / "original-argv-declaration.json", declaration)
        worker = supervisor(owner, control, source, root, output, plan, value, lifecycle, custody, environment)
        source_before = worker["source_state"]()
        require(source_before == json.loads((root / "build16/source-after.json").read_bytes()),
                "Complete original App and Native23 source snapshots differ")
        write(evidence / "source-before.json", source_before)
        phase = worker["run_phase"](PHASE, argv, value["resourcePolicy"]["phaseTimeoutSeconds"])
        custody.require_closed()
        record["compiler"] = phase
        require(owner.source_identity(source, plan["appSourceSHA"], plan["appSourceTree"])["status"] == "",
                "Original common source identity changed during Native23 compilation")
        source_after = worker["source_state"]()
        write(evidence / "source-after.json", source_after)
        require(source_after == source_before and source_rows(source, value) == intake["sourceInputs"],
                "Exact original source inputs changed during Native23 compilation")
        generated_after = lifecycle.inventory(output / "source")
        write(evidence / "generated-inputs-after.json", generated_after)
        require(generated_after == generated, "Original generated project/scheme/Swift bytes or modes changed")
        parents_after, _, products_after = parent_receipts(owner, root, plan, source, lifecycle)
        write(evidence / "original-shared-products-after.json", products_after)
        require(parents_after == parents and products_after == products_before,
                "Original App/Stage1 receipts or complete products changed")
        controls_after = owner.control_identity(control, plan["controlCommit"])
        require(controls_after == json.loads((root / "controls-after.json").read_bytes()),
                "Original executed control closure changed during Native23 compilation")
        write(evidence / "controls-after.json", controls_after)
        compiler_proof(source, output, value, phase, lifecycle)
        products = output / "derived/Build/Products"
        product_inventory = lifecycle.inventory(products)
        write(evidence / "products-with-modes.json", product_inventory)
        descriptor = descriptor_proof(source, products, value)
        write(evidence / "compiled-descriptor.json", descriptor)
        record.update(status="PASS_ORIGINAL_NATIVE23_UI_RUNNER_BUILD_NOT_ACCEPTANCE",
                      originalSharedBuildUnchanged=True, sourceUnchanged=True,
                      compilerProof=ref(evidence / "compiler-inputs.json"),
                      compiledDescriptor=ref(evidence / "compiled-descriptor.json"),
                      productInventory=ref(evidence / "products-with-modes.json"),
                      productsRoot=str(products), generatedInputsBefore=ref(evidence / "generated-inputs-before.json"),
                      generatedInputsAfter=ref(evidence / "generated-inputs-after.json"))
    except BaseException as exc:
        primary = exc
        record["firstFailure"] = error(exc)
    finally:
        primary = finish_record(custody, record, evidence, primary)
    if primary is not None:
        raise primary
    return ref(evidence / "receipt.json")
