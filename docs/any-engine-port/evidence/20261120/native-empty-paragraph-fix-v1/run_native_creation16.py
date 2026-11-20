#!/usr/bin/env python3
"""Run the original creation14 plus two sparse-empty checks with the narrow fixed Host on exact native v9."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
from urllib.parse import urlsplit

CHECKS = {
    "property": {
        "native_custom_type_catalog_uses_canonical_definition_proof",
        "synthetic_page_and_canonical_body_created_through_guarded_routes",
        "type_switch_preserves_existing_body_and_exact_native_block_identity",
        "type_undo_and_reapply_are_native_version_conditional",
        "explicit_native_policy_allows_new_block_on_current_custom_document",
        "non_document_type_refused_before_dispatch",
        "collection_attach_and_typed_property_writes_have_verified_readback",
        "detach_and_reattach_preserve_orphan_namespace_values",
        "hide_attaches_verified_preferences_without_deleting_business_values",
        "show_preserves_unknown_future_visibility_keys",
        "derived_source_visibility_stays_in_presentation_namespace",
        "verified_property_undo_preserves_unedited_sibling_fields",
        "stale_full_version_edit_refused_without_unconditional_fallback",
        "complete_property_workflow_preserves_canonical_body_children_and_unknown_style",
        "only_allocated_synthetic_page_removed",
    },
    "creation": {
        "exact_current_writer_creation_capabilities",
        "production_guarded_object_create_verified_original_scope",
        "object_retry_new_creator_same_metadata_has_one_native_id",
        "changed_object_intent_refused_before_native_create",
        "production_guarded_block_create_preserves_text_and_unknown_style",
        "block_retry_new_creator_same_metadata_has_no_native_change",
        "changed_block_intent_refused_before_native_create",
        "guarded_child_creation_preserves_native_parent_identity",
        "verified_retry_preserves_later_editor_change_and_children",
        "revocation_before_dispatch_neither_reserves_nor_creates",
        "confirmation_failure_retains_known_object_id_without_redispatch",
        "fixture_journal_contains_identity_and_receipt_metadata_only",
        "closed_original_session_refuses_new_creation_work",
        "only_allocated_synthetic_objects_removed",
        "empty_paragraph_native_sparse_text_is_verified",
        "empty_paragraph_exact_retry_preserves_id_and_native_history",
    },
    "archive": {
        "actual_native_history",
        "empty_destination_precondition",
        "complete_object_archive_scope",
        "canonical_export_roundtrip",
        "raw_payload_bytes_preserved",
        "export_does_not_rewrite_source",
        "unmapped_block_refusal",
        "failed_plan_does_not_write",
        "source_bytes_and_audit_digest",
        "explicit_identity_map",
        "native_import_confirmed",
        "native_retry_is_idempotent",
        "only_live_associations_imported",
        "metadata_and_revision_preserved",
        "original_native_claims_untouched",
        "owned_disposable_objects_cleaned",
    },
}

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=CHECKS, required=True)
    for name in ("repo-root", "fixture", "native-binary", "native-manifest", "executable", "build-receipt", "output-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expected-native-sha256", required=True)
    parser.add_argument("--expected-native-manifest-sha256", required=True)
    parser.add_argument("--allow-disposable-writes", action="store_true")
    args = parser.parse_args()
    if not args.allow_disposable_writes:
        parser.error("explicit disposable scope required")
    for value in (args.expected_native_sha256, args.expected_native_manifest_sha256):
        if not re.fullmatch("[0-9a-f]{64}", value):
            parser.error("exact SHA256 pins required")
    root, out = args.repo_root.resolve(), args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    helper_path = root / "Tools/AnyEnginePort/run_live_provider_probe.py"
    metadata_path = root / "Tools/AnyEngineValidation/run_guarded_hierarchy_v8_probe.py"
    helper = load_module("workflow_owned_process", helper_path)
    metadata = load_module("workflow_loopback_metadata", metadata_path)
    result = {"status": "FAIL", "scope": "actual_native_v9_sparse_empty_" + args.mode + str(len(CHECKS[args.mode])),
              "startedAt": datetime.now(timezone.utc).isoformat(),
              "expectedChecks": sorted(CHECKS[args.mode]), "originalFourteenCreationAssertionsUnchanged": True, "narrowSparseEmptyReadbackFix": True,
              "productionTransportChanged": False, "protectedApplePersistenceCertified": False}
    before = None
    binary, native_manifest, executable = args.native_binary.resolve(), args.native_manifest.resolve(), args.executable.resolve()

    def snapshot():
        value = helper.source_snapshot(root, Path(__file__))
        if args.mode in ("property", "creation"):
            host = root / "Modules/PinkhaAnyHost"
            paths = [host / "Package.swift", host / "Package.resolved"] + list((host / "Sources").rglob("*.swift"))
            for path in paths:
                if path.is_file():
                    value["files"][path.relative_to(root).as_posix()] = {"sha256": helper.sha256(path), "bytes": path.stat().st_size}
        for path in (helper_path, metadata_path):
            value["files"][path.relative_to(root).as_posix()] = {"sha256": helper.sha256(path), "bytes": path.stat().st_size}
        return value

    try:
        result["stage"] = "pinned_preflight"
        fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
        endpoint = fixture["endpoint"]
        parsed = urlsplit(endpoint)
        if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or not parsed.port or parsed.path or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise RuntimeError("owned_literal_loopback_required")
        if helper.sha256(binary) != args.expected_native_sha256 or helper.sha256(native_manifest) != args.expected_native_manifest_sha256:
            raise RuntimeError("explicit_native_pins_mismatch")
        if fixture["binarySHA256"] != args.expected_native_sha256 or fixture["nativeSourceManifestSHA256"] != args.expected_native_manifest_sha256:
            raise RuntimeError("fixture_native_pins_mismatch")
        result.update(nativeBinarySHA256=args.expected_native_sha256,
                      nativeSourceManifestSHA256=args.expected_native_manifest_sha256,
                      fixtureSHA256=helper.sha256(args.fixture), probeSHA256=helper.sha256(executable),
                      endpoint=endpoint, accountID=fixture["accountId"],
                      originalFixtureSpaceUnused=fixture["spaceId"])
        result["nativeProcessBefore"] = metadata.native_process_identity(fixture["pid"], parsed.port, binary)
        proof = json.loads(args.build_receipt.read_text(encoding="utf-8"))
        if proof.get("status") != "PASS_EXACT_SOURCE_COMPONENT_BUILD" or proof.get("sourceStable") is not True or proof.get("retainedInputsStable") is not True or proof.get("binarySHA256") != result["probeSHA256"]:
            raise RuntimeError("current_source_build_receipt_mismatch")
        for relative, digest in proof["sourceInputs"].items():
            if helper.sha256(root / relative) != digest:
                raise RuntimeError("compiled_source_input_changed:" + relative)
        result["buildReceiptSHA256"] = helper.sha256(args.build_receipt)
        result["buildScope"] = proof["scope"]
        shutil.copyfile(args.build_receipt, out / "component-build-receipt.json")
        for source, name in ((Path(__file__), "executed-runner.py"), (helper_path, "executed-process-helper.py"),
                             (metadata_path, "executed-loopback-metadata-helper.py"),
                             (args.fixture, "verified-fixture.json"), (native_manifest, "native-source-manifest.json")):
            shutil.copyfile(source, out / name)
        selected = {"property": "Modules/PinkhaAnyHost/Sources/PinkhaAnyHostProbe/PropertyProbe.swift",
                    "creation": "Modules/PinkhaAnyHost/Sources/PinkhaAnyHostProbe/CreationProbe.swift",
                    "archive": "Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegrationProbe/NativeArchiveProbe.swift"}[args.mode]
        shutil.copyfile(root / selected, out / "executed-production-probe.swift")
        result["productionProbeSourceSHA256"] = helper.sha256(root / selected)
        before = snapshot()
        helper.write_json(out / "source-before.json", before)
        swift_root = Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift")
        runtime_dirs = [swift_root / "Toolchains/6.3.3+Asserts/usr/bin", swift_root / "Runtimes/6.3.3/usr/bin"]
        if not all(path.is_dir() for path in runtime_dirs):
            raise RuntimeError("pinned_swift_runtime_directories_missing")
        os.environ["PATH"] = os.pathsep.join(str(path) for path in runtime_dirs) + os.pathsep + os.environ.get("PATH", "")
        result["explicitSwiftRuntimePATHPrefixes"] = [str(path) for path in runtime_dirs]
        health = metadata.http(endpoint, "GET", "/v1/health")
        if health.get("account") != fixture["accountId"] or not health.get("startedAt"):
            raise RuntimeError("owned_fixture_account_or_run_mismatch")
        result["engineStartedAt"] = health["startedAt"]
        caps = metadata.http(endpoint, "GET", "/v1/pinkha/capabilities")
        required = ["conditionalPropertiesSet", "conditionalPropertiesApplySeq", "conditionalPropertiesNoop",
                    "conditionalMembershipSet", "nativeDocumentMembership", "currentWriterObjectCreate", "currentWriterBlockCreate"]
        if caps.get("contract") != "pinkha-torah-native-v1" or any(type(caps.get(name)) is not int or caps[name] != 1 for name in required):
            raise RuntimeError("required_exact_v8_contract_missing")
        result["requiredNativeCapabilities"] = {name: caps[name] for name in required}
        result["stage"] = "fresh_disposable_space"
        import uuid
        nonce = uuid.uuid4().hex
        created = metadata.http(endpoint, "POST", "/v1/spaces", {"name": "Pinkha v9 sparse-empty " + args.mode + " " + nonce})
        space = created.get("id")
        if not isinstance(space, str) or not space or space == fixture["spaceId"]:
            raise RuntimeError("new_owned_space_identity_missing")
        result["spaceID"] = space
        helper.write_json(out / "allocated-space.json", {"endpoint": endpoint, "accountID": fixture["accountId"],
                          "spaceID": space, "originalFixtureSpaceUnused": fixture["spaceId"]})
        base = "/v1/spaces/" + space
        if args.mode == "property":
            result["stage"] = "fresh_property_schema"
            typed = metadata.http(endpoint, "POST", base + "/types", {"name": "V8 property canonical document", "xKey": "v8_prop_type_" + nonce})
            type_id = typed["typeId"]
            metadata.http(endpoint, "POST", base + "/types/" + type_id + "/parts",
                          {"key": "body", "datasets": [{"module": "editor"}]})
            policy = metadata.http(endpoint, "GET", base + "/pinkha/document-types/" + type_id)
            if policy.get("eligible") is not True or policy.get("canonicalEditorDataset") != "editor_blocks":
                raise RuntimeError("fresh_custom_type_not_native_canonical_document")
            owner = metadata.http(endpoint, "POST", base + "/collections",
                                  {"name": "V8 property preserved values", "xKey": "v8_prop_values_" + nonce})["collectionId"]
            text_id = metadata.http(endpoint, "POST", base + "/collections/" + owner + "/properties",
                                    {"name": "Text value", "xKey": "text_value", "kind": "string", "scope": "synced"})["propId"]
            number_id = metadata.http(endpoint, "POST", base + "/collections/" + owner + "/properties",
                                      {"name": "Number value", "xKey": "number_value", "kind": "number", "scope": "synced"})["propId"]
            result["propertySchema"] = {"typeID": type_id, "collectionID": owner, "textPropertyID": text_id, "numberPropertyID": number_id}
            command = [str(executable), endpoint, space, fixture["accountId"], "--properties", "--allow-disposable-writes",
                       "--custom-type-id", type_id, "--collection-id", owner, "--text-property-id", text_id, "--number-property-id", number_id]
        elif args.mode == "creation":
            command = [str(executable), endpoint, space, fixture["accountId"], "--creation-retry", "--allow-disposable-writes"]
        else:
            command = [str(executable), "--archive", "--disposable", endpoint, fixture["accountId"], space]
        result["stage"] = "production_creation14_plus_sparse_empty2"
        run = out / "run"
        run.mkdir()
        result["process"] = helper.run_process(command, root, run, 360)
        report = None
        try:
            raw = (run / "stdout.json").read_bytes()
            if len(raw) <= 1024 * 1024:
                candidate = json.loads(raw)
                if isinstance(candidate, dict):
                    report = candidate
                    result["report"] = report
        except (ValueError, UnicodeError):
            result["reportParseFailed"] = True
        if result["process"].get("exitCode") != 0 or result["process"].get("timedOut") or result["process"].get("cleanupErrors") or result["process"].get("runnerErrorType"):
            raise RuntimeError("actual_production_workflow_failed")
        if report is None or report.get("status") != "PASS" or type(report.get("count")) is not int or report["count"] != len(CHECKS[args.mode]):
            raise RuntimeError("original_workflow_count_or_status_failed")
        checks = report.get("checks")
        if args.mode == "archive":
            complete = isinstance(checks, dict) and set(checks) == CHECKS[args.mode] and all(v is True for v in checks.values())
        else:
            complete = isinstance(checks, list) and len(checks) == len(CHECKS[args.mode]) and set(checks) == CHECKS[args.mode]
        if not complete:
            raise RuntimeError("original_meaningful_checks_not_complete")
        result["executedChecks"] = len(CHECKS[args.mode])
        result["probeScopeLabelRetainedExactly"] = report.get("scope")
        result["stage"] = "native_and_source_readback"
        after_health = metadata.http(endpoint, "GET", "/v1/health")
        if after_health.get("account") != health.get("account") or after_health.get("startedAt") != health.get("startedAt"):
            raise RuntimeError("native_run_changed")
        result["nativeProcessAfter"] = metadata.native_process_identity(fixture["pid"], parsed.port, binary)
        if helper.sha256(executable) != result["probeSHA256"]:
            raise RuntimeError("probe_binary_changed")
        result["status"] = "PASS"
    except Exception as error:
        result["errorType"] = type(error).__name__
        if type(error) is RuntimeError:
            result["errorCode"] = str(error)
    finally:
        if before is not None:
            try:
                after = snapshot()
                helper.write_json(out / "source-after.json", after)
                result["sourceStable"] = before["files"] == after["files"] and before["dependencies"] == after["dependencies"]
                result["nativeBinaryStable"] = helper.sha256(binary) == args.expected_native_sha256 and helper.sha256(native_manifest) == args.expected_native_manifest_sha256
                if not result["sourceStable"] or not result["nativeBinaryStable"]:
                    result["status"] = "FAIL"
            except Exception as error:
                result["status"] = "FAIL"
                result["sourceVerificationErrorType"] = type(error).__name__
        result["finishedAt"] = datetime.now(timezone.utc).isoformat()
        helper.write_json(out / "result.json", result)
    print(json.dumps({key: result.get(key) for key in ["status", "scope", "stage", "executedChecks", "sourceStable", "nativeBinaryStable", "errorCode"]}), flush=True)
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
