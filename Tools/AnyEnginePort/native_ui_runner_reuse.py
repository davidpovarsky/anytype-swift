#!/usr/bin/env python3
"""Reuse one sealed failed-run UI runner with the immutable original application.

The old build admission remains unchanged. This opt-in origin never manufactures
a current build receipt, and original failure is retained independently of reuse.
"""
from __future__ import annotations
import copy
import importlib
import json
import os
from pathlib import Path
import plistlib
import stat
import sys
import zipfile

import native_ui_transition as transition
import native_ui_transition_contract as contract
import native_ui_original_products_contract as original
import native_ui_original_products_readiness as owned

ROOT = Path(__file__).resolve().parents[2]
PROFILE = "pinkha-native-ui-retained-runner-45174286335-2-v1"
MANIFEST = ROOT / "Tools/AnyEnginePort/native-ui-runner-45174286335-2.json"
MANIFEST_SHA = "fd099336edb3823fa6b8631f6705d30e43c55bd030055879f13858c8cbaa84ca"
WORKFLOW = ".github/workflows/pinkha-any-native-ui-runner-continuation.yml"
CONTROL_INPUTS = (
    "Tools/AnyEnginePort/native_ui_runner_reuse.py",
    "Tools/AnyEnginePort/native_ui_runner_continuation.py",
    "Tools/AnyEnginePort/native-ui-runner-45174286335-2.json",
    WORKFLOW, ".github/workflows/torah-inspector-ipados27.yml",
)
REUSE = transition.EVIDENCE / "retained-runner-origin"
ORIGINALS = REUSE / "originals"
ADMISSION = REUSE / "admission.json"
LEDGER = REUSE / "generated-descriptors.json"
ARCHIVE = transition.EVIDENCE / "UIRunnerProducts.tar.gz"
PREFIX = "native-ui-transition-candidate/"
_SEAL = object()


def fixed():
    raw = contract.regular(MANIFEST, 128 * 1024)
    contract.require(contract.sha(raw) == MANIFEST_SHA, "fixed_retained_runner_manifest_changed")
    value = original.strict_json(raw)
    contract.require(value["protocol"] == PROFILE and value["limits"]["currentBuilds"] == 0,
                     "retained_runner_contract_changed")
    return value


def write_bytes(path, raw, mode=0o400):
    path = Path(path)
    contract.require(path.resolve() == path and not path.exists()
                     and path.parent.is_dir(), "exclusive_regular_evidence_path_required")
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(mode)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_json(path, value, mode=0o400):
    write_bytes(path, (json.dumps(value, sort_keys=True, indent=2) + "\n").encode(), mode)


def preload():
    contract.require(ROOT == original.ROOT == owned.ROOT == transition.ROOT,
                     "retained_runner_current_roots_disagree")
    gate = str(ROOT / "Tools/PinkhaSimulatorGate")
    if gate not in sys.path:
        sys.path.append(gate)
    normalizer = importlib.import_module("sdk06_enumeration_probe")
    pairs = (
        (sys.modules[__name__], "Tools/AnyEnginePort/native_ui_runner_reuse.py"),
        (transition, "Tools/AnyEnginePort/native_ui_transition.py"),
        (normalizer, "Tools/PinkhaSimulatorGate/sdk06_enumeration_probe.py"),
        (normalizer.component, "Tools/PinkhaSimulatorGate/shared_editor_existing_build.py"),
        (normalizer.component.host, "Tools/Hanlin/run_host_tests.py"),
        (normalizer.supervisor, "Tools/PinkhaSimulatorGate/run_owned_single_lane.py"),
        (normalizer.owned, "Tools/PinkhaSimulatorGate/wave15_batch.py"),
        (normalizer.simulator_selection, "Tools/PinkhaSimulatorGate/simulator_selection.py"),
    )
    bindings = [original.control_module_binding(module, relative) for module, relative in pairs]
    return normalizer, bindings


def current_inputs(state, manifest):
    names = tuple(dict.fromkeys((*CONTROL_INPUTS, *manifest["currentUIInputs"],
                                 *manifest["unchangedHelpers"])))
    observed = owned.git_source_bytes(
        ROOT, state["context"]["controlCommit"], {name: ROOT / name for name in names})
    for name, expected in (manifest["currentUIInputs"] | manifest["unchangedHelpers"]).items():
        contract.require(observed[name] == expected, "retained_runner_current_dependency_changed:" + name)
    return observed


def original_metadata(root, manifest):
    values = {}
    for name, expected in manifest["metadata"].items():
        raw = contract.regular(root / name, 128 * 1024)
        contract.require(len(raw) == expected["bytes"] and contract.sha(raw) == expected["sha256"],
                         "retained_runner_original_metadata_changed:" + name)
        values[name] = original.strict_json(raw)
    build = values[PREFIX + "build.json"]
    origin = manifest["origin"]
    contract.require(build["status"] == "BUILT_UI_ONLY_RUNNER_ORIGINAL_APP_UNCHANGED"
                     and build["controlCommit"] == origin["sourceCommit"]
                     and build["currentRunID"] == origin["runID"]
                     and build["currentRunAttempt"] == origin["runAttempt"]
                     and build["applicationCommit"] == manifest["originalApp"]["commit"]
                     and build["originalArtifact"] == manifest["originalApp"]["artifact"]
                     and build["originalApplicationCodeCarriersSHA256"]
                     == manifest["originalApp"]["codeCarriersSHA256"]
                     and build["uiRunnerBuildInvocations"] == 1
                     and build["applicationBuildsThisRun"] == build["nativeLibraryBuildsThisRun"]
                     == build["testsExecutedByBuild"] == build["retainedMethodsExecutedThisRun"] == 0
                     and build["originalProductsUnchanged"] is True
                     and build["ownedCommand"]["return_code"] == 0
                     and build["ownedCommand"]["ownedQuiescence"]["status"] == "PASS",
                     "original_ui_build_origin_not_admitted")
    before = values[PREFIX + "build-source-before.json"]
    contract.require(all(before[key] == build["sourceAfter"][key] for key in ("direct", "loaded")),
                     "original_runner_source_changed_during_build")
    for path, digest in manifest["currentUIInputs"].items():
        contract.require(before["direct"][path] == digest, "original_ui_input_binding_changed")
    generated = values[PREFIX + "generated-project.json"]["generatedInputs"]
    products = values[PREFIX + "runner-products.json"]
    expected_products = {item["name"][len("Build/Products/"):]:
                         {k: v for k, v in item.items() if k != "name" and
                          not (k == "bytes" and item["kind"] == "directory")}
                         for item in manifest["entries"] if item["name"].startswith("Build/Products/")}
    expected_generated = {item["name"][len("Source/"):]:
                          {k: item[k] for k in ("bytes", "mode", "sha256")}
                          for item in manifest["entries"] if item["name"].startswith("Source/")}
    contract.require(products == expected_products and generated == expected_generated,
                     "original_archive_manifest_layers_disagree")
    for stage, (_, _, methods) in contract.STAGES.items():
        value = values[PREFIX + stage + "/result.json"]
        cases = {method + "()": "Failed" for method in methods}
        contract.require(value["status"] == "FAIL" and value["testCommandInvoked"] is True
                         and value["controlCommit"] == origin["sourceCommit"]
                         and value["currentRunID"] == origin["runID"]
                         and value["currentRunAttempt"] == origin["runAttempt"]
                         and value["partialNamed"]["actualNamedCases"] == cases
                         and value["partialNamed"]["actualNamedPasses"] == []
                         and value["retainedMethodsExecutedThisRun"] == 0,
                         "original_five_failed_outcomes_must_remain_failed")
        contract.exact_enumeration(values[PREFIX + stage + "/enumeration.json"], stage)
    return values


def validate_api(run, artifact, jobs, manifest):
    origin, fixed_artifact = manifest["origin"], manifest["artifact"]
    contract.require(str(run["id"]) == origin["runID"] and run["run_attempt"] == origin["runAttempt"]
                     and run["head_sha"] == origin["sourceCommit"] and run["head_branch"] == origin["branch"]
                     and run["status"] == "completed" and run["conclusion"] == "failure",
                     "exact_original_failed_run_required")
    contract.require(str(artifact["id"]) == fixed_artifact["id"]
                     and artifact["name"] == fixed_artifact["name"]
                     and artifact["size_in_bytes"] == fixed_artifact["bytes"]
                     and artifact["digest"] == "sha256:" + fixed_artifact["sha256"]
                     and artifact["expired"] is False
                     and str(artifact["workflow_run"]["id"]) == origin["runID"]
                     and artifact["workflow_run"]["head_sha"] == origin["sourceCommit"],
                     "exact_original_runner_artifact_required")
    found = [job for job in jobs["jobs"] if str(job["id"]) == origin["jobID"]]
    contract.require(len(found) == 1, "one_original_ui_job_required")
    job = found[0]
    contract.require(str(job["run_id"]) == origin["runID"] and job["run_attempt"] == origin["runAttempt"]
                     and job["head_sha"] == origin["sourceCommit"]
                     and str(job["runner_id"]) == origin["runnerID"]
                     and job["status"] == "completed" and job["conclusion"] == "failure",
                     "original_ui_job_identity_changed")
    expected = {"Build and preserve only the new UI runner": "success",
                "Enumerate and execute the four changed failed methods": "failure",
                "Enumerate and execute the changed Files roundtrip method": "failure"}
    for name, outcome in expected.items():
        rows = [step for step in job["steps"] if step["name"] == name]
        contract.require(len(rows) == 1 and rows[0]["conclusion"] == outcome,
                         "original_ui_step_evidence_changed:" + name)
    return {"runID": origin["runID"], "runAttempt": origin["runAttempt"],
            "sourceCommit": origin["sourceCommit"], "jobID": origin["jobID"],
            "artifactID": fixed_artifact["id"], "originalConclusion": "failure"}


def layout(manifest):
    expected = {}
    for entry in manifest["entries"]:
        name = entry["name"]
        original.safe_relative(name)
        if name.startswith("Build/Products/"):
            relative = "derived/" + name
        else:
            contract.require(name.startswith("Source/"), "only_original_products_and_generated_source")
            relative = "source/" + name[len("Source/"):]
        contract.require(relative not in expected, "duplicate_restored_member")
        expected[relative] = {k: v for k, v in entry.items() if k != "name"}
    contract.require(len(expected) == 24, "exact_twenty_four_original_members_required")
    for relative in tuple(expected):
        for parent in Path(relative).parents:
            key = parent.as_posix()
            if key != "." and key not in expected:
                expected[key] = {"kind": "directory", "mode": 0o700, "bytes": 0}
    return expected


def read_ledger(path):
    value = original.data(path)
    contract.require(set(value) == {"protocol", "descriptors"} and value["protocol"] == PROFILE
                     and isinstance(value["descriptors"], dict)
                     and set(value["descriptors"]).issubset(contract.STAGES),
                     "only_two_fixed_generated_descriptor_purposes")
    for stage, row in value["descriptors"].items():
        contract.require(set(row) == {"relative", "kind", "mode", "bytes", "sha256", "bindingSHA256"}
                         and row["relative"] == "derived/Build/Products/" + contract.COPY_NAMES[stage]
                         and row["kind"] == "file" and row["mode"] == 0o600
                         and type(row["bytes"]) is int and 0 < row["bytes"] <= 65536
                         and all(isinstance(row[k], str) and len(row[k]) == 64
                                 and all(c in "0123456789abcdef" for c in row[k])
                                 for k in ("sha256", "bindingSHA256")),
                         "generated_descriptor_ledger_schema_or_path_changed")
    return value


def verify_tree(work, manifest, ledger, *, pending=None):
    work = Path(work)
    contract.require(work.is_dir() and work.resolve() == work and not work.is_symlink()
                     and stat.S_IMODE(work.lstat().st_mode) == 0o700,
                     "canonical_private_restored_runner_root_required")
    expected = layout(manifest)
    additions = dict(ledger["descriptors"])
    if pending is not None:
        stage, row = pending
        contract.require(stage in contract.STAGES and stage not in additions, "descriptor_purpose_replay")
        additions[stage] = row
    for stage, row in additions.items():
        relative = "derived/Build/Products/" + contract.COPY_NAMES[stage]
        contract.require(row["relative"] == relative and relative not in expected,
                         "generated_descriptor_may_not_replace_original")
        expected[relative] = {k: row[k] for k in ("kind", "mode", "bytes", "sha256")}
    seen = {}
    for path in sorted(work.rglob("*")):
        relative = path.relative_to(work).as_posix()
        observed = path.lstat()
        contract.require(relative in expected and not path.is_symlink(), "unrecorded_runner_tree_member")
        wanted = expected[relative]
        kind = "directory" if stat.S_ISDIR(observed.st_mode) else "file" if stat.S_ISREG(observed.st_mode) else "forbidden"
        contract.require(kind == wanted["kind"] and stat.S_IMODE(observed.st_mode) == wanted["mode"],
                         "restored_runner_type_or_mode_changed")
        if kind == "file":
            contract.require(observed.st_nlink == 1 and observed.st_size == wanted["bytes"]
                             and owned.digest(path) == wanted["sha256"], "restored_runner_payload_changed")
        seen[relative] = wanted
    contract.require(set(seen) == set(expected), "restored_runner_member_missing")
    return {"originalEntries": 24, "originalProducts": 20, "originalGeneratedSources": 4,
            "structuralParents": len(layout(manifest)) - 24, "generatedDescriptors": len(additions),
            "entrySetSHA256": original.canonical(seen), "originalBytesModesTypesUnchanged": True}


def restore_tree(archive, work, manifest):
    contract.require(not work.exists(), "fresh_retained_runner_root_required")
    work.mkdir(mode=0o700)
    stage = work / ".original-extraction"
    original.restore_tar(archive, stage, manifest["entries"])
    (work / "derived").mkdir(mode=0o700)
    (stage / "Build").rename(work / "derived/Build")
    (stage / "Source").rename(work / "source")
    stage.rmdir()
    members = {("derived/" + x["name"] if x["name"].startswith("Build/") else
                "source/" + x["name"][len("Source/"):]) for x in manifest["entries"]}
    for relative, row in layout(manifest).items():
        if relative not in members:
            (work / relative).chmod(row["mode"])
    return verify_tree(work, manifest, {"protocol": PROFILE, "descriptors": {}})


def extract_originals(carrier, directory, archive, manifest):
    contract.require(carrier.stat().st_size == manifest["artifact"]["bytes"]
                     and owned.digest(carrier) == manifest["artifact"]["sha256"],
                     "original_runner_carrier_identity_changed")
    contract.require(not directory.exists() and not archive.exists(), "fresh_runner_originals_required")
    directory.mkdir(mode=0o700)
    with zipfile.ZipFile(carrier) as stream:
        entries = stream.infolist()
        contract.require(len(entries) == manifest["archiveEntryCount"]
                         and len({x.filename for x in entries}) == len(entries),
                         "original_runner_zip_member_set_changed")
        for entry in entries:
            original.safe_relative(entry.filename.rstrip("/"))
        requested = dict(manifest["metadata"])
        requested[manifest["runnerArchive"]["member"]] = manifest["runnerArchive"]
        for name, expected in requested.items():
            entry = stream.getinfo(name)
            contract.require(not entry.is_dir() and entry.file_size == expected["bytes"]
                             and entry.file_size <= 512 * 1024, "bounded_exact_runner_member_required")
            raw = stream.read(entry)
            contract.require(len(raw) == expected["bytes"] and contract.sha(raw) == expected["sha256"],
                             "original_runner_member_hash_changed")
            target = archive if name == manifest["runnerArchive"]["member"] else directory / name
            target.parent.mkdir(parents=True, exist_ok=True)
            write_bytes(target, raw)
    return original_metadata(directory, manifest)


def compose_descriptor(raw, *, products, application, stage, runtime):
    manifest = fixed()
    expected = manifest["originalDescriptor"]
    contract.require(len(raw) == expected["bytes"] and contract.sha(raw) == expected["sha256"],
                     "exact_original_ui_template_required")
    original_value = plistlib.loads(raw)
    target = original_value[contract.TARGET]
    contract.require(target.get("UseUITargetAppProvidedByTests") is True
                     and "UseDestinationArtifacts" not in target,
                     "exact_original_provided_by_tests_mode_required")
    info = plistlib.loads(contract.regular(application / "Info.plist", 256 * 1024))
    contract.require(application.name == "PinkhaAnyNative.app"
                     and info.get("CFBundleIdentifier") == contract.APP_BUNDLE,
                     "sealed_original_application_bundle_required")
    normalizer, bindings = preload()
    normalized = copy.deepcopy(original_value)
    change = normalizer.normalize_runtime_injection(
        normalized[contract.TARGET], runtime, expected_original_token=expected["mainThreadCheckerToken"])
    normalized_raw = plistlib.dumps(normalized, sort_keys=False)
    composed_raw, proof = contract.descriptor_bytes(
        normalized_raw, products=products, original_app=application, stage=stage)
    configured = plistlib.loads(composed_raw)
    configured[contract.TARGET].pop("UseUITargetAppProvidedByTests")
    configured[contract.TARGET]["DependentProductPaths"] = [
        str(application), *target["DependentProductPaths"]]
    inverse = copy.deepcopy(configured)
    for key in ("UITargetAppPath", "UITargetAppBundleIdentifier", "OnlyTestIdentifiers",
                "UseUITargetAppProvidedByTests", "DependentProductPaths"):
        if key in target:
            inverse[contract.TARGET][key] = target[key]
        else:
            inverse[contract.TARGET].pop(key, None)
    inverse[contract.TARGET]["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"] = (
        target["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"])
    contract.require(inverse == original_value, "unadmitted_retained_descriptor_delta")
    result = plistlib.dumps(configured, sort_keys=False)
    proof.update(originalSHA256=expected["sha256"], normalizedSHA256=contract.sha(normalized_raw),
                 originalRunnerSource=manifest["origin"], origin=PROFILE,
                 normalization=change, normalizationModuleBindings=bindings,
                 additionalChangedFields=["UseUITargetAppProvidedByTests", "DependentProductPaths"],
                 exactOriginalTemplateInverse=True, appProvidedByTests=False,
                 applicationDependency=str(application))
    return result, proof


def reference():
    preload()
    return RetainedRunner(_SEAL)


def require_reference(value):
    contract.require(type(value) is RetainedRunner and value._seal is _SEAL,
                     "sealed_original_runner_reference_required")
    original.control_module_binding(sys.modules[__name__], "Tools/AnyEnginePort/native_ui_runner_reuse.py")
    return value


class RetainedRunner:
    def __init__(self, seal):
        contract.require(seal is _SEAL, "runner_reference_not_admitted")
        self._seal = seal

    def record_fields(self):
        require_reference(self)
        return {"uiRunnerBuildInvocations": 0, "runnerExecutionOrigin": PROFILE,
                "originalRunnerOrigin": fixed()["origin"], "originalUIRunnerBuildInvocations": 1,
                "originalFailedUIRunRemainsFailure": True,
                "retainedRunnerAdmissionSHA256": owned.digest(ADMISSION)}

    def build_receipt_path(self):
        require_reference(self)
        return ORIGINALS / (PREFIX + "build.json")

    def verify(self, state):
        require_reference(self)
        manifest = fixed()
        record = original.data(ADMISSION)
        context = transition.context_record(state)
        contract.require(record["status"] == "ADMITTED_RETAINED_UI_RUNNER_NO_BUILD"
                         and record["profile"] == PROFILE and record["manifestSHA256"] == MANIFEST_SHA
                         and record["currentContext"] == context
                         and record["currentSources"] == current_inputs(state, manifest)
                         and record["originalRunnerOrigin"] == manifest["origin"]
                         and record["currentUIRunnerBuilds"] == record["currentAppBuilds"]
                         == record["currentNativeBuilds"] == record["methodsExecutedAtAdmission"] == 0,
                         "retained_runner_current_admission_changed")
        contract.require(context["applicationCommit"] == manifest["originalApp"]["commit"]
                         and context["originalArtifact"] == manifest["originalApp"]["artifact"]
                         and context["originalApplicationCodeCarriersSHA256"]
                         == manifest["originalApp"]["codeCarriersSHA256"], "original_app_runner_composition_changed")
        values = original_metadata(ORIGINALS, manifest)
        contract.require(ARCHIVE.stat().st_size == manifest["runnerArchive"]["bytes"]
                         and owned.digest(ARCHIVE) == manifest["runnerArchive"]["sha256"],
                         "retained_ui_archive_changed")
        ledger = read_ledger(LEDGER)
        verify_tree(transition.WORK, manifest, ledger)
        for stage, row in ledger["descriptors"].items():
            binding_path = transition.EVIDENCE / stage / "descriptor-binding.json"
            contract.require(owned.digest(binding_path) == row["bindingSHA256"],
                             "generated_descriptor_binding_changed")
            binding = original.data(binding_path)
            library = Path(binding["normalization"]["replacement_token"])
            contract.require(library.is_file() and library.stat().st_size == binding["normalization"]["library_bytes"]
                             and owned.digest(library) == binding["normalization"]["library_sha256"],
                             "current_runtime_injection_changed")
        descriptor = transition.PRODUCTS / manifest["originalDescriptor"]["name"]
        contract.require(owned.digest(descriptor) == manifest["originalDescriptor"]["sha256"],
                         "original_restored_descriptor_changed")
        return values[PREFIX + "build.json"], descriptor

    def descriptor_bytes(self, raw, state, stage):
        require_reference(self)
        runtime = original.data(state["locations"]["evidence"] / "native-ui-original-runtime.json")
        contract.require(runtime["ownedSimulatorUDID"] == state["admission"]["ownedSimulatorUDID"],
                         "retained_runner_runtime_owned_uuid_changed")
        return compose_descriptor(raw, products=transition.PRODUCTS,
                                  application=state["application"], stage=stage, runtime=runtime["runtime"])

    def register_descriptor(self, stage, path, binding_path, state):
        require_reference(self)
        contract.require(stage in contract.STAGES and path == transition.PRODUCTS / contract.COPY_NAMES[stage]
                         and binding_path == transition.EVIDENCE / stage / "descriptor-binding.json",
                         "exact_generated_descriptor_destination_required")
        manifest = fixed()
        ledger = read_ledger(LEDGER)
        contract.require(stage not in ledger["descriptors"], "generated_descriptor_purpose_already_used")
        raw = contract.regular(path, 65536)
        expected, proof = self.descriptor_bytes(
            contract.regular(transition.PRODUCTS / manifest["originalDescriptor"]["name"]), state, stage)
        proof.update(copiedSHA256=contract.sha(expected), copiedPath=str(path))
        contract.require(raw == expected and original.data(binding_path) == proof,
                         "generated_descriptor_not_exact_approved_composition")
        row = {"relative": path.relative_to(transition.WORK).as_posix(), "kind": "file", "mode": 0o600,
               "bytes": len(raw), "sha256": contract.sha(raw), "bindingSHA256": owned.digest(binding_path)}
        verify_tree(transition.WORK, manifest, ledger, pending=(stage, row))
        write_bytes(REUSE / ("ledger-before-" + stage + ".json"), contract.regular(LEDGER))
        updated = {"protocol": PROFILE, "descriptors": {**ledger["descriptors"], stage: row}}
        pending = REUSE / ("ledger-after-" + stage + ".json")
        write_json(pending, updated)
        os.replace(pending, LEDGER)
        fd = os.open(REUSE, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        self.verify(state)


def restore():
    preload()
    manifest = fixed()
    state = transition.setup()
    transition.verify_device(state)
    contract.require(state["context"]["currentRunID"] != manifest["origin"]["runID"]
                     and state["context"]["controlCommit"] != manifest["origin"]["sourceCommit"],
                     "separate_current_restoration_run_required")
    contract.require(not transition.WORK.exists() and not transition.EVIDENCE.exists(),
                     "fresh_retained_runner_admission_required")
    transition.EVIDENCE.mkdir(mode=0o700)
    REUSE.mkdir(mode=0o700)
    inputs = current_inputs(state, manifest)
    sources = transition.source_snapshot(state)
    write_json(REUSE / "current-source-before.json", sources)
    commands = REUSE / "commands"
    origin = manifest["origin"]
    endpoint = "repos/" + manifest["repository"] + "/actions/"
    api = {}
    for name, tail in (
        ("run", "runs/" + origin["runID"] + "/attempts/" + str(origin["runAttempt"])),
        ("artifact", "artifacts/" + manifest["artifact"]["id"]),
        ("jobs", "runs/" + origin["runID"] + "/attempts/" + str(origin["runAttempt"]) + "/jobs?per_page=100"),
    ):
        raw = original.public_command(["gh", "api", endpoint + tail], commands, "original-" + name, 60)
        api[name] = original.strict_json(raw)
    api_proof = validate_api(api["run"], api["artifact"], api["jobs"], manifest)
    downloads = Path(os.environ["RUNNER_TEMP"]) / (
        "retained-ui-runner-" + state["context"]["currentRunID"] + "-" + str(state["context"]["currentRunAttempt"]))
    contract.require(not downloads.exists(), "fresh_original_runner_download_required")
    original.public_command(["gh", "api", endpoint + "artifacts/" + manifest["artifact"]["id"] + "/zip"],
                            downloads, "original-runner", 180)
    carrier = downloads / "original-runner.stdout"
    extract_originals(carrier, ORIGINALS, ARCHIVE, manifest)
    restored = restore_tree(ARCHIVE, transition.WORK, manifest)
    write_json(LEDGER, {"protocol": PROFILE, "descriptors": {}})
    host = transition.PRODUCTS / ("Debug-iphonesimulator/" + contract.TARGET + "-Runner.app")
    signature, _ = owned.run_owned(["codesign", "--verify", "--deep", "--strict", str(host)],
                                   REUSE / "runner-signature.log", 30)
    carriers = []
    for relative in (contract.TARGET + "-Runner", "PlugIns/" + contract.TARGET + ".xctest/" + contract.TARGET):
        path = host / relative
        observed, log = owned.run_owned(["lipo", "-archs", str(path)],
                                        REUSE / ("runner-carrier-" + str(len(carriers)) + ".log"), 30)
        architectures = contract.regular(log).decode().split()
        contract.require(architectures == ["arm64"], "retained_ui_carrier_architecture_changed")
        carriers.append({"path": path.relative_to(transition.PRODUCTS).as_posix(),
                         "sha256": owned.digest(path), "architectures": architectures, "command": observed})
    after = transition.recheck_sources(state, sources)
    contract.require(current_inputs(state, manifest) == inputs, "retained_runner_control_changed_during_restore")
    transition.ui.current()
    write_json(REUSE / "current-source-after.json", after)
    record = {"schemaVersion": 1, "status": "ADMITTED_RETAINED_UI_RUNNER_NO_BUILD", "profile": PROFILE,
              "manifestSHA256": MANIFEST_SHA, "currentContext": transition.context_record(state),
              "currentSources": inputs, "originalRunnerOrigin": origin, "originalAPI": api_proof,
              "originalCarrier": manifest["artifact"], "runnerArchive": manifest["runnerArchive"],
              "restoredTree": restored, "signature": signature, "executableCarriers": carriers,
              "currentUIRunnerBuilds": 0, "currentAppBuilds": 0, "currentNativeBuilds": 0,
              "methodsExecutedAtAdmission": 0, "originalBuildInvocations": 1,
              "originalFailedRunRemainsFailure": True, "originalFiveFailuresRetried": False,
              "sourceBeforeSHA256": owned.digest(REUSE / "current-source-before.json"),
              "sourceAfterSHA256": owned.digest(REUSE / "current-source-after.json"),
              "fullAcceptance": False, "currentSharedAppAcceptance": False}
    write_json(ADMISSION, record)
    reference().verify(state)
    return record
