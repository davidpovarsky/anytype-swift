"""Exact Page154 source and retained native evidence for a distinct Apple build."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HEART = "d98420b1113536afd08cde6de9a5816f6d27ffff"
MANIFEST_PATH = "Tools/PinkhaSemanticAnchorWire/page-source.json"
MANIFEST_SHA = "2f76212f9fcd749aeb9e806b941e0fd0b54eba17e5cc842adb81c7eb3bae0f38"
VERSION = "pinkha-semantic-anchor-native-page-candidate-v1-" + MANIFEST_SHA
VARIANT = "semantic-anchor-native-page154-v1"
ARTIFACT = "Pinkha-Semantic-Page-Production-Simulator-v1"
PROOF = "docs/validation/20261123-semantic-page-native/attempt6-page-pass"
NATIVE_SOURCE = "43babda573466d9c0f85a98ee4b2d6cb70fdb17a"
ACCEPTANCE_SHA = "821cf39bab3ab2b553a648a847000598400435067e1550155e1c2804143a7900"
BUILD_SHA = "fa8dee5f53df02b92d61a357fe3994befe238edf63949ae78d7395e19d2ba7a8"
AUDIT_SHA = "4ca0e31c9c7abfab17581adffea50602bbf851c2e81a820e9c10685a47d15e46"
NATIVE_BINARY_SHA = "ad6872c62bfed92a087d8d6e35b0284306b547ace48ea0b0c186c595d4725d02"
SERVICE = "clientlibrary/service/pinkha_semantic_anchor.go"
SERVICE_SHA = "da234f17b6e1811fc637d1c5ce5523fbf15bbc24d80465dafe8993e347082f80"
ENTRY = "ServicePinkhaSemanticAnchorCapture"
PACKAGE = "github.com/anyproto/anytype-heart/clientlibrary/service"
PHASES = (("capture", "TestSemanticAnchorNativePageCaptureAndWire"),
          ("cold-reopen", "TestSemanticAnchorNativePageColdReopen"))
ORIGINS = {"qualified139": 139, "current_repaired9": 9, "wire3": 3,
           "page3": 2, "page4_fixture_explicit_empty_restrictions": 1}
PASS = "BUILT_PAGE154_APPLE_FRAMEWORK_NOT_EXECUTED"


def require(value, message):
    if not value:
        raise ValueError(message)


def relative(value):
    require(isinstance(value, str) and value and "\\" not in value
            and not PurePosixPath(value).is_absolute()
            and all(item not in {"", ".", ".."} for item in value.split("/")), "Unsafe relative evidence/source path")
    return Path(*PurePosixPath(value).parts)


def digest(path):
    require(path.is_file() and not path.is_symlink(), "Expected regular nonsymlink source/evidence")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf8")
    temporary.replace(path)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True, timeout=30).strip()


def file_hashes(root, expected):
    actual = {name: digest(root / relative(name)) for name in expected}
    require(actual == expected, "Exact source bytes changed")
    return actual


def candidate(control):
    path = control / MANIFEST_PATH
    require(digest(path) == MANIFEST_SHA, "Page154 manifest changed")
    value = json.loads(path.read_bytes())
    require(value.get("schemaVersion") == 1 and value.get("heart_sha") == HEART
            and value.get("candidate_path_count") == 154 and len(value.get("files", {})) == 154
            and value.get("selected_methods") == [method for _, method in PHASES]
            and Counter(row.get("origin") for row in value["files"].values()) == ORIGINS,
            "Wrong exact Page154 source closure")
    require(value["files"][SERVICE]["after_sha256"] == SERVICE_SHA
            and value["qualified139_patch_sha256"] == "2e898ac9aac29c0f53dd777492be6b47f14784949313364ff47439de93cd3c00",
            "Native service or retained139 source changed")
    require(digest(control / relative(value["qualified139_patch"])) == value["qualified139_patch_sha256"],
            "Retained original139 patch bytes differ")
    for name, row in value["files"].items():
        relative(name)
        require(re.fullmatch("[0-9a-f]{64}", row["after_sha256"]), "Invalid native source digest")
        if "control_source" in row:
            require(digest(control / relative(row["control_source"])) == row["after_sha256"],
                    "Additive Page154 overlay differs")
    return value


def named_events(rows, method):
    require(rows and all(isinstance(row, dict) and row.get("Package") == PACKAGE for row in rows),
            "Wrong native event package")
    named = [row for row in rows if row.get("Test")]
    require({row["Test"] for row in named} == {method}, "Wrong or extra actual native method")
    require([row["Action"] for row in named if row.get("Action") in {"run", "pass", "fail", "skip"}] == ["run", "pass"],
            "Original selected native method did not run and pass exactly once")
    require([row["Action"] for row in rows if not row.get("Test")
             and row.get("Action") in {"pass", "fail", "skip"}] == ["pass"],
            "Original native package did not pass")


def native_observations(manifest, build, acceptance, audit, phases):
    expected = {name: row["after_sha256"] for name, row in manifest["files"].items()}
    require(build.get("status") == "PASS_NATIVE_PAGE_CANDIDATE_COMPILE_ONLY"
            and build.get("app_sha") == NATIVE_SOURCE and build.get("heart_sha") == HEART
            and build.get("candidate_sha256") == MANIFEST_SHA and build.get("runtime_version") == VERSION
            and build.get("binary_sha256") == NATIVE_BINARY_SHA and build.get("source_sha256") == expected
            and build.get("actual_methods_executed") == 0 and build.get("previous_methods_rerun") == 0,
            "Original native build/source does not belong to Page154")
    require(acceptance.get("status") == "PASS_NATIVE_PAGE_CAPTURE_AND_COLD_REOPEN"
            and acceptance.get("app_sha") == NATIVE_SOURCE and acceptance.get("heart_sha") == HEART
            and acceptance.get("candidate_sha256") == MANIFEST_SHA
            and acceptance.get("binary_sha256") == NATIVE_BINARY_SHA
            and type(acceptance.get("actual_methods_executed")) is int and acceptance["actual_methods_executed"] == 2
            and type(acceptance.get("actual_methods_passed")) is int and acceptance["actual_methods_passed"] == 2
            and acceptance.get("current_source_sha256") == expected and acceptance.get("previous_methods_rerun") == 0
            and acceptance.get("native_page_apply") == acceptance.get("native_service_acceptance") ==
                acceptance.get("process_reopen") == "PASS"
            and acceptance.get("apple") == acceptance.get("mounted_editor") == "NOT_RUN"
            and acceptance.get("app_capability") == "OFF",
            "Original native Page2 acceptance differs")
    require(audit.get("status") == "AUDITED_NATIVE_PAGE_CAPTURE_AND_PROCESS_REOPEN_PASS"
            and audit.get("candidate_sha256") == MANIFEST_SHA and audit.get("executed_app_sha") == NATIVE_SOURCE
            and audit.get("native_source_paths") == 154 and audit.get("actual_new_methods_run") == 2
            and audit.get("actual_new_methods_passed") == 2
            and audit.get("named_methods") == [method for _, method in PHASES]
            and audit.get("private_raw_logs_exported") is False
            and audit.get("exact_original_qualified139_plus_current9_plus_wire3_service1_page_tests2") is True,
            "Independent original native audit differs")
    require(len(phases) == len(acceptance["phases"]) == len(acceptance["attempts"]) == 2,
            "Exactly two original native phases required")
    for index, ((phase, method), observed) in enumerate(zip(PHASES, phases)):
        row, attempt = acceptance["phases"][index], acceptance["attempts"][index]
        require(row["phase"] == attempt["phase"] == phase and row["method"] == attempt["method"] == method
                and row["status"] == "PASS" and row["terminal_count"] == 1
                and attempt["exit_code"] == 0 and attempt["named_actions"] == ["run", "pass"]
                and row["pid"] == observed.get("pid")
                and observed.get("phase") == phase and observed.get("source_manifest_sha256") == MANIFEST_SHA
                and observed.get("runtime_version") == VERSION and observed.get("heart_sha") == HEART
                and observed.get("test_passed") is True and observed.get("closed") is True
                and observed.get("account_stop_verified") is True
                and observed.get("apple_acceptance") == "NOT_RUN" and observed.get("app_capability") == "OFF",
                "Original phase identity/lifetime or runtime version differs")
    first, second = phases
    require(type(first["pid"]) is int and type(second["pid"]) is int and first["pid"] > 1
            and second["pid"] > 1 and first["pid"] != second["pid"]
            and first["pid"] == first["create_pid"] == second["create_pid"]
            and acceptance["distinct_native_pids"] == audit["distinct_native_pids"] == [first["pid"], second["pid"]],
            "Original reopen is not a distinct native process")
    for key in ("account_id", "space_id", "object_id", "block_id", "anchor_id", "native_change_id",
                "native_change_sha256", "source_manifest_sha256", "state_sha256", "nonce"):
        require(first[key] == second[key] and first[key], "Original native reopen identity differs")
    require(first["rpc_calls"]["PinkhaSemanticAnchorCapture"] == 4
            and second["rpc_calls"]["PinkhaSemanticAnchorCapture"] == 1,
            "Original native call count differs")
    return expected


def retained_native(control, manifest):
    directory = control / PROOF
    for name, expected in {"build.json": BUILD_SHA, "page-acceptance.json": ACCEPTANCE_SHA,
                           "INDEPENDENT_AUDIT.json": AUDIT_SHA}.items():
        require(digest(directory / name) == expected, "Original Page native evidence bytes changed")
    build = json.loads((directory / "build.json").read_bytes())
    acceptance = json.loads((directory / "page-acceptance.json").read_bytes())
    audit = json.loads((directory / "INDEPENDENT_AUDIT.json").read_bytes())
    evidence_hashes = {"INDEPENDENT_AUDIT.json": AUDIT_SHA}
    for name, expected in audit["artifact_sha256"].items():
        path = directory / relative(name)
        require(path.stat().st_size == expected["bytes"] and digest(path) == expected["sha256"],
                "An original native artifact changed")
        evidence_hashes[name] = expected["sha256"]
    phases = []
    for phase, method in PHASES:
        path = directory / "page-results" / (phase + ".json")
        phases.append(json.loads(path.read_bytes()))
        events = directory / "named-go-events" / (phase + ".jsonl")
        named_events([json.loads(row) for row in events.read_text().splitlines() if row], method)
    expected = native_observations(manifest, build, acceptance, audit, phases)
    return dict(status="RETAINED_ORIGINAL_PAGE2_PASS_NO_TEST_RERUN", source_sha=NATIVE_SOURCE,
                manifest_sha256=MANIFEST_SHA, build_receipt_sha256=BUILD_SHA,
                acceptance_sha256=ACCEPTANCE_SHA, audit_sha256=AUDIT_SHA,
                original_native_binary_sha256=NATIVE_BINARY_SHA, source_sha256=expected,
                module_sha256=manifest["module_sha256"], original_actual_methods=2,
                methods_executed_this_run=0, original_distinct_native_pids=acceptance["distinct_native_pids"],
                evidence_sha256=evidence_hashes, original_scope_limits=audit["not_proven"])


def verify_source(heart, manifest):
    require(git(heart, "rev-parse", "HEAD") == HEART, "Wrong native base")
    hashes = file_hashes(heart, {name: row["after_sha256"] for name, row in manifest["files"].items()})
    file_hashes(heart, manifest["module_sha256"])
    changed = set(git(heart, "diff", "--name-only", "HEAD").splitlines())
    added = set(git(heart, "ls-files", "--others", "--exclude-standard").splitlines())
    tracked = {name for name, row in manifest["files"].items() if row["before_sha256"] is not None}
    require(changed == tracked and added == set(manifest["files"]) - tracked,
            "Unreviewed native source changes are present")
    return hashes


def prepare_source(control, heart, manifest, run):
    require(git(heart, "rev-parse", "HEAD") == HEART and not git(heart, "status", "--porcelain"),
            "Fresh clean exact native checkout required")
    file_hashes(heart, manifest["module_sha256"])
    for name, row in manifest["files"].items():
        path = heart / relative(name)
        if row["before_sha256"] is None:
            require(not path.exists(), "Additive source already exists")
        else:
            require(digest(path) == row["before_sha256"], "Original native source differs before patch")
    patch = control / relative(manifest["qualified139_patch"])
    run(["git", "apply", "--check", str(patch)], "source-patch-check")
    run(["git", "apply", str(patch)], "source-patch-apply")
    for name, row in manifest["files"].items():
        if "control_source" in row:
            destination = heart / relative(name)
            require(not destination.exists() and row["before_sha256"] is None,
                    "Additive source cannot overwrite a native input")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(control / relative(row["control_source"]), destination)
    return verify_source(heart, manifest)


def generated_entry(headers, symbols):
    pattern = (r"(?m)^FOUNDATION_EXPORT\s+NSData\s*\*\s*(?:_Nullable\s+)?"
               + ENTRY + r"\s*\(\s*NSData\s*\*\s*(?:_Nullable\s+)?raw\s*\)\s*;")
    declarations = re.findall(pattern, headers)
    require(len(declarations) == 1, "Actual generated byte entry declaration missing or ambiguous")
    require("ServicePinkhaTorahAuthorizedOperationRead" in headers,
            "Required existing authorized-read entry is missing")
    require("ServicePinkhaCoherentAppleAuthorityFixture" not in headers,
            "Fixture entry is forbidden in this distinct production artifact")
    definitions = [line.strip() for line in symbols.splitlines()
                   if len(line.split()) >= 2 and line.split()[-2:] == ["T", "_" + ENTRY]]
    require(len(definitions) == 1, "Actual exported compiled byte-entry symbol missing or ambiguous")
    return dict(declaration=declarations[0], defined_symbol=definitions[0], entry=ENTRY,
                status="ACTUAL_GENERATED_HEADER_AND_DEFINED_BINARY_SYMBOL")
