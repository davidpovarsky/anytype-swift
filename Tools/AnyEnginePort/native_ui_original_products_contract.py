#!/usr/bin/env python3
"""Fixed, two-origin admission for original native UI Products. No build path."""
from __future__ import annotations
import ast
import copy
import hashlib
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = "Tools/AnyEnginePort/native-ui-original-products-451082.json"
CONTRACT_SHA = "c3c152137febebbec644d72fa8c72e03c9657a52309360e57b36854d53846a32"
WORKFLOW = ".github/workflows/pinkha-any-native-ui-original-products.yml"
CENTRAL = ".github/workflows/torah-inspector-ipados27.yml"
CONTROL_PATHS = (
    CONTRACT_PATH, WORKFLOW, CENTRAL,
    "Tools/AnyEnginePort/native_ui_original_products.py",
    "Tools/AnyEnginePort/native_ui_original_products_contract.py",
    "Tools/AnyEnginePort/native_ui_original_products_results.py",
)
PROFILE = "pinkha-native-ui-original-products-v1"
COPY_NAME = "CurrentNativeUIOriginalProducts.xctestrun"
EVIDENCE = ROOT / "build/any-patched-evidence"
WORK = ROOT / "build/native-ui-original-products"
DERIVED = ROOT / "build/any-native-app-derived"
ADMISSION = EVIDENCE / "native-ui-original-products-admission.json"
STAGES = {
    "native-ui-continuation": ("native-ui-continuation-four", 360, (
        "NativeLaunchTests/testHierarchyMoveAndPropertyVisibilityRetainNativeBodyAndType",
        "NativeLaunchTests/testHierarchyDragIntoFolderPersistsAfterColdReopen",
        "NativeLaunchTests/testSourceDragIntoNativeEditorPreservesTargetAndColdReopens",
        "NativeLaunchTests/testHanlinSelectedContextAndSeparateCreateConsentSurviveColdReopen")),
    "archive-roundtrip": ("archive-roundtrip", 1800, (
        "NativeLaunchTests/testCanonicalArchiveFilesRoundtripPreservesMappingAndBodies",)),
    "custom-type": ("native-custom-type", 360, (
        "NativeLaunchTests/testCustomCanonicalTypeTransitionPreservesNativeDocumentAcrossColdReopen",)),
    "native-history": ("native-history", 1800, (
        "NativeHistoryTests/testSavedHebrewVersionsRemainReadOnlyAcrossCloseBackgroundAndColdReopen",)),
}

def require(condition, reason):
    if not condition:
        raise ValueError(reason)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode())

def strict_json(raw):
    def unique(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)

def regular(path, maximum=8 * 1024**2):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= maximum,
            "bounded_regular_file_required")
    return path.read_bytes()

def data(path):
    return strict_json(regular(path))

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")

def file_sha(path):
    require(path.is_file() and not path.is_symlink(), "regular_digest_file_required")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024**2):
            digest.update(chunk)
    return digest.hexdigest()

def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, timeout=30)

def contract(root=ROOT):
    raw = regular(root / CONTRACT_PATH, 1024**2)
    require(sha(raw) == CONTRACT_SHA, "fixed_original_contract_changed")
    result = strict_json(raw)
    require(result["contract"] == PROFILE and result["origin"]["executedMethods"] == 0
            and result["origin"]["applicationBuilds"] == result["origin"]["uiRunnerBuilds"] == 1
            and len(result["retainedMethods"]) == 22, "fixed_origin_contract_invalid")
    return result

def source_functions(path, names):
    raw = regular(path, 2 * 1024**2)
    tree = ast.parse(raw.decode("utf-8"))
    lines = raw.splitlines(keepends=True)
    result = {}
    for name in names:
        found = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
        require(len(found) == 1, "one_fixed_helper_function_required")
        node = found[0]
        start = min([node.lineno] + [decorator.lineno for decorator in node.decorator_list])
        # AST locates the exact slice; the pin is bytes, independent of host AST fields.
        result[name] = sha(b"".join(lines[start - 1:node.end_lineno]))
    return result

def provider_proof(fixed, root=ROOT):
    proof = fixed["providerQualification"]
    for path, expected in {**proof["inputs"], **proof["proofFiles"]}.items():
        require(sha(regular(root / path)) == expected, "qualified_provider_input_changed:" + path)
    qualification = data(root / proof["qualificationPath"])
    require(qualification["new_distinct_controls"] == 2
            and qualification["first_attempt_passed_method_retained"] == 1
            and qualification["second_attempt_only_failed_method_passed"] == 1
            and qualification["old_control_or_product_methods_reexecuted"] == 0
            and qualification["original_failure_preserved"] is True,
            "qualified_provider_scope_changed")
    dependency = fixed["runtimeDependencies"]
    gate = root / "Tools/PinkhaSimulatorGate"
    require(sha(regular(gate / "simulator_selection.py")) == dependency["simulatorSelectionSHA256"],
            "runtime_selection_helper_changed")
    require(source_functions(gate / "sdk06_enumeration_probe.py", dependency["normalizerFunctions"])
            == dependency["normalizerFunctions"], "runtime_normalizer_scope_changed")
    return {"qualificationSHA256": proof["proofFiles"][proof["qualificationPath"]],
            "distinctNewControls": 2, "originalBoundaryFailurePreserved": True,
            "inputs": proof["inputs"], "runtimeDependencies": dependency}

def control_context(fixed, root=ROOT):
    require(root.resolve() == ROOT.resolve(), "control_root_override_forbidden")
    require(os.environ.get("GITHUB_ACTIONS") == "true"
            and os.environ.get("GITHUB_REPOSITORY") == fixed["repository"],
            "actual_repository_actions_context_required")
    commit = git(root, "rev-parse", "HEAD").decode().strip()
    require(re.fullmatch(r"[0-9a-f]{40}", commit) and commit == os.environ.get("GITHUB_SHA")
            and commit != fixed["origin"]["commit"], "separate_current_control_source_required")
    require(os.environ.get("GITHUB_REF") == "refs/heads/" + fixed["controlBranch"],
            "current_control_branch_mismatch")
    workflow_ref = os.environ.get("GITHUB_WORKFLOW_REF", "")
    permitted = {fixed["repository"] + "/" + path + "@" + os.environ["GITHUB_REF"]
                 for path in (WORKFLOW, CENTRAL)}
    require(workflow_ref in permitted, "dedicated_control_workflow_required")
    run, attempt = os.environ.get("GITHUB_RUN_ID", ""), os.environ.get("GITHUB_RUN_ATTEMPT", "")
    require(run.isdigit() and run != fixed["origin"]["runID"] and attempt.isdigit() and int(attempt) > 0,
            "new_current_run_and_attempt_required")
    require(not git(root, "diff", "--name-only", "HEAD"), "dirty_current_control_checkout")
    require(not git(root, "ls-files", "--others", "--exclude-standard"), "unexpected_untracked_control_source")
    inputs = {}
    for path in CONTROL_PATHS:
        raw = regular(root / path, 2 * 1024**2)
        require(raw == git(root, "show", commit + ":" + path), "physical_control_source_differs_from_git")
        inputs[path] = sha(raw)
    proof = provider_proof(fixed, root)
    temp = Path(os.environ.get("RUNNER_TEMP", "")).resolve()
    require(os.environ.get("RUNNER_TEMP") and temp.is_dir() and temp != root.resolve()
            and not temp.is_relative_to(root.resolve()) and not root.resolve().is_relative_to(temp),
            "independent_runner_temp_required")
    return {"controlCommit": commit, "currentRunID": run, "currentRunAttempt": int(attempt),
            "controllerSourceInputs": inputs, "qualifiedProvider": proof}

def paths(ctx):
    temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    app = temp / ("native-ui-original-app-" + ctx["currentRunID"] + "-" + str(ctx["currentRunAttempt"]))
    return {"app": app, "evidence": EVIDENCE, "work": WORK, "derived": DERIVED,
            "products": DERIVED / "Build/Products", "originals": EVIDENCE / "original-451082",
            "download": WORK / "download"}

def validate_paths(locations, control=ROOT):
    resolved = {k: p.resolve() for k, p in locations.items()}
    app, evidence, work, products = (resolved[k] for k in ("app", "evidence", "work", "products"))
    control = control.resolve()
    require(app != control and not app.is_relative_to(control) and not control.is_relative_to(app),
            "original_app_and_control_must_be_disjoint")
    require(evidence == control / "build/any-patched-evidence"
            and work == control / "build/native-ui-original-products"
            and products == control / "build/any-native-app-derived/Build/Products",
            "exact_current_owned_output_paths_required")
    require(resolved["originals"] == evidence / "original-451082"
            and resolved["download"] == work / "download"
            and resolved["derived"] == products.parent.parent, "original_output_origin_mismatch")
    for raw in locations.values():
        require(not raw.is_symlink() and raw.absolute() == raw.resolve(), "symlink_output_root_forbidden")
    return resolved

def public_command(command, directory, label, timeout=30):
    directory.mkdir(parents=True, exist_ok=True)
    require(re.fullmatch(r"[a-z0-9-]+", label), "fixed_command_label_required")
    record = {"command": command, "cwd": str(ROOT), "timeoutSeconds": timeout,
              "status": "FAIL"}
    stdout = stderr = b""
    failure = None
    try:
        process = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=timeout)
        stdout, stderr = process.stdout, process.stderr
        record["returncode"] = process.returncode
        record["status"] = "PASS" if process.returncode == 0 else "FAIL"
    except (subprocess.TimeoutExpired, OSError) as error:
        stdout = getattr(error, "stdout", b"") or b""
        stderr = getattr(error, "stderr", b"") or b""
        record["failureKind"] = type(error).__name__
        record["errno"] = getattr(error, "errno", None)
        failure = error
    for suffix, raw in (("stdout", stdout), ("stderr", stderr)):
        require(isinstance(raw, bytes), "binary_command_stream_required")
        path = directory / (label + "." + suffix)
        with path.open("xb") as stream:
            stream.write(raw)
        record[suffix] = {"bytes": len(raw), "sha256": sha(raw), "path": path.name}
    dump(directory / (label + ".json"), record)
    if failure is not None:
        raise failure
    require(record.get("returncode") == 0, "owned_command_failed:" + label)
    return stdout

def validate_original_api(run, artifact, jobs, fixed):
    origin = fixed["origin"]
    require(run.get("id") == int(origin["runID"]) and run.get("run_attempt") == origin["runAttempt"]
            and run.get("head_sha") == origin["commit"] and run.get("head_branch") == origin["branch"]
            and run.get("path") == origin["workflow"] and run.get("event") == "workflow_dispatch"
            and run.get("status") == "completed" and run.get("conclusion") == "failure"
            and run.get("repository", {}).get("full_name") == fixed["repository"]
            and run.get("head_repository", {}).get("full_name") == fixed["repository"],
            "original_failed_run_identity_changed")
    expected = fixed["artifact"]
    require(artifact.get("id") == expected["id"] and artifact.get("name") == expected["name"]
            and artifact.get("expired") is False and artifact.get("size_in_bytes") == expected["bytes"]
            and artifact.get("digest") == "sha256:" + expected["sha256"]
            and artifact.get("workflow_run", {}).get("id") == int(origin["runID"])
            and artifact.get("workflow_run", {}).get("head_sha") == origin["commit"],
            "original_product_carrier_identity_changed")
    matches = [j for j in jobs.get("jobs", []) if j.get("id") == origin["jobID"]]
    require(len(matches) == 1, "one_original_build_job_required")
    job = matches[0]
    require(job.get("run_id") == int(origin["runID"]) and job.get("head_sha") == origin["commit"]
            and job.get("status") == "completed" and job.get("conclusion") == "failure",
            "original_build_job_origin_changed")
    steps = job.get("steps", [])
    for group, conclusion in (("originalSuccessfulSteps", "success"), ("originalUnexecutedSteps", "skipped")):
        for number, name in fixed[group].items():
            found = [s for s in steps if s.get("number") == int(number) and s.get("name") == name]
            require(len(found) == 1 and found[0].get("conclusion") == conclusion,
                    "original_build_or_zero_execution_proof_changed")
    return {"origin": origin, "successfulBuildInvocation": 1, "executedCurrentMethodsAtOrigin": 0}

def selected_member(name):
    exact = {"native-shared-products.json", "native-continuation-retained.json", "native-reuse.json",
             "original-native-artifact.json", "continuation-products-postflight.json", "simulator.json",
             "xcode-version.txt", "source-sha.txt", "native-app-bundle.json", "native-ui-build.log",
             "native-products-originals/manifest.json",
             "native-products-originals/PinkhaAnyNativeApp_iphonesimulator27.0-arm64.xctestrun"}
    return name in exact or name.startswith(("retained-450382-originals/", "retained-450876-originals/"))

def safe_relative(name):
    path = PurePosixPath(name)
    require(isinstance(name, str) and name and not path.is_absolute() and "\\" not in name
            and "\x00" not in name and all(p not in {".", "..", ""} for p in name.split("/"))
            and path.as_posix() == name, "unsafe_original_member_path")
    return path

def extract_originals(archive, destination, tar_path, fixed):
    require(archive.stat().st_size == fixed["artifact"]["bytes"]
            and file_sha(archive) == fixed["artifact"]["sha256"], "original_carrier_bytes_changed")
    require(not destination.exists() and not tar_path.exists(), "fresh_original_extraction_required")
    destination.mkdir(parents=True)
    expected = {x["name"]: x for x in fixed["zipMembers"]}
    with zipfile.ZipFile(archive) as stream:
        infos = stream.infolist()
        require(len(infos) == len(expected) and len({i.filename for i in infos}) == len(infos),
                "exact_original_zip_inventory_required")
        for info in infos:
            safe_relative(info.filename)
            wanted = expected.get(info.filename)
            require(wanted is not None and info.file_size == wanted["bytes"]
                    and (info.external_attr >> 16) == wanted["mode"]
                    and stat.S_ISREG(info.external_attr >> 16), "original_zip_entry_changed")
            target = None
            if selected_member(info.filename):
                target = destination / info.filename
            elif info.filename == "native-products-originals/native-ui-products.tar.gz":
                target = tar_path
            if target is not None:
                target.parent.mkdir(parents=True, exist_ok=True)
                with stream.open(info) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)
                require(target.stat().st_size == info.file_size, "truncated_original_zip_member")
    require(tar_path.stat().st_size == fixed["productArchive"]["archiveBytes"]
            and file_sha(tar_path) == fixed["productArchive"]["archiveSHA256"],
            "original_product_tar_changed")
    for name, expected_sha in fixed["metadataSHA256"].items():
        require(sha(regular(destination / name)) == expected_sha, "original_metadata_changed:" + name)

def restore_tar(archive, products, entries):
    require(not products.exists(), "fresh_products_destination_required")
    expected = {x["name"]: x for x in entries}
    require(len(expected) == len(entries) and expected, "unique_original_product_inventory_required")
    for name in expected:
        safe_relative(name)
    products.mkdir(parents=True)
    seen = set()
    with tarfile.open(archive, "r:gz") as stream:
        for entry in stream:
            name = entry.name
            safe_relative(name)
            wanted = expected.get(name)
            require(wanted is not None and name not in seen, "unadmitted_or_duplicate_product_entry")
            seen.add(name)
            kind = "directory" if entry.isdir() else "file" if entry.isfile() else "forbidden"
            require(kind == wanted["kind"] and entry.mode == wanted["mode"]
                    and entry.size == wanted["bytes"], "product_entry_type_mode_or_size_changed")
            target = products / name
            require(target.resolve().is_relative_to(products.resolve()) and not target.is_symlink(),
                    "product_restore_path_escape")
            if entry.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with stream.extractfile(entry) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)
                require(file_sha(target) == wanted["sha256"], "restored_product_bytes_changed")
            target.chmod(entry.mode)
    require(seen == set(expected), "missing_original_product_entry")

def verify_entries(products, entries, copy_sha=None):
    expected = {x["name"]: x for x in entries}
    seen = set()
    for path in products.rglob("*"):
        name = path.relative_to(products).as_posix()
        if name == COPY_NAME and copy_sha is not None:
            require(path.is_file() and not path.is_symlink() and file_sha(path) == copy_sha,
                    "copied_runtime_descriptor_changed")
            continue
        if name == "Debug-iphonesimulator" and path.is_dir() and not path.is_symlink():
            continue
        wanted = expected.get(name)
        require(wanted is not None and not path.is_symlink(), "unexpected_restored_product_member")
        seen.add(name)
        kind = "directory" if path.is_dir() else "file" if path.is_file() else "forbidden"
        require(kind == wanted["kind"] and stat.S_IMODE(path.stat().st_mode) == wanted["mode"],
                "restored_product_mode_or_type_changed")
        if kind == "file":
            require(path.stat().st_size == wanted["bytes"] and file_sha(path) == wanted["sha256"],
                    "restored_product_file_changed")
    require(seen == set(expected), "restored_product_member_missing")
    require(copy_sha is None or (products / COPY_NAME).is_file(), "copied_runtime_descriptor_missing")
    return {"originalRegularFiles": sum(x["kind"] == "file" for x in entries),
            "originalDirectories": sum(x["kind"] == "directory" for x in entries),
            "originalEntriesSHA256": canonical(entries), "allOriginalBytesAndModesUnchanged": True}

def control_module_binding(module, relative):
    expected = (ROOT / relative).resolve()
    observed = Path(getattr(module, "__file__", "")).resolve()
    require(observed == expected and expected.is_file() and not (ROOT / relative).is_symlink(),
            "actual_current_control_module_required:" + relative)
    return {"path": relative, "sha256": sha(regular(expected, 2 * 1024**2)),
            "origin": "CURRENT_CONTROL_CHECKOUT", "claim": "Actual imported module; not a claim every function ran"}


def runtime_pair(runtimes, devices, fixed):
    policy = fixed["runtime"]
    rs = [x for x in runtimes.get("runtimes", []) if x.get("identifier") == policy["identifier"]]
    ds = [x for x in devices.get("devicetypes", []) if x.get("identifier") == policy["deviceType"]]
    require(len(rs) == len(ds) == 1, "exact_original_runtime_and_device_type_required")
    runtime = rs[0]
    require(runtime.get("version") == policy["version"] and runtime.get("buildversion") == policy["buildversion"]
            and runtime.get("isAvailable") is True and policy["architecture"] in runtime.get("supportedArchitectures", []),
            "original_runtime_version_build_or_architecture_changed")
    gate = str(ROOT / "Tools/PinkhaSimulatorGate")
    if gate not in sys.path:
        sys.path.append(gate)
    selector = importlib.import_module("simulator_selection")
    binding = control_module_binding(selector, "Tools/PinkhaSimulatorGate/simulator_selection.py")
    pair = selector.choose_pair({"runtimes": rs}, {"devicetypes": ds}, product_family="iPad", major=27,
                                architecture=policy["architecture"])
    require(pair["selection"]["runtimeIdentifier"] == policy["identifier"]
            and pair["selection"]["deviceTypeIdentifier"] == policy["deviceType"], "runtime_pair_selection_changed")
    return {**pair, "selection": {**pair["selection"], "currentControlModule": binding}}

def copied_descriptor(original, copied, runtime, fixed):
    require(copied.name == COPY_NAME and copied.parent.resolve() == original.parent.resolve()
            and not copied.is_symlink(), "copied_descriptor_must_preserve_original_TESTROOT")
    item = fixed["productArchive"]["xctestrun"]
    require(len(item) == 1 and sha(regular(original)) == item[0]["sha256"]
            and original.name == item[0]["path"] and not copied.exists(), "original_descriptor_not_admitted")
    configuration = plistlib.loads(regular(original))
    require(configuration.get("__xctestrun_metadata__", {}).get("FormatVersion") == 1
            and set(configuration) == {"__xctestrun_metadata__", "PinkhaAnyNativeUITests"},
            "exact_original_single_ui_descriptor_required")
    before = copy.deepcopy(configuration)
    gate = str(ROOT / "Tools/PinkhaSimulatorGate")
    if gate not in sys.path:
        sys.path.append(gate)
    normalizer = importlib.import_module("sdk06_enumeration_probe")
    bindings = [
        control_module_binding(normalizer, "Tools/PinkhaSimulatorGate/sdk06_enumeration_probe.py"),
        control_module_binding(normalizer.component, "Tools/PinkhaSimulatorGate/shared_editor_existing_build.py"),
        control_module_binding(normalizer.component.host, "Tools/Hanlin/run_host_tests.py"),
    ]
    change = normalizer.normalize_runtime_injection(configuration["PinkhaAnyNativeUITests"], runtime,
                 expected_original_token=fixed["runtime"]["originalMainThreadChecker"])
    inverse = copy.deepcopy(configuration)
    inverse["PinkhaAnyNativeUITests"]["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"] = (
        before["PinkhaAnyNativeUITests"]["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"])
    require(inverse == before, "only_one_runtime_injection_field_may_change")
    with copied.open("xb") as stream:
        plistlib.dump(configuration, stream, sort_keys=False)
    return {"path": str(copied), "sha256": file_sha(copied),
            "originalSHA256": item[0]["sha256"], "normalization": change,
            "originalDescriptorUnchanged": True, "sameDirectoryPreservesTESTROOT": True,
            "currentControlModuleBindings": bindings}

def legacy_modules(app):
    target = app / "Tools/AnyEnginePort"
    if str(target) not in sys.path:
        sys.path.insert(0, str(target))
    names = ("verify_archive_roundtrip", "verify_native_test_execution", "verify_custom_type",
             "native_continuation_sources", "continue_native_acceptance", "native_ui_followup_retention")
    result = {}
    for name in names:
        module = importlib.import_module(name)
        require(Path(module.__file__).resolve() == (target / (name + ".py")).resolve(),
                "legacy_validator_must_come_from_immutable_app:" + name)
        result[name] = module
    return result

def application_source(app, fixed, modules):
    require(app.is_dir() and not app.is_symlink()
            and git(app, "rev-parse", "HEAD").decode().strip() == fixed["origin"]["commit"],
            "immutable_application_checkout_required")
    require(not git(app, "diff", "--name-only", "HEAD")
            and not git(app, "ls-files", "--others", "--exclude-standard"),
            "immutable_application_checkout_changed")
    source = modules["native_continuation_sources"]
    closure = source.source_tree(fixed["origin"]["commit"], app)
    for name, identity in closure.items():
        raw = regular(app / name, 32 * 1024**2)
        require(source.blob(raw) == identity, "actual_protected_application_source_changed:" + name)
    for name, expected in fixed["frozenBuild"]["sourceInputs"].items():
        require(sha(regular(app / name)) == expected, "actual_original_build_input_changed:" + name)
    return {"applicationCommit": fixed["origin"]["commit"], "protectedFiles": len(closure),
            "protectedGitBlobsSHA256": canonical(closure),
            "originalFrozenInputs": fixed["frozenBuild"]["sourceInputs"]}

def retained_proof(originals, app, fixed, modules):
    base = modules["continue_native_acceptance"]
    followup = modules["native_ui_followup_retention"]
    older = base.verify_originals(originals / base.RETAINED_DIR, app)
    newer = followup.verify_originals(originals / followup.DIRECTORY, base, app)
    current_binding = data(originals / "native-reuse.json")
    for directory in (originals / base.RETAINED_DIR, originals / followup.DIRECTORY):
        prior = data(directory / "native-reuse.json")
        require(current_binding == {**prior, "consumerCommit": fixed["origin"]["commit"]},
                "retained_native_binary_or_source_binding_changed")
    require(current_binding["artifactReceiptSHA256"] ==
            sha(regular(originals / "original-native-artifact.json")),
            "retained_native_artifact_original_bytes_changed")
    proof = modules["native_continuation_sources"].verify_sources(fixed["origin"]["commit"], app)
    followup_source = followup.verify_sources(fixed["origin"]["commit"], app)
    origins = dict(older["retainedMethodsWithOrigins"])
    require(not set(origins).intersection(followup.PASSED), "retained_original_method_overlap")
    origins.update({name: {"runID": followup.RUN, "commit": followup.SOURCE} for name in followup.PASSED})
    original = data(originals / "native-continuation-retained.json")
    require(origins == fixed["retainedMethods"] == original["retainedMethodsWithOrigins"]
            and original["retainedMethodCount"] == 22 and original["testsExecutedThisRun"] == 0
            and original["consumerCommit"] == fixed["origin"]["commit"]
            and original["consumerRunID"] == fixed["origin"]["runID"]
            and original["sourceProof"] == proof and original["followupSourceProof"] == followup_source,
            "twenty_two_original_retained_methods_not_proven")
    require(original["followupOriginalProof"] == newer, "original_followup_proof_changed")
    return {"retainedMethodCount": 22, "retainedMethodsWithOrigins": origins,
            "retainedMethodsExecutedThisRun": 0, "originalFailedBatchesRemainFailure": True,
            "originalAdmissionSHA256": sha(regular(originals / "native-continuation-retained.json")),
            "sourceProof": proof, "followupSourceProof": followup_source,
            "originalRawProof": {"older": older, "followup": newer}}

def plan(stage, descriptor, udid, result):
    require(stage in STAGES and str(uuid.UUID(udid)).upper() == udid,
            "fixed_stage_and_owned_uuid_required")
    profile, allowance, methods = STAGES[stage]
    command = ["xcodebuild", "test-without-building",
               *["-only-testing:PinkhaAnyNativeUITests/" + name for name in methods],
               "-xctestrun", str(descriptor), "-destination", "platform=iOS Simulator,id=" + udid,
               "-resultBundlePath", str(result), "-parallel-testing-enabled", "NO",
               "-test-timeouts-enabled", "YES", "-default-test-execution-time-allowance", str(allowance),
               "-maximum-test-execution-time-allowance", str(allowance),
               "ARCHS=arm64", "ONLY_ACTIVE_ARCH=YES", "CODE_SIGNING_ALLOWED=YES",
               "CODE_SIGNING_REQUIRED=YES", "CODE_SIGN_IDENTITY=-"]
    return {"stage": stage, "profile": profile, "methods": list(methods),
            "command": command, "applicationBuildsThisRun": 0, "uiRunnerBuildsThisRun": 0}

def validate_selection(selected, fixed):
    all_methods = [name for _, _, methods in STAGES.values() for name in methods]
    require(len(all_methods) == len(set(all_methods)) == 7
            and not set(all_methods).intersection(fixed["retainedMethods"]),
            "only_seven_previously_unexecuted_methods_may_run")
    require(selected == {stage: list(value[2]) for stage, value in STAGES.items()},
            "fixed_current_method_selection_changed")

def validate_admission_origin(record, fixed, ctx, locations):
    require(ctx.get("controlCommit") != fixed["origin"]["commit"]
            and ctx.get("currentRunID") != fixed["origin"]["runID"]
            and type(ctx.get("currentRunAttempt")) is int and ctx["currentRunAttempt"] > 0,
            "separate_current_control_and_run_required")
    expected = {"contract": PROFILE, "contractSHA256": CONTRACT_SHA,
                "applicationCommit": fixed["origin"]["commit"],
                "applicationCheckout": str(locations["app"]),
                "productsDirectory": str(locations["products"]),
                "originalArtifact": fixed["artifact"],
                "originalFrozenBuildSHA256": fixed["metadataSHA256"]["native-shared-products.json"],
                "originalProductOrigin": {"origin": fixed["origin"], "successfulBuildInvocation": 1,
                                         "executedCurrentMethodsAtOrigin": 0}, **ctx}
    require(record.get("status") == "ADMITTED_ORIGINAL_NATIVE_UI_PRODUCTS"
            and all(record.get(key) == value for key, value in expected.items()),
            "current_original_products_admission_origin_changed")
    for key in ("currentApplicationBuilds", "currentUIRunnerBuilds", "currentNativeLibraryBuilds",
                "currentMethodsExecutedAtAdmission"):
        require(type(record.get(key)) is int and record[key] == 0, "zero_current_builds_required")
    retained = record.get("retainedProof", {})
    require(retained.get("retainedMethodsWithOrigins") == fixed["retainedMethods"]
            and type(retained.get("retainedMethodCount")) is int and retained["retainedMethodCount"] == 22
            and type(retained.get("retainedMethodsExecutedThisRun")) is int
            and retained["retainedMethodsExecutedThisRun"] == 0,
            "original_retained_scope_changed")
    validate_selection(record.get("selection"), fixed)

def validate_owned_device_absence(inventory, owned_udid):
    require(isinstance(inventory, dict) and isinstance(inventory.get("devices"), dict),
            "explicit_device_inventory_dictionary_required")
    require(isinstance(owned_udid, str) and str(uuid.UUID(owned_udid)).upper() == owned_udid,
            "canonical_current_owned_uuid_required")
    seen = set()
    for runtime, rows in inventory["devices"].items():
        require(isinstance(runtime, str) and bool(runtime) and isinstance(rows, list),
                "typed_runtime_device_list_required")
        for device in rows:
            require(isinstance(device, dict) and isinstance(device.get("udid"), str),
                    "typed_observed_device_uuid_required")
            normalized = str(uuid.UUID(device["udid"])).upper()
            require(normalized == device["udid"].upper() and normalized not in seen,
                    "unique_canonical_observed_device_uuid_required")
            seen.add(normalized)
    require(owned_udid not in seen, "current_owned_device_still_present")
    return {"completeDeviceInventory": True, "enumeratedDeviceCount": len(seen),
            "ownedSimulatorUDID": owned_udid, "ownedDeviceAbsent": True}
