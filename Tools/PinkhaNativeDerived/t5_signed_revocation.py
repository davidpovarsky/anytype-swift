"""One real former-member cached-query boundary on the corrected r15 source.

No product patch is introduced. An observed authorization gap keeps this run
failed and its sanitized actual observation intact; it cannot become acceptance
through a controller exception or an expected-failure label.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
from uuid import uuid4

import attachment_runtime
import build_custom_heart
import run_t5_native_attachment as native
import run_t5_pairs_ci as modules

PROTOCOL = "pinkha-t5-signed-local-revocation-v1"
METHOD = "TestT5NativeCachedQueriesAfterSignedRevocation"
PROFILE = "r15-attachment-v1"
FIXTURE = "Tools/PinkhaNativeDerived/signed_revocation/native_signed_revocation_test.go"
SOURCE = attachment_runtime.SOURCE_SHA
HEART = attachment_runtime.HEART_SHA
HELPER_SHA = "0ebbe2f6227418eac2c532b0058290158319ba9f786baaf445de444887e8c669"
PASS = "PASS_LOCAL_SIGNED_REVOCATION"
DENIAL_FAILURE = "FAIL_REVOKED_NATIVE_QUERY_EXPOSED_OR_AMBIGUOUS"
OBSERVATION_KEYS = {
    "protocol", "nonce", "pid", "heart_sha", "runtime_version", "fixture_sha256",
    "account_id_sha256", "space_id_sha256", "object_id_sha256", "canonical_sha256",
    "same_engine_account", "populated_native_cache", "reader_positive", "signed_acl_add_head",
    "signed_acl_transfer_head", "signed_acl_remove_head", "current_permission", "had_read_permission",
    "read_key_rotated", "read_key_id_before", "read_key_id_after", "native_acl_updater",
    "local_signed_delivery", "object_search_error_code", "object_search_rows", "object_search_total",
    "object_search_explicit_denial", "object_show_error_code", "object_show_has_payload",
    "object_show_explicit_denial", "account_stop_verified", "rpc_calls", "network_acl_transport",
    "offline_unknown_revocation", "ios_acceptance", "full_t5_acceptance", "status",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_inventory(control):
    paths = native.git(control, "ls-files", "-z", "--", "Tools/PinkhaNativeDerived",
        ".github/workflows/pinkha-t5-signed-revocation.yml").decode().strip("\0").split("\0")
    return {path: digest(control / path) for path in paths if path}


def validate_observation(value, identity, pid, nonce):
    require(isinstance(value, dict) and set(value) == OBSERVATION_KEYS, "Unreviewed native observation schema")
    require(value["protocol"] == PROTOCOL and value["nonce"] == nonce and type(value["pid"]) is int
            and value["pid"] == pid > 0, "Native process/nonce identity differs")
    for key in ("heart_sha", "runtime_version", "fixture_sha256"):
        require(value[key] == identity[key], "Native source marker differs: " + key)
    for key in ("account_id_sha256", "space_id_sha256", "object_id_sha256", "canonical_sha256"):
        require(isinstance(value[key], str) and re.fullmatch(r"[0-9a-f]{64}", value[key]), "Missing exact fixture identity: " + key)
    for key in ("same_engine_account", "populated_native_cache", "reader_positive", "had_read_permission",
                "read_key_rotated", "local_signed_delivery", "account_stop_verified"):
        require(value[key] is True, "Required actual native boundary missing: " + key)
    heads = [value[key] for key in ("signed_acl_add_head", "signed_acl_transfer_head", "signed_acl_remove_head")]
    require(all(isinstance(head, str) and head for head in heads) and len(set(heads)) == 3,
            "Three distinct actual signed membership transitions required")
    require(value["current_permission"] == "none" and value["native_acl_updater"] == "NOT_REPLACED_OR_SUPPRESSED",
            "Current native authority or unmodified callback boundary differs")
    require(all(isinstance(value[key], str) and value[key] for key in ("read_key_id_before", "read_key_id_after"))
            and value["read_key_id_before"] != value["read_key_id_after"], "Actual signed read key did not rotate")
    require(value["network_acl_transport"] == value["ios_acceptance"] == "NOT_RUN"
            and value["offline_unknown_revocation"] == value["full_t5_acceptance"] == "NOT_PROVEN",
            "Local-only evidence overstates remote, offline or App acceptance")
    calls = value["rpc_calls"]
    exact = {"InitialSetParameters": 1, "AppGetVersion": 1, "WalletCreate": 1, "AccountCreate": 1,
             "WorkspaceCreate": 1, "WorkspaceOpen": 1, "ObjectCreateRelation": 1, "ObjectCreateObjectType": 3,
             "ObjectCreate": 2, "ObjectSetDetails": 2, "BlockCreate": 1, "AccountStop": 1, "AppShutdown": 1}
    require(isinstance(calls, dict) and set(calls) == set(exact) | {"ObjectSearch", "ObjectShow"}
            and all(type(count) is int and count > 0 for count in calls.values())
            and all(calls[key] == count for key, count in exact.items())
            and calls["ObjectSearch"] >= 3 and calls["ObjectShow"] >= 4,
            "Native account/query/mutation sequence differs from the reviewed fixture")
    for key in ("object_search_error_code", "object_show_error_code", "object_search_rows", "object_search_total"):
        require(type(value[key]) is int, "Missing actual native response metric: " + key)
    require(value["object_search_error_code"] >= -1 and value["object_show_error_code"] >= -1
            and value["object_search_rows"] >= 0 and value["object_search_total"] >= 0,
            "Impossible native response metric")
    for key in ("object_search_explicit_denial", "object_show_has_payload", "object_show_explicit_denial"):
        require(type(value[key]) is bool, "Missing native denial/payload observation")
    search_denied = (value["object_search_error_code"] > 0 and value["object_search_rows"] == 0
                     and value["object_search_total"] == 0)
    show_denied = value["object_show_error_code"] > 0 and not value["object_show_has_payload"]
    require(value["object_search_explicit_denial"] is search_denied
            and value["object_show_explicit_denial"] is show_denied, "Denial was inferred from an empty aggregate")
    expected = PASS if search_denied and show_denied else DENIAL_FAILURE
    require(value["status"] == expected, "Native status contradicts its actual response observations")
    return expected


def qualify_execution(log, code, observation_status):
    text = log.read_text(encoding="utf-8", errors="replace")
    starts = re.findall(r"^=== RUN\s+(\S+)\s*$", text, re.M)
    endings = re.findall(r"^--- (PASS|FAIL|SKIP): (\S+) \(", text, re.M)
    require(starts == [METHOD] and len(endings) == 1 and endings[0][1] == METHOD,
            "Native fixture selected zero, extra, duplicate or incomplete methods")
    if observation_status == PASS:
        require(code == 0 and endings == [("PASS", METHOD)], "Native success receipt has no actual passing test")
    else:
        require(code != 0 and endings == [("FAIL", METHOD)]
                and ("actual revoked ObjectSearch must explicitly deny" in text
                     or "actual revoked ObjectShow must explicitly deny" in text),
                "Observed failure is not the exact revoked-query contract failure")
    return dict(method=METHOD, tests_started=1, tests_passed=int(observation_status == PASS),
                tests_failed=int(observation_status != PASS), tests_skipped=0,
                exit_code=code, native_log_sha256=digest(log))


def export_private(private, evidence):
    require(not evidence.exists(), "Refuse an existing public native export")
    names = ["ownership.json"]
    secret_path = private / "sensitive-needles.private"
    if not secret_path.is_file() or secret_path.is_symlink():
        return dict(status="WITHHELD_NATIVE_OUTPUT_WITHOUT_SECRET_INVENTORY", files={})
    values = json.loads(secret_path.read_bytes())
    require(isinstance(values, list) and len(values) == 2 and all(isinstance(x, str) and x for x in values),
            "Original account secret inventory is incomplete")
    needles = [value.encode() for value in values]
    names += ["native-observation.json", "native.log"]
    retained = []
    for name in names:
        path = private / name
        if not path.exists():
            continue
        require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(private.resolve()),
                "Native export is outside the owned private directory")
        raw = path.read_bytes()
        require(not any(needle in raw for needle in needles), "Native evidence contains sensitive account material")
        retained.append((name, raw))
    evidence.mkdir(parents=True)
    for name, raw in retained:
        (evidence / name).write_bytes(raw)
    return dict(status="PASS_EXACT_ACCOUNT_SECRET_SCAN", files={name: digest(evidence / name) for name, _ in retained})


def run_fixture(binary, private, env, timeout=330):
    command = [str(binary), "-test.run", "^" + METHOD + "$", "-test.count=1", "-test.v", "-test.timeout=300s"]
    with (private / "native.log").open("x", encoding="utf-8") as output:
        process = subprocess.Popen(command, env=env, cwd=private, stdout=output,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except BaseException:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
            raise
    return dict(pid=process.pid, exit_code=code, command=command)


def execute(args, receipt):
    control, source, heart, work, evidence = [getattr(args, name).resolve() for name in
                                             ("control", "source", "heart", "work", "evidence")]
    require(len({control, source, heart, work, evidence}) == 5, "Distinct isolated build directories required")
    require(platform.system() == "Linux" and platform.machine() == "x86_64"
            and os.environ.get("T5_GO_IMAGE") == native.IMAGE, "Pinned Linux amd64 musl image required")
    require(subprocess.check_output(["go", "version"], text=True).strip() == "go version go1.26.5 linux/amd64",
            "Reviewed Go toolchain required")
    for tree, expected in ((control, os.environ["GITHUB_SHA"]), (source, SOURCE), (heart, HEART)):
        require(native.git(tree, "rev-parse", "HEAD").decode().strip() == expected
                and not native.git(tree, "status", "--porcelain").strip(), "Fresh exact source checkout required")
    require(not work.exists() or not any(work.iterdir()), "Native workspace must be empty")
    work.mkdir(parents=True, exist_ok=True)
    require(shutil.disk_usage(work).free >= 8 * 1024**3, "Native disk reserve below8GiB")
    before = source_inventory(control)
    native.save(evidence / "control-source-before.json", before)
    helper = control / "Tools/PinkhaNativeDerived/build_custom_heart.py"
    require(digest(helper) == HELPER_SHA, "Reviewed builder helper changed")
    require(digest(source / modules.GENPROTO_DECLARATION) == modules.GENPROTO_DECLARATION_SHA,
            "Existing reviewed genproto declaration changed")
    runtime = attachment_runtime.prepare(source, control, PROFILE)
    patch, inventory_path = runtime.write(work / "corrected-source")
    inventory = json.loads(inventory_path.read_bytes())
    native.save(evidence / "runtime-source.json", dict(variant=PROFILE, heart_sha=HEART,
        patch_sha256=runtime.patch_sha256, inventory_sha256=runtime.inventory_sha256, runtime_version=runtime.version,
        inventory=inventory, product_source_changes=0, app_capability="UNCHANGED"))
    env = dict(os.environ, GOMAXPROCS="2", CGO_ENABLED="1", GOTOOLCHAIN="local", GOWORK="off", GOFLAGS="-mod=readonly")
    native.run([sys.executable, "-B", str(helper), "--heart-source", str(heart), "--patch", str(patch),
        "--inventory", str(inventory_path), "--approved-patch-sha256", runtime.patch_sha256,
        "--apply-approved-patch", "--target", "verify", "--evidence", str(evidence / "source-preflight")],
        control, evidence / "source-preflight.log", env, 120)
    applied = native.verify_applied(heart, inventory)
    native.save(evidence / "native-source-before.json", applied)
    original_modules = {name: digest(heart / name) for name in ("go.mod", "go.sum")}
    private = work / "private"
    private.mkdir(mode=0o700)
    try:
        tantivy = build_custom_heart.fetch_tantivy(heart, "linux-amd64-musl")
        require(tantivy["archive_sha256"] == modules.TANTIVY, "Unexpected native Tantivy input")
        native.save(evidence / "tantivy.json", tantivy)
        gowork = work / "go.work"
        gowork.write_text("go 1.26.5\n\nuse " + str(heart) + "\n\nreplace " + modules.GENPROTO_PATH
            + " => " + modules.GENPROTO_PATH + " " + modules.GENPROTO_VERSION + "\n", encoding="utf-8")
        env.update(GOWORK=str(gowork), CGO_LDFLAGS="-L" + str(heart / "deps/libs/linux-amd64-musl"))
        native.run(["go", "mod", "download"], heart, evidence / "download-modules.log", env, 900)
        env["GOPROXY"] = "off"
        native.run(["go", "list", "-m", "-json", "all"], heart, evidence / "resolved-modules.log", env, 120)
        native.run(["go", "list", "-m", "-json", modules.GENPROTO_PATH], heart, evidence / "genproto.log", env, 120)
        genproto = modules.validate_genproto_selection(json.loads((evidence / "genproto.log").read_bytes()))
        fixture, destination = control / FIXTURE, heart / "clientlibrary/service/pinkha_t5_signed_revocation_test.go"
        require(fixture.is_file() and not destination.exists(), "Exact additive native fixture required")
        overlay = work / "overlay.json"
        native.save(overlay, {"Replace": {str(destination): str(fixture)}})
        fixture_sha = digest(fixture)
        binary = work / "pinkha-t5-signed-revocation.test"
        ldflags = ("-extldflags=-static -X github.com/anyproto/anytype-heart/util/vcs.GitCommit=" + HEART
            + " -X github.com/anyproto/anytype-heart/util/vcs.GitSummary=" + runtime.version
            + " -X github.com/anyproto/anytype-heart/clientlibrary/service.t5ACLFixtureSHA=" + fixture_sha)
        receipt["phase"] = "ONE_FOCUSED_NATIVE_BINARY_BUILD"
        native.save(evidence / "receipt.json", receipt)
        native.run(["go", "test", "-c", "-p", "1", "-tags", modules.TAGS, "-overlay", str(overlay),
                    "-ldflags", ldflags, "-o", str(binary), "./clientlibrary/service"],
                   heart, evidence / "compile-native-fixture.log", env, 1800)
        identity = dict(heart_sha=HEART, runtime_version=runtime.version, fixture_sha256=fixture_sha,
                        binary_sha256=digest(binary), app_sha=os.environ["GITHUB_SHA"], genproto=genproto,
                        patch_sha256=runtime.patch_sha256, overlay=json.loads(overlay.read_bytes()))
        native.save(evidence / "build.json", identity)
        nonce = uuid4().hex
        native.save(private / "ownership.json", dict(protocol=PROTOCOL, nonce=nonce, synthetic_only=True))
        root = private / "account-root"
        root.mkdir(mode=0o700)
        env.update(PINKHA_T5_ACL_ROOT=str(root), PINKHA_T5_ACL_REPORT=str(private / "native-observation.json"),
            PINKHA_T5_ACL_NONCE=nonce, PINKHA_T5_ACL_OWNERSHIP=(private / "ownership.json").read_text(),
            PINKHA_T5_ACL_FIXTURE_SHA256=fixture_sha, PINKHA_T5_ACL_RUNTIME_VERSION=runtime.version)
        receipt["phase"] = "ACTUAL_LOCAL_SIGNED_REVOCATION"
        native.save(evidence / "receipt.json", receipt)
        process = run_fixture(binary, private, env)
        receipt["execution"] = process
        require(digest(binary) == identity["binary_sha256"], "Native binary changed during execution")
        observation = json.loads((private / "native-observation.json").read_bytes())
        observed = validate_observation(observation, identity, process["pid"], nonce)
        receipt["actual"] = qualify_execution(private / "native.log", process["exit_code"], observed)
        receipt["native_status"] = observed
        require(observed == PASS, "Actual locally revoked query returned rows/payload or ambiguous success")
        receipt.update(status=PASS, phase="COMPLETE")
    finally:
        receipt["evidence_export"] = export_private(private, evidence / "actual")
        require(source_inventory(control) == before, "Controller or fixture source changed")
        require(native.verify_applied(heart, inventory) == applied, "Native source changed during the proof")
        require({name: digest(heart / name) for name in original_modules} == original_modules,
                "Original native dependency declarations changed")
        native.save(evidence / "control-source-after.json", source_inventory(control))
        native.save(evidence / "native-source-after.json", native.verify_applied(heart, inventory))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("control", "source", "heart", "work", "evidence"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    args.evidence.mkdir(parents=True, exist_ok=True)
    require(not (args.evidence / "receipt.json").exists(), "Refuse an existing native attempt receipt")
    receipt = dict(status="NOT_RUN", native_status="NOT_RUN", phase="SOURCE_PREFLIGHT",
        run_id=os.environ.get("GITHUB_RUN_ID"), run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"),
        app_sha=os.environ.get("GITHUB_SHA"), network_acl_transport="NOT_RUN", offline_unknown_revocation="NOT_PROVEN",
        ios_acceptance="NOT_RUN", full_t5_acceptance="NOT_PROVEN", product_source_changes=0,
        started_at=datetime.now(timezone.utc).isoformat())
    try:
        require(re.fullmatch(r"[0-9a-f]{40}", receipt["app_sha"] or "")
                and (receipt["run_id"] or "").isdigit() and (receipt["run_attempt"] or "").isdigit(),
                "Real GitHub run/attempt/source identity required")
        execute(args, receipt)
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
    finally:
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        native.save(args.evidence / "receipt.json", receipt)
    return int(receipt["status"] != PASS)


if __name__ == "__main__":
    raise SystemExit(main())
