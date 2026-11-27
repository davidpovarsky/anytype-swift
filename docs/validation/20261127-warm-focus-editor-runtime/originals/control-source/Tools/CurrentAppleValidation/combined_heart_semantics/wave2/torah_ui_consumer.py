"""Additive UI hooks for the admitted shared F consumer; never builds a product.

The original stage/descriptor/enumeration/results/Set postflight and owned-lane
lifecycle remain in the original consumer. These hooks supply only prerequisites
that the six Torah lanes and original editor require.
"""
from datetime import datetime, timezone
from pathlib import Path
import re
import uuid

import torah_ui_profile as profile

UI_LANES = frozenset(profile.STARTUP_LANES)
ORIGINAL_HELPERS = {
    "run_wave15_acceptance": "f99b1c04efeee2be45459b49d8c71fd8207039c97be4578cd6f2dfc8d29bb283",
    "run_ui27": "87e0972ee6852d1fdb34d82afa5dde346baf836afaa8419203b647e7d3e21ca7",
}
require = profile.require


def before_ui(consumer, lane):
    require(lane in UI_LANES, "Unreviewed UI startup lane")
    for name, expected in ORIGINAL_HELPERS.items():
        require(profile.sha(Path(consumer.helpers[name].__file__).read_bytes()) == expected,
                "Original UI prerequisite validator changed: " + name)
    original = consumer.helpers["run_wave15_acceptance"]
    profile.inspect_original_lanes(original)
    require(consumer.admission["appLanguage"] == "en" or lane == "editor",
            "Original non-editor UI lanes require a dedicated English admission")
    return profile.reviewed_ui_sources(consumer.source, source_commit=consumer.binding["sourceSHA"])


def _canonical_environment(consumer, lane, directory, preparation, preparation_path, fixture):
    """Retain the real original stage console as input to the unchanged parser."""
    original = consumer.helpers["run_wave15_acceptance"]
    shared = consumer.shared_module
    invocation_raw = shared.raw(preparation_path / "invocation.json")
    invocation = shared.decode(invocation_raw)
    command = preparation["command"]
    require(command.get("status") == "PASS_COMMAND" and command.get("exitCode") == 0
            and command.get("argv") == invocation.get("argv"), "Original preparation console command differs")
    label = directory.name + "-preparation-test"
    original_directory = consumer.commands.root / label
    command_raw = shared.raw(original_directory / "result.json")
    require(shared.decode(command_raw) == command, "Preparation result is not this actual recorded command")
    console_path = original_directory / "original.log"
    console_raw = shared.raw(console_path)
    parser_directory = preparation_path / "canonical-original-console"
    require(not parser_directory.exists(), "Original canonical parser evidence must be new")
    parser_directory.mkdir(mode=0o700)
    parser_path = parser_directory / "command-original-preparation.log"
    shared.write_bytes(parser_path, console_raw)
    require(shared.digest(parser_path) == shared.digest(console_path), "Canonical console copy changed")
    environment = original.property_environment(parser_directory, fixture["spaceId"])
    shared.write(parser_directory / "provenance.json", {
        "originalConsole": str(console_path), "originalConsoleSHA256": shared.sha(console_raw),
        "retainedParserConsole": str(parser_path), "preparationCommandSHA256": shared.sha(command_raw),
        "preparationInvocationSHA256": shared.sha(invocation_raw),
        "parser": "run_wave15_acceptance.property_environment unchanged",
        "writingIDsProvenByStage1FixtureAlone": False,
    })
    return environment, console_raw


def _combined_runtime_source(consumer):
    """Read the already-admitted unified identity; never relabel a legacy Heart."""
    shared = consumer.shared_module
    source = consumer.source_admission
    require(source.get("commit") == consumer.binding["sourceSHA"], "Shared source admission differs")
    runtime = source.get("runtimeIdentity", {})
    identity = runtime.get("identity", {})
    require(identity.get("protocol") == "pinkha-unified-runtime-full-identity-v1"
            and identity.get("sourceManifestSHA256") == shared.MANIFEST
            and identity.get("heartVersion") == shared.VERSION
            and runtime.get("nativeRuntimeExecutedByThisCheck") is False
            and re.fullmatch(r"[0-9a-f]{64}", runtime.get("producerRuntimeProofSHA256", "")),
            "Actual common producer must have admitted the exact combined runtime")
    lock = shared.decode(shared.raw(consumer.source / "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"))
    pins = [row for row in lock["pins"] if row.get("identity") == "torahinspectorkit"]
    require(len(pins) == 1 and re.fullmatch(r"[0-9a-f]{40}", pins[0].get("state", {}).get("revision", "")),
            "Exact admitted Inspector package revision required")
    require(re.fullmatch(r"[0-9a-f]{64}", source.get("sourceStateSHA256", "")), "Complete source inventory proof missing")
    return {
        "source_sha": consumer.binding["sourceSHA"], "run_id": consumer.binding["runID"],
        "run_attempt": consumer.binding["runAttempt"], "kit_sha": pins[0]["state"]["revision"],
        "candidate_inputs_sha256": source["sourceStateSHA256"],
        "runtime_profile": "dual-engine-runtime-v1", "native_marker": identity["heartVersion"],
        "native_manifest_sha256": identity["sourceManifestSHA256"],
        "producer_runtime_proof_sha256": runtime["producerRuntimeProofSHA256"],
        "candidateInputsIdentityKind": "common admitted complete producer source state",
    }


def _prelaunch_inspector(consumer, lane, directory, udid):
    """Keep original process/code predicates with the admitted unified identity.

    Original heart_runtime_profile only understands legacy r14/r15, so it cannot
    truthfully admit combined8ac. No legacy marker constant or validator is
    patched. Common product admission above supplies the new runtime identity;
    actual process reading/mapped-code/continuity validators remain original.
    """
    shared, original = consumer.shared_module, consumer.helpers["run_ui27"]
    evidence = directory / "inspector-prelaunch"
    evidence.mkdir(mode=0o700)
    source_identity = _combined_runtime_source(consumer)
    # Use original installed-byte verification with bounded command calls.
    source = original.installed_runtime_source(udid, evidence, consumer.app, source_identity, command_timeout=lambda: 30)
    installed = Path(source["installed_app"])
    owner = Path.home() / "Library/Developer/CoreSimulator/Devices" / udid
    require(installed.resolve() == installed and installed.is_relative_to(owner), "Prelaunch installed App is outside owned simulator")
    launched_at = datetime.now(timezone.utc).isoformat()
    log, _ = consumer.command([
        "/usr/bin/env", "SIMCTL_CHILD_PINKHA_UI27_ROUTE_OBSERVATION=1", "SIMCTL_CHILD_PINKHA_UI27_STARTUP_OBSERVATION=1",
        "xcrun", "simctl", "launch", "--terminate-running-process", udid, shared.BUNDLE,
        "-AppleLanguages", "(en)", "-AppleLocale", "en_US",
    ], lane + "-inspector-prelaunch", 60)
    text = shared.raw(log, 4096).decode("utf-8").strip()
    match = re.fullmatch(re.escape(shared.BUNDLE) + r":\s*([1-9][0-9]*)", text)
    require(match is not None, "Original simctl launch did not return one exact App PID")
    pid = int(match.group(1))
    process_before = original.read_process_identity(pid, installed / "Anytype", command_timeout=lambda: 30)
    mapping_path, mapping = consumer.command(["/usr/bin/vmmap", "-w", str(pid)], lane + "-inspector-vmmap", 30)
    mapping_raw = shared.raw(mapping_path)
    shared.write_bytes(evidence / "live-runtime-vmmap.log", mapping_raw)
    mapping_text = mapping_raw.decode("utf-8", errors="replace")
    runtime_path = installed / "Frameworks/ProtobufMessages.framework/ProtobufMessages"
    process_after = original.read_process_identity(pid, installed / "Anytype", command_timeout=lambda: 30)
    loaded = (mapping["exitCode"] == 0 and str(runtime_path) in mapping_text
              and re.search(r"\[\s*" + str(pid) + r"\s*\]", mapping_text) is not None)
    marker_present = original.contains(runtime_path, source_identity["native_marker"].encode())
    record = dict(pid=pid, installed_app=str(installed), runtime_path=str(runtime_path),
                  runtime_sha256=original.digest(runtime_path), marker_present=marker_present,
                  runtime_loaded=loaded, vmmap_exit_code=mapping["exitCode"], process_start_identity=process_before,
                  process_identity_unchanged=process_before == process_after,
                  runtime_verified_at=datetime.now(timezone.utc).isoformat(), launch_started_at=launched_at,
                  requested_app_language="en", route_observation_requested=True, every_launch_verified=False,
                  nativeVersionExecutedByThisObservation=False)
    shared.write(evidence / "observed-runtime-before-qualification.json", record)
    require(marker_present and record["runtime_sha256"] == original.digest(consumer.app / "Frameworks/ProtobufMessages.framework/ProtobufMessages"),
            "Installed runtime marker/bytes differ from the admitted original product")
    require(loaded and process_before == process_after, "Original live App process/runtime mapping differs")
    require(original.digest(installed / "Anytype") == source["built_app_executable_sha256"], "Installed App changed during prelaunch mapping")
    record["mapped_app_code"] = original.mapped_app_code(installed, source["installed_code_carriers"], mapping_text)
    record.update({key: value for key, value in source.items() if key != "status"})
    shared.write(evidence / "live-runtime.json", record)
    return record


def prepare_ui(consumer, lane, directory, udid, preparation, preparation_path, fixture_raw, environment):
    shared = consumer.shared_module
    fixture = shared.decode(fixture_raw)
    environment, console, live = dict(environment), None, None
    if lane == "canonical-properties":
        additions, console = _canonical_environment(consumer, lane, directory, preparation, preparation_path, fixture)
        environment.update(additions)
    if lane in {"inspector", "inspector-search"}:
        live = _prelaunch_inspector(consumer, lane, directory, udid)
        environment["PINKHA_UI27_EXPECTED_APP_PID"] = str(live["pid"])
    require(shared.decode(shared.raw(preparation_path / "result.json")) == preparation,
            "Original successful preparation changed before startup binding")
    result = profile.startup_environment(
        lane=lane, fixture_raw=fixture_raw, ui_environment=environment,
        preparation_raw=shared.raw(preparation_path / "result.json"),
        invocation_raw=shared.raw(preparation_path / "invocation.json"),
        admission_raw=shared.raw(consumer.root / "evidence/admission.json"),
        owned_simulator_raw=shared.raw(directory / "owned-simulator.json"),
        binding=consumer.binding, udid=udid, token=uuid.uuid4().hex,
        code_carriers_sha256=consumer.carriers["sha256"], canonical_console_raw=console,
    )
    envelope = shared.decode(result[profile.PREFIX + "BINDING_JSON"])
    shared.write(directory / "startup-controller-binding.json", envelope)
    return result, {"live": live, "envelope": envelope}


def _continuity(consumer, lane, ui_path, live, methods):
    """Original continuity validator over byte-identical exported AX originals."""
    shared, original = consumer.shared_module, consumer.helpers["run_ui27"]
    actual = ui_path / "private-attachments"
    manifest_raw = shared.raw(actual / "manifest.json")
    manifest = shared.decode(manifest_raw)
    require(isinstance(manifest, list), "Original UI attachment manifest is missing")
    root = ui_path / "original-process-continuity"
    copies = root / "original-attachments"
    require(not root.exists(), "Continuity compatibility evidence must be new")
    copies.mkdir(parents=True, mode=0o700)
    shared.write_bytes(copies / "manifest.json", manifest_raw)
    names = {row.get("exportedFileName") for case in manifest for row in case.get("attachments", [])
             if isinstance(row.get("exportedFileName"), str) and row["exportedFileName"].endswith(".txt")}
    require(len(names) <= 200, "Bounded actual text-attachment inventory required")
    retained = {}
    for name in sorted(names):
        require(Path(name).name == name, "Original attachment filename escaped its directory")
        path = actual / name
        require(path.resolve().parent == actual.resolve() and not path.is_symlink(), "Original AX attachment is aliased")
        value = shared.raw(path, 8 * 1024**2)
        shared.write_bytes(copies / name, value)
        require(shared.digest(path) == shared.digest(copies / name), "Original AX bytes changed in continuity view")
        retained[name] = {"originalPath": str(path), "sha256": shared.sha(value)}
    shared.write(root / "original-attachment-provenance.json", {
        "originalManifest": str(actual / "manifest.json"), "manifestSHA256": shared.sha(manifest_raw),
        "byteIdenticalTextCopies": retained, "originalScreenshotsRetainedAt": str(actual),
        "compatibilityViewIsNotACompleteArtifact": True,
    })
    return original.verify_ui_process_continuity(root, "original", live, methods, command_timeout=lambda: 30)


def after_ui(consumer, lane, ui_path, context, methods, before):
    after = before_ui(consumer, lane)
    require(after == before, "Reviewed UI source changed during execution")
    envelope = context["envelope"]
    result = {"provenance": envelope["provenance"], "fixtureSHA256": envelope["fixtureSHA256"],
              "canonicalPreparationConsoleSHA256": envelope["canonicalPreparationConsoleSHA256"],
              "sourceBeforeAfter": before, "fullMatrixAccepted": False, "visualReview": "PENDING"}
    if lane in {"inspector", "inspector-search"}:
        result["originalProcessContinuity"] = _continuity(consumer, lane, ui_path, context["live"], methods)
    return result
