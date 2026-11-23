#!/usr/bin/env python3
"""Qualify byte-owned archive admission against actual original native exports."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
import zipfile

PACKET = "docs/pinkha/torah-integration/native-owned-annotation-contract-20261123"
SLICE = "slice-a"
HEART = "d98420b1113536afd08cde6de9a5816f6d27ffff"
SUPPORT_SHA256 = "017778c096eca985774bd1a4f1e1e117ac3dee6ac08082c2a9793273826aa196"
NEW_NATIVE = (
    "native/core/block/import/owned_annotation_archive.go",
    "native/core/block/import/owned_annotation_archive_test.go",
    "native/core/application/owned_annotation_export_native_test.go",
)
COMPILED_ORIGINAL_MODELS = (
    "pb/snapshot.pb.go", "pb/changes.pb.go", "pkg/lib/pb/model/models.pb.go",
    "pb/commands.pb.go",
)
SPECIMENS = ("text", "format", "nested", "attachment")
PACKAGES = ("github.com/anyproto/anytype-heart/core/application",
            "github.com/anyproto/anytype-heart/core/block/import")


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], timeout=60)


def safe(root, relative):
    relative = Path(relative)
    require(not relative.is_absolute() and relative.parts
            and ".." not in relative.parts, "Unsafe retained path")
    path = root / relative
    require(path.resolve().is_relative_to(root.resolve()), "Aliased retained path")
    cursor = path
    while cursor != root:
        require(not cursor.is_symlink(), "Retained path contains a symlink")
        cursor = cursor.parent
    return path


def read_sources(control, manifest, destination=None, original_repository=None):
    inventory, destinations = [], set()
    for entry in manifest["source_inputs"]:
        name = entry["destination"]
        require(name not in destinations, "Duplicate materialized source")
        destinations.add(name)
        retained = PACKET + "/" + SLICE + "/retained-inputs/" + name
        raw = safe(control, retained).read_bytes()
        require(raw == git(control, "show", "HEAD:" + retained), "Dirty retained source input")
        require(len(raw) == entry["bytes"] and sha(raw) == entry["sha256"]
                and blob(raw) == entry["git_blob"], "Immutable source input differs")
        if original_repository is not None:
            original = git(original_repository, "show", entry["revision"] + ":" + entry["source_path"])
            require(original == raw, "Actual original revision:path differs")
        if destination is not None:
            target = safe(destination, name)
            require(not target.exists(), "Preserve a pre-existing source output")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        inventory.append({key: entry[key] for key in
                          ("revision", "source_path", "destination", "bytes", "sha256", "git_blob")})
    require(len(inventory) == 17
            and sum(row["role"] == "native-product" for row in manifest["source_inputs"]) == 12,
            "Unexpected retained native composition")
    return inventory


def control_inputs(control, packet, manifest):
    name = PACKET + "/" + SLICE + "/EXECUTION_INPUTS.json"
    raw = safe(control, name).read_bytes()
    require(raw == git(control, "show", "HEAD:" + name), "Dirty native execution contract")
    require(manifest["schema"] == 1 and manifest["heart_base"] == HEART
            and manifest["historical_controls_replayed"] is False
            and manifest["generated_rpc_changes"] is False
            and manifest["production_import_activated"] is False,
            "Unexpected native qualification scope")
    entries = manifest["control_inputs"]
    expected = set(NEW_NATIVE) | {SLICE + "/run_native_archive.py"}
    require(len(entries) == len(expected) and {row["path"] for row in entries} == expected,
            "Native control allowlist differs")
    result = []
    for entry in entries:
        data = safe(packet, entry["path"]).read_bytes()
        require(sha(data) == entry["sha256"] and len(data) == entry["bytes"]
                and blob(data) == entry["git_blob"], "Native control input changed")
        require(data == git(control, "show", "HEAD:" + PACKET + "/" + entry["path"]),
                "Dirty native control input")
        result.append(entry)
    new_rows = manifest["new_native_inputs"]
    require(len(new_rows) == 3 and {row["path"] for row in new_rows} == set(NEW_NATIVE),
            "Only the reviewed three new native files may be installed")
    by_name = {row["path"]: row for row in entries}
    for row in new_rows:
        require(row["heart_preimage_sha256"] is None
                and row["heart_path"] == row["path"].removeprefix("native/")
                and all(row[key] == by_name[row["path"]][key]
                        for key in ("bytes", "sha256", "git_blob")),
                "New native file binding differs")
    require(tuple(manifest["compiled_original_model_paths"]) == COMPILED_ORIGINAL_MODELS,
            "Original generated model compilation binding differs")
    require(tuple(target["import_path"] for target in manifest["targets"]) == PACKAGES,
            "Only the two reviewed native packages may execute")
    return result


def verify_original_models(heart, manifest, object_database=None):
    rows = []
    entries = manifest["original_model_and_rpc_inputs"]
    require(len(entries) == 11 and len({row["path"] for row in entries}) == 11,
            "Original generated/proto inventory differs")
    for entry in entries:
        raw = (git(object_database, "show", HEART + ":" + entry["path"])
               if object_database is not None else safe(heart, entry["path"]).read_bytes())
        require(len(raw) == entry["bytes"] and sha(raw) == entry["sha256"]
                and blob(raw) == entry["git_blob"], "Unchanged original model/proto/RPC bytes differ")
        rows.append(dict(entry))
    return rows


def materialize_and_load_support(control, manifest, work):
    inputs = work / "inputs"
    inputs.mkdir()
    inventory = read_sources(control, manifest, inputs)
    source = inputs / "support/run_original_application_compile.py"
    require(sha(source.read_bytes()) == SUPPORT_SHA256, "Original bounded process owner differs")
    spec = importlib.util.spec_from_file_location("original_native_process_owner", source)
    support = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(support)
    return support, inputs, inventory


def install_native(support, commands, inputs, heart, packet, manifest, evidence):
    require(git(heart, "rev-parse", "HEAD").decode().strip() == HEART, "Original Heart checkout differs")
    require(not git(heart, "status", "--porcelain", "--untracked-files=all").strip(),
            "Original Heart checkout is not fresh")
    for name, digest in manifest["original_module_hashes"].items():
        require(support.digest(heart / name) == digest, "Original module/native checksum differs")
    verify_original_models(heart, manifest)
    patch = inputs / "r14/native-heart-integration.patch"
    inventory = json.loads((inputs / "r14/native-heart-integration.json").read_bytes())
    require(inventory["heart_sha"] == HEART and inventory["patch_sha256"] == support.digest(patch),
            "Original r14 binding differs")
    for entry in inventory["files"]:
        target = safe(heart, entry["path"])
        before = entry["before_sha256"]
        require((target.is_file() and support.digest(target) == before)
                if before is not None else not target.exists(), "Original r14 preimage differs")
    commands.require("r14-check", ["git", "apply", "--check", str(patch)], heart, 30)
    commands.require("r14-apply", ["git", "apply", str(patch)], heart, 30)
    composed, required = {}, {}
    for entry in inventory["files"]:
        require(support.digest(heart / entry["path"]) == entry["after_sha256"],
                "Original r14 afterimage differs")
        composed[entry["path"]] = entry["after_sha256"]
    for entry in manifest["source_inputs"]:
        if entry["role"] != "native-product":
            continue
        name = entry["heart_path"]
        target = safe(heart, name)
        before = entry["heart_preimage_sha256"]
        require((target.is_file() and support.digest(target) == before)
                if before is not None else not target.exists(),
                "Original native product preimage differs: " + name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(safe(inputs, entry["destination"]).read_bytes())
        require(support.digest(target) == entry["sha256"], "Accepted native product afterimage differs")
        composed[name] = required[name] = entry["sha256"]
    for entry in manifest["new_native_inputs"]:
        name = entry["heart_path"]
        target = safe(heart, name)
        require(not target.exists(), "New native path already exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(safe(packet, entry["path"]).read_bytes())
        require(support.digest(target) == entry["sha256"], "Reviewed new native afterimage differs")
        composed[name] = required[name] = entry["sha256"]
    originals = verify_original_models(heart, manifest)
    for row in originals:
        if row["path"] in COMPILED_ORIGINAL_MODELS:
            required[row["path"]] = row["sha256"]
    require(len(required) == 19, "Actual required compiler closure differs")
    status = git(heart, "status", "--porcelain", "--untracked-files=all").decode().splitlines()
    require(all(row[:2] in (" M", "??") and row[3:] in composed for row in status),
            "Unexpected native source mutation")
    for name, digest in composed.items():
        require(support.digest(heart / name) == digest, "Composed original source differs")
    support.write_json(evidence / "COMPOSED_NATIVE_SOURCES.json", {
        "all_declared_afterimages": composed, "required_actual_compiler_coverage": required,
        "unchanged_original_model_proto_rpc_inputs": originals,
        "generated_rpc_changes": False, "old_native_selectors_replayed": False,
        "production_import_activated": False,
    })
    return required, composed


def verify_native_results(path, parent, expected):
    events = [json.loads(line) for line in path.read_text().splitlines()]
    runs, passes, failures, skips = {}, {}, [], []
    for event in events:
        name, action = event.get("Test"), event.get("Action")
        if name and action == "run":
            runs[name] = runs.get(name, 0) + 1
        if name and action == "pass":
            passes[name] = passes.get(name, 0) + 1
        if action == "fail":
            failures.append(name or "<package>")
        if action == "skip":
            skips.append(name or "<package>")
    selected = set(expected) | {parent}
    require(set(runs) == selected and all(n == 1 for n in runs.values()),
            "Unexpected, missing or replayed native case")
    require(set(passes) == selected and all(n == 1 for n in passes.values())
            and not failures and not skips, "Actual native cases did not all pass once")
    require(sum(e.get("Action") == "pass" and not e.get("Test") for e in events) == 1,
            "Native package completion absent or repeated")
    return {"leaf_cases": sorted(expected), "leaf_pass": len(expected),
            "fail": 0, "skip": 0, "original_prior_cases_replayed": 0, "json_events": len(events)}


def verify_specimens(fixtures):
    result, identities = [], set()
    expected_blocks = {"text": 2, "format": 2, "nested": 4, "attachment": 1}
    for kind in SPECIMENS:
        manifest_path = safe(fixtures, kind + "-manifest.json")
        manifest = json.loads(manifest_path.read_bytes())
        archive_path = safe(fixtures, kind + ".zip")
        require(archive_path.is_file() and archive_path.stat().st_size <= 8 << 20,
                "Actual specimen is absent or exceeds evidence retention bound")
        raw = archive_path.read_bytes()
        require(manifest["schema"] == 1 and manifest["specimen"] == kind
                and manifest["archive"] == kind + ".zip"
                and manifest["archive_bytes"] == len(raw)
                and manifest["archive_sha256"] == sha(raw)
                and manifest["original_export_report_success"] is True
                and manifest["native_text_format_nested_attachment_checks_passed"] is True,
                "Actual native export receipt differs")
        require(all(manifest[key] is False for key in
                    ("native_import_activated", "body_ack_authority",
                     "cold_reopen_qualified", "swift_invocation_qualified")),
                "Native fixture overclaims an unrelated qualification")
        require(manifest["expected_native_blocks"] == expected_blocks[kind]
                and manifest["root_id"] in manifest["generated_snapshot_ids"]
                and all(isinstance(manifest[key], str) and manifest[key]
                        for key in ("root_id", "space_id", "account_id")),
                "Native specimen identity/content evidence is incomplete")
        identities.add((manifest["account_id"], manifest["space_id"]))
        with zipfile.ZipFile(archive_path) as zipped:
            names = zipped.namelist()
            require(0 < len(names) <= 512 and len(names) == len(set(names))
                    and sum(member.file_size for member in zipped.infolist()) <= 8 << 20,
                    "Actual native archive member/expanded inventory exceeds its bound")
            require(zipped.testzip() is None, "Actual native archive member CRC differs")
            by_name = {row["name"]: row for row in manifest["members"]}
            require(len(by_name) == len(manifest["members"]) == len(names)
                    and set(by_name) == set(names), "Actual native manifest member inventory differs")
            expanded = 0
            for member in zipped.infolist():
                body = zipped.read(member)
                expanded += len(body)
                row = by_name[member.filename]
                require(expanded <= 8 << 20 and len(body) == row["bytes"] == member.file_size
                        and sha(body) == row["sha256"] and member.flag_bits == row["zip_flags"]
                        and member.compress_type == row["zip_method"]
                        and member.extra.hex() == row["zip_extra_hex"],
                        "Actual native member bytes/header differ from fixture readback")
        report_path = safe(fixtures, kind + "-export-report.json")
        report = json.loads(report_path.read_bytes())
        require(isinstance(report, dict) and report.get("status", 0) == 0
                and report.get("succeed", 0) > 0 and report.get("objectErrors", 0) == 0
                and report.get("fileErrors", 0) == 0, "Actual original export report is incomplete")
        # Native assertions independently checked every report issue before
        # writing the manifest; its generated numeric SUCCESS may be omitted.
        result.append({"specimen": kind, "archive": kind + ".zip", "bytes": len(raw),
                       "sha256": sha(raw), "members": len(names),
                       "generated_snapshots": len(manifest["generated_snapshot_ids"]),
                       "manifest_sha256": sha(manifest_path.read_bytes()),
                       "report_sha256": sha(report_path.read_bytes()),
                       "product_65536_byte_limit_met": len(raw) <= 65536})
    require(len(identities) == 1, "Native specimens came from different original fixture owners")
    cleanup = json.loads(safe(fixtures, "native-export-cleanup.json").read_bytes())
    require(cleanup["original_account_stop_returned_or_app_absent"] is True
            and cleanup["owned_directory_removed"] is True
            and cleanup["import_started"] is False
            and cleanup["cold_reopen_qualified"] is False
            and cleanup["body_ack_authority"] is False, "Original native fixture cleanup did not complete")
    return result, cleanup


def verify_rejections(fixtures, manifest, specimens):
    path = safe(fixtures, "archive-admission-rejections.json")
    receipt = json.loads(path.read_bytes())
    require(receipt["schema"] == 1 and receipt["genuine_base_specimens"] == 4
            and receipt["archive_admission_only"] is True
            and receipt["native_import_activated"] is False
            and receipt["body_ack_authority"] is False, "Archive rejection scope differs")
    expected = manifest["expected_rejections"]
    rows = receipt["derived_rejection_cases"]
    require(len(rows) == len(expected) == 26
            and len({row["case"] for row in rows}) == len(rows)
            and {row["case"] for row in rows} == set(expected),
            "Actual derived rejection cases differ")
    actual = {row["specimen"]: row["sha256"] for row in specimens}
    for row in rows:
        require(row["refusal"] == expected[row["case"]]
                and row["base_specimen"] in actual
                and row["base_sha256"] == actual[row["base_specimen"]]
                and re.fullmatch(r"[0-9a-f]{64}", row["variant_sha256"])
                and row["variant_sha256"] != row["base_sha256"],
                "Derived rejection does not bind genuine original bytes and exact refusal")
    return {"path": path.name, "sha256": sha(path.read_bytes()), "cases": len(rows)}


def verify_fixture_inventory(fixtures):
    registration = json.loads(safe(fixtures, "schema-registration.json").read_bytes())
    phases = registration.get("registration_calls")
    require(type(phases) is int and 1 <= phases <= 21
            and registration.get("registration_complete") is True,
            "Native schema history has no bounded completed registration inventory")
    expected = {kind + suffix for kind in SPECIMENS
                for suffix in (".zip", "-manifest.json", "-export-report.json")}
    expected |= {"native-export-cleanup.json", "archive-admission-rejections.json",
                 "schema-registration.json"}
    expected |= {"schema-registration-%02d.json" % phase for phase in range(phases)}
    require({path.name for path in fixtures.iterdir()} == expected,
            "Unexpected specimen evidence files")
    for name in expected:
        require(safe(fixtures, name).is_file(), "Specimen evidence must be a regular file")


def execute_target(support, commands, go, heart, work, evidence, target, result):
    name = target["name"]
    binary = work / (name + ".test")
    commands.require("compile-" + name, [go, "test", "-c", "-p", "2", "-o", str(binary),
                                       target["package"]], heart, 3600)
    require(binary.is_file() and binary.stat().st_size > 0, "Native compiler produced no executable")
    binary_info = {"path": binary.name, "sha256": support.digest(binary),
                   "bytes": binary.stat().st_size, "retained_in_artifact": False}
    result.setdefault("native_binaries", {})[name] = binary_info
    commands.require(name + "-buildinfo", [go, "version", "-m", str(binary)], heart, 30)
    result[name] = "EXECUTION_REQUESTED"
    support.write_json(evidence / "RESULT.json", result)
    output = commands.require("execute-" + name, [
        go, "tool", "test2json", "-t", "-p", target["import_path"], str(binary),
        "-test.v=test2json", "-test.run=" + target["selector"], "-test.count=1",
        "-test.timeout=" + target["test_timeout"],
    ], heart, target["command_timeout_seconds"])
    cases = verify_native_results(output, target["parent"], target["expected_cases"])
    require(support.digest(binary) == binary_info["sha256"], "Executed native binary changed")
    result.setdefault("native_cases", {})[name] = cases
    result[name] = "ACTUAL_NATIVE_CASES_PASSED"
    support.write_json(evidence / "RESULT.json", result)
    return binary, binary_info


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--control-root", required=True, type=Path)
    parser.add_argument("--control-head", required=True)
    parser.add_argument("--execution-manifest-sha256", required=True)
    parser.add_argument("--heart", type=Path)
    parser.add_argument("--work", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--job-deadline-unix", type=int)
    parser.add_argument("--source-only", action="store_true")
    parser.add_argument("--original-repository", type=Path)
    parser.add_argument("--original-heart-repository", type=Path)
    args = parser.parse_args()
    control = args.control_root.resolve()
    packet = control / PACKET
    manifest_raw = safe(packet, SLICE + "/EXECUTION_INPUTS.json").read_bytes()
    require(sha(manifest_raw) == args.execution_manifest_sha256, "Workflow manifest binding differs")
    manifest = json.loads(manifest_raw)
    require(re.fullmatch(r"[0-9a-f]{40}", args.control_head)
            and git(control, "rev-parse", "HEAD").decode().strip() == args.control_head,
            "Workflow exact source differs")
    controls = control_inputs(control, packet, manifest)
    if args.source_only:
        rows = read_sources(control, manifest, original_repository=args.original_repository)
        models = (verify_original_models(None, manifest, args.original_heart_repository)
                  if args.original_heart_repository else [])
        new_originals = []
        if args.original_repository is not None:
            for entry in manifest["new_native_inputs"]:
                original = git(args.original_repository, "show",
                               entry["source_revision"] + ":" + PACKET + "/" + entry["path"])
                require(original == safe(packet, entry["path"]).read_bytes(),
                        "Reviewed three-file source commit differs")
                new_originals.append(entry["path"])
        changed = git(control, "diff", "--name-status", "--no-renames",
                      manifest["control_preparation_base"], args.control_head).decode().splitlines()
        for row in changed:
            status, name = row.split("\t", 1)
            require(status in ("A", "M") and (name.startswith(PACKET + "/" + SLICE + "/")
                    or name == ".github/workflows/otzaria-native-archive.yml"),
                    "Change outside the owned source/gate preparation boundary")
        print(json.dumps({
            "status": "SOURCE_ONLY_PASS", "checkout_sha": args.control_head,
            "checkout_tree": git(control, "rev-parse", "HEAD^{tree}").decode().strip(),
            "immutable_source_rows": len(rows), "control_inputs": controls,
            "original_revision_bytes_independently_checked": args.original_repository is not None,
            "original_model_proto_rpc_rows_independently_checked": len(models),
            "authored_native_rows_independently_checked": new_originals,
            "changes_since_preparation_base": changed,
            "native_execution": False, "provider_called": False,
            "production_import_activated": False, "historical_controls_replayed": False,
        }, indent=2))
        return 0
    require(all(value is not None for value in
                (args.heart, args.work, args.evidence, args.job_deadline_unix)),
            "Native execution requires explicit owned roots and deadline")
    heart, work, evidence = (p.resolve() for p in (args.heart, args.work, args.evidence))
    require(platform.system() == "Darwin" and platform.machine() == "arm64",
            "Actual Darwin ARM64 native route required")
    require(not work.exists() and not evidence.exists(), "Fresh owned native work/evidence required")
    for path in (heart, work, evidence):
        require(path.is_relative_to(control) and path != control, "Execution path escapes owned checkout")
    roots = (packet, heart, work, evidence)
    require(not any(a == b or a.is_relative_to(b) or b.is_relative_to(a)
                    for i, a in enumerate(roots) for b in roots[i+1:]), "Execution roots overlap")
    require(time.time() < args.job_deadline_unix <= time.time() + 7100, "Invalid native deadline")
    evidence.mkdir(parents=True)
    fixtures = evidence / "fixtures"
    fixtures.mkdir(mode=0o700)
    work.mkdir(parents=True)
    support, inputs, source_rows = materialize_and_load_support(control, manifest, work)
    temporary = work / "native-temporary"
    temporary.mkdir(mode=0o700)
    allowed = ("PATH", "HOME", "LANG", "LC_ALL", "DEVELOPER_DIR", "SDKROOT", "GOCACHE", "GOMODCACHE")
    env = {key: os.environ[key] for key in allowed if key in os.environ}
    env.update(TMPDIR=str(temporary), CGO_ENABLED="1", GOMAXPROCS="2",
               GOTOOLCHAIN="local", GOWORK="off", GOENV="off", GOFLAGS="-mod=readonly",
               OTZARIA_NATIVE_EXPORT_FIXTURES=str(fixtures))
    commands = support.Commands(evidence, env, args.job_deadline_unix - 180)
    result = {
        "status": "STARTED_NOT_ACCEPTED", "control_head": args.control_head, "heart_base": HEART,
        "execution_manifest_sha256": sha(manifest_raw), "scope": manifest["scope"],
        "source_inputs": source_rows, "control_inputs": controls,
        "native_exports": "NOT_RUN", "archive_admission": "NOT_RUN",
        "historical_controls_replayed": False, "generated_rpc_changes": False,
        "production_import_activated": False, "body_ack_authority": False,
        "cold_reopen_qualified": False, "swift_invocation_qualified": False,
    }
    support.write_json(evidence / "RESULT.json", result)
    success = False
    try:
        required, composed = install_native(support, commands, inputs, heart, packet, manifest, evidence)
        go = shutil.which("go")
        require(go, "Native Go toolchain absent")
        go = str(Path(go).resolve())
        version = commands.require("go-version", [go, "version"], heart, 30).read_text().strip()
        require(version == "go version go1.26.5 darwin/arm64", "Original Go toolchain differs")
        xcode = commands.require("xcode-version", ["xcodebuild", "-version"], heart, 30).read_text()
        require(xcode.startswith("Xcode 27"), "Original Apple compiler route differs")
        commands.require("clang-version", ["xcrun", "--sdk", "macosx", "clang", "--version"], heart, 30)
        result["go"] = {"version": version, "path": go, "sha256": support.digest(go)}
        formatting = commands.require("new-native-source-format", [
            str(Path(go).with_name("gofmt")), "-l",
            *[str(heart / row["heart_path"]) for row in manifest["new_native_inputs"]],
        ], heart, 30)
        require(not formatting.read_text().strip(), "New native source is not exact gofmt")
        commands.require("original-tantivy", [
            sys.executable, "-I", str(inputs / "support/bootstrap/prepare_original_tantivy.py"),
            "--heart", str(heart), "--helper", str(inputs / "support/bootstrap/build_custom_heart.py"),
            "--helper-sha256", "0ebbe2f6227418eac2c532b0058290158319ba9f786baaf445de444887e8c669",
            "--receipt", str(evidence / "TANTIVY_SETUP.json"),
        ], heart, 600)
        native = support.native_library_inputs(heart)
        require(native == manifest["expected_tantivy_inputs"], "Original native Tantivy bytes differ")
        env["CGO_LDFLAGS"] = "-L" + str(heart / "deps/libs/darwin-arm64")
        listing = commands.require("declared-native-inputs", [
            go, "list", "-deps", "-test", "-json", *[row["package"] for row in manifest["targets"]],
        ], heart, 1200)
        coverage = [{"path": name, "sha256": digest} for name, digest in sorted(required.items())]
        closure = support.dependency_inputs(listing, heart, coverage)
        # The unchanged original helper verifies application. This explicit
        # additional check also verifies the actual archive package selection.
        present = {row["import_path"] for row in closure["packages"]}
        require(set(PACKAGES).issubset(present), "Both actual native package closures are required")
        closure["original_helper_selected_packages"] = closure["selected_original_packages"]
        closure["selected_original_packages"] = list(PACKAGES)
        support.write_json(evidence / "DECLARED_NATIVE_INPUTS.json", closure)
        require(len(closure["required_product_test_coverage"]) == 19, "Native input closure is incomplete")
        export_binary = execute_target(support, commands, go, heart, work, evidence,
                                       manifest["targets"][0], result)
        specimens, native_cleanup = verify_specimens(fixtures)
        result["actual_original_specimens"] = specimens
        result["actual_native_fixture_cleanup"] = native_cleanup
        support.write_json(evidence / "RESULT.json", result)
        archive_binary = execute_target(support, commands, go, heart, work, evidence,
                                        manifest["targets"][1], result)
        result["derived_rejection_receipt"] = verify_rejections(fixtures, manifest, specimens)
        require(verify_specimens(fixtures) == (specimens, native_cleanup),
                "Real native specimens changed during archive admission")
        verify_fixture_inventory(fixtures)
        for entry in closure["files"]:
            require(support.digest(entry["path"]) == entry["sha256"],
                    "Declared native input changed during execution")
        for name, digest in composed.items():
            require(support.digest(heart / name) == digest, "Product/test source changed during execution")
        verify_original_models(heart, manifest)
        for name, digest in manifest["original_module_hashes"].items():
            require(support.digest(heart / name) == digest, "Original module input changed")
        require(support.native_library_inputs(heart) == native, "Native link inputs changed")
        for binary, info in (export_binary, archive_binary):
            require(support.digest(binary) == info["sha256"], "Executed native binary changed")
        control_inputs(control, packet, manifest)
        read_sources(control, manifest)
        require(git(control, "rev-parse", "HEAD").decode().strip() == args.control_head,
                "Control revision changed during execution")
        result["status"], success = "PASS_NATIVE_EXPORT_AND_ARCHIVE_ADMISSION_ONLY", True
    except BaseException as error:
        result.update(status="FAIL", error_type=type(error).__name__, error=str(error))
    finally:
        try:
            require(commands.owned_groups_drained, "Preserve native state: owned process group not drained")
            shutil.rmtree(temporary)
            result["owned_native_temporary_removed"] = True
        except Exception as error:
            result.update(status="FAIL", owned_native_temporary_removed=False,
                          cleanup_error_type=type(error).__name__)
            success = False
        result["owned_command_groups_drained"] = commands.owned_groups_drained
        result["commands"] = len(commands.items)
        result["finished_unix"] = time.time()
        support.write_json(evidence / "RESULT.json", result)
        indexed = []
        for path in sorted(evidence.rglob("*")):
            require(not path.is_symlink(), "Evidence contains a symlink")
            if path.is_file() and path.name != "EVIDENCE_INDEX.json":
                indexed.append({"path": path.relative_to(evidence).as_posix(),
                                "bytes": path.stat().st_size, "sha256": support.digest(path)})
        support.write_json(evidence / "EVIDENCE_INDEX.json", {
            "scope": "Actual original exports, bounded archive admission and owned staging. "
                     "No wallet, account database, private key, import activation or body ACK.",
            "files": indexed,
        })
    return 0 if success else 1


if __name__ == "__main__":
    def interrupted(signum, frame):
        raise KeyboardInterrupt("Native workflow interrupted: " + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    sys.exit(main())
