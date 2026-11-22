"""One composed native source, changed finalization controls and one real account.

Uses the existing pinned T2 generator, dependency setup and owned process runner.
Unchanged native methods remain bound to their original receipts; they are not
selected here. This is not an Apple, network-delivery or T2-to-T5 projection gate.
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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Tools/TorahNativeOperations"))
import run_native_rpc as rpc
import run_account_lifecycle as process_control
from authorized_read import build_apple as original_read
from authorized_read import profile as read_profile
import coherent_read_runtime as composition
import build_custom_heart
import run_t5_native_attachment as native
import run_t5_pairs_ci as modules
import t5_signed_revocation as signed

PROTOCOL = "pinkha-coherent-signed-authority-v1"
METHOD = "TestCoherentNativeReadsAfterSignedRevocation"
PASS = "PASS_COHERENT_SIGNED_AUTHORITY"
FIXTURE_DIRECTORY = "Tools/PinkhaNativeDerived/coherent_read/account"
FIXTURES = {"native_signed_revocation_base_test.go", "coherent_authority_account_test.go"}
CORE = "github.com/anyproto/anytype-heart/core"
NEW_METHODS = {
    "TestCoherentAuthorizedReadFinalizationReleasesNoRetiredPayload",
    "TestCoherentAuthorizedReadBuildsWireBeforePublication",
    "TestCoherentAuthorizedReadRejectsActiveReadLeaseBeforePublication",
    "TestCoherentAuthorizedReadMissingOwnershipFailsClosed",
    "TestCoherentAuthorizedReadNativeSuccessReleasesPublication",
}
TOP_METHODS = NEW_METHODS | set(composition.AFFECTED_PRIOR_METHODS)
TERMINALS = TOP_METHODS | {
    "TestCoherentAuthorizedReadFinalizationReleasesNoRetiredPayload/" + entry + "-" + outcome
    for entry in ("native", "wire") for outcome in ("denied", "retired", "cancelled-after-wait")
} | {
    "TestCoherentAuthorizedReadMissingOwnershipFailsClosed/" + name
    for name in ("missing-read-owner", "missing-publication", "missing-release")
}
OBSERVATION_KEYS = {
    "protocol", "nonce", "pid", "heart_sha", "runtime_version", "fixture_sha256",
    "account_id_sha256", "space_id_sha256", "object_id_sha256", "block_id_sha256",
    "canonical_sha256", "claim_id_sha256", "native_change_id_sha256", "owner_wire_sha256",
    "reader_wire_sha256", "removed_wire_sha256", "same_runtime_account_space_target", "owner_positive",
    "reader_positive", "exact_signed_bytes_and_provenance", "removed_error_code", "removed_has_payload",
    "account_stop_verified", "rpc_calls", "stages", "automatic_t2_to_t5_projection",
    "network_acl_transport", "ios_acceptance", "status",
}
RAW_FILES = {"coherent-owner.pb": "owner_wire_sha256", "coherent-reader.pb": "reader_wire_sha256",
             "coherent-removed.pb": "removed_wire_sha256"}
PUBLIC_FILES = {"ownership.json", "native-observation.json", "native.log", "coherent-observation.json", *RAW_FILES}
require, digest = composition.require, composition.digest


def source_inventory(control):
    paths = native.git(control, "ls-files", "-z", "--", "Tools/PinkhaNativeDerived", "Tools/TorahNativeOperations",
                       ".github/workflows/pinkha-coherent-heart-native.yml").decode().strip("\0").split("\0")
    return {name: digest(control / name) for name in paths if name}


def fixture_identity(control):
    directory = control / FIXTURE_DIRECTORY
    require({path.name for path in directory.glob("*.go")} == FIXTURES, "Unexpected combined account fixture source")
    baseline = composition.base.normalized((control / signed.FIXTURE).read_bytes()).decode()
    expected = baseline.replace("func TestT5NativeCachedQueriesAfterSignedRevocation(t *testing.T) {",
        "// Candidate-only fixture body. The original signed-revocation source and its\n"
        "// qualified receipt remain unchanged. Hooks run only after native ACL unlock.\n"
        "func runCoherentT5SignedRevocation(t *testing.T, hook func(stage, accountID, spaceID, objectID, blockID string)) {")
    require(expected != baseline, "Original account fixture anchor changed")
    for anchor, hook in (
        ("\trequire.Equal(t, objectID, cached.Id())\n", "\thook(\"owner\", accountID, spaceID, objectID, block.BlockId)\n"),
        ("\trequire.Same(t, cached, stillCached)\n", "\thook(\"reader\", accountID, spaceID, objectID, block.BlockId)\n"),
    ):
        require(expected.count(anchor) == 1, "Original positive account seam changed")
        expected = expected.replace(anchor, anchor + hook)
    anchor = "\t// No updater is replaced or suppressed. These are ordinary actual generated\n"
    require(expected.count(anchor) == 1, "Original unlocked removal seam changed")
    expected = expected.replace(anchor, "\thook(\"removed\", accountID, spaceID, objectID, block.BlockId)\n" + anchor)
    require(composition.base.normalized((directory / "native_signed_revocation_base_test.go").read_bytes()) == expected.encode(),
            "Candidate fixture changed original assertions beyond the three reviewed unlocked hooks")
    combined, sources = hashlib.sha256(), {}
    for name in sorted(FIXTURES):
        path = directory / name
        raw = path.read_bytes()
        combined.update(name.encode() + b"\0" + raw)
        sources[name] = digest(path)
    return combined.hexdigest(), sources


def qualify_components(log):
    events = []
    for line in log.read_text(encoding="utf8").splitlines():
        if line.startswith("{"):
            events.append(json.loads(line))
        else:
            require(not line.strip() or line.startswith("go: downloading "), "Unexpected component output")
    starts = [(value.get("Package"), value["Test"]) for value in events if value.get("Action") == "run" and value.get("Test")]
    ends = [(value.get("Package"), value["Test"]) for value in events if value.get("Action") == "pass" and value.get("Test")]
    exact = {(CORE, name) for name in TERMINALS}
    require(not any(value.get("Action") in {"fail", "skip"} for value in events), "Coherent component failed/skipped")
    require(set(starts) == set(ends) == exact and len(starts) == len(ends) == len(exact) == 18,
            "Missing, extra, repeated or wrong-package coherent component case")
    require([value.get("Package") for value in events if value.get("Action") == "pass" and not value.get("Test")] == [CORE],
            "Exact native component package did not finish")
    return {"status": "PASS_COHERENT_FINALIZATION_COMPONENTS", "top_level_pass": 9, "terminal_pass": 18,
            "new_methods": 5, "new_terminals": 14, "affected_prior_methods": 4, "affected_prior_terminals": 4,
            "fail": 0, "skip": 0, "source_scope": "Publication doubles and changed front-door guards; not a real ACL proof",
            "exact_passed": sorted(TERMINALS), "log_sha256": digest(log)}


def validate_observations(value, t5, identity, pid, nonce, private):
    require(isinstance(value, dict) and set(value) == OBSERVATION_KEYS, "Unreviewed coherent account observation schema")
    require(identity.get("runtime_profile") == composition.VARIANT
            and re.fullmatch(r"[0-9a-f]{64}", identity.get("patch_sha256", ""))
            and identity["runtime_version"] == composition.version(identity["patch_sha256"]),
            "Standalone or unbound runtime cannot qualify coherent authority")
    require(value["protocol"] == PROTOCOL and value["nonce"] == nonce and type(value["pid"]) is int
            and value["pid"] == pid > 0 and value["status"] == PASS, "Coherent process/nonce/status differs")
    require(signed.validate_observation(t5, identity, pid, nonce) == signed.PASS, "The same account T5 gate did not pass")
    for key in ("heart_sha", "runtime_version", "fixture_sha256"):
        require(value[key] == identity[key] == t5[key], "Coherent runtime/fixture binding differs: " + key)
    for key in ("account_id_sha256", "space_id_sha256", "object_id_sha256"):
        require(value[key] == t5[key], "The two native read families used different owned targets")
    for key in (name for name in value if name.endswith("_sha256")):
        require(isinstance(value[key], str) and re.fullmatch(r"[0-9a-f]{64}", value[key]), "Missing exact coherent observation hash")
    for key in ("same_runtime_account_space_target", "owner_positive", "reader_positive",
                "exact_signed_bytes_and_provenance", "account_stop_verified"):
        require(value[key] is True, "Actual shared authority assertion missing: " + key)
    require(type(value["removed_error_code"]) is int and value["removed_error_code"] in (4, 9)
            and value["removed_has_payload"] is False, "Removed T2 read did not return typed zero-payload denial/invalidation")
    require(isinstance(value["rpc_calls"], dict) and all(type(count) is int for count in value["rpc_calls"].values())
            and value["rpc_calls"] == {"PinkhaTorahOperationsAppend": 1, "PinkhaTorahAuthorizedOperationRead": 3}
            and value["stages"] == ["owner", "reader", "removed"], "Actual immutable operation journey differs")
    require(value["automatic_t2_to_t5_projection"] == "NOT_PROVEN"
            and value["network_acl_transport"] == value["ios_acceptance"] == "NOT_RUN", "Native scope was overstated")
    for name, key in RAW_FILES.items():
        require(digest(private / name) == value[key] and (private / name).stat().st_size > 0, "Actual generated wire evidence differs")
    return {"status": PASS, "same_runtime_account_space_target": True, "owner_positive": True, "reader_positive": True,
            "removed_t2_error_code": value["removed_error_code"], "removed_t2_payload": False,
            "t5_query_rows": t5["object_search_rows"], "t5_query_total": t5["object_search_total"],
            "t5_show_payload": t5["object_show_has_payload"], "t5_read_key_rotated": t5["read_key_rotated"],
            "actual_account_tests": 1, "automatic_t2_to_t5_projection": "NOT_PROVEN"}


def qualify_account(log):
    lines = log.read_text(encoding="utf8", errors="replace").splitlines()
    starts = [match.group(1) for line in lines if (match := re.fullmatch(r"=== RUN\s+(\S+)\s*", line))]
    endings = [match.groups() for line in lines if (match := re.match(r"--- (PASS|FAIL|SKIP): (\S+) \(", line))]
    require(starts == [METHOD] and endings == [("PASS", METHOD)] and "PASS" in lines,
            "Coherent account selected zero, extra, failed, skipped or incomplete methods")
    return {"method": METHOD, "tests_started": 1, "tests_passed": 1, "tests_failed": 0, "tests_skipped": 0,
            "native_log_sha256": digest(log)}


def export_private(private, evidence):
    result = signed.export_private(private, evidence)
    if result["status"] != "PASS_EXACT_ACCOUNT_SECRET_SCAN":
        return result
    needles = [value.encode() for value in json.loads((private / "sensitive-needles.private").read_bytes())]
    for name in ["coherent-observation.json", *RAW_FILES]:
        path = private / name
        if not path.exists():
            continue
        require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(private.resolve()),
                "Coherent private export escapes its owner")
        raw = path.read_bytes()
        require(not any(value in raw for value in needles), "Coherent evidence contains actual disposable credentials")
        (evidence / name).write_bytes(raw)
        result["files"][name] = digest(evidence / name)
    return result


def qualify_complete_export(result):
    require(result.get("status") == "PASS_EXACT_ACCOUNT_SECRET_SCAN" and set(result.get("files", {})) == PUBLIC_FILES,
            "A successful coherent journey requires every exact secret-scanned original output")
    require(all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) for value in result["files"].values()),
            "Successful coherent export lacks original byte hashes")


def execute(args, receipt, run):
    control, source, heart, work, evidence = [getattr(args, name) for name in ("control", "source", "heart", "work", "evidence")]
    require(len({control, source, heart, work, evidence}) == 5, "Distinct isolated native directories required")
    require(platform.system() == "Linux" and platform.machine() == "x86_64" and os.environ.get("T5_GO_IMAGE") == native.IMAGE,
            "Pinned Linux amd64 musl image required")
    require(subprocess.check_output(["go", "version"], text=True).strip() == "go version go1.26.5 linux/amd64", "Pinned Go version required")
    for tree, expected in ((control, receipt["app_sha"]), (source, signed.SOURCE)):
        require(native.git(tree, "rev-parse", "HEAD").decode().strip() == expected and not native.git(tree, "status", "--porcelain").strip(),
                "Fresh exact native/controller source required")
    require(native.git(heart, "rev-parse", "HEAD").decode().strip() == signed.HEART, "Wrong native base")
    require(not work.exists() or not any(work.iterdir()), "Refuse reused native work directory")
    work.mkdir(parents=True, exist_ok=True)
    require(shutil.disk_usage(work).free >= 8 * 1024**3, "Native disk reserve below8GiB")
    before = source_inventory(control)
    native.save(evidence / "control-source-before.json", before)
    fixture_sha, fixture_files = fixture_identity(control)
    qualified = original_read.qualified_generation(control)
    require(digest(control / "Tools/PinkhaNativeDerived/build_custom_heart.py") == signed.HELPER_SHA, "Reviewed native helper changed")
    require(digest(source / modules.GENPROTO_DECLARATION) == modules.GENPROTO_DECLARATION_SHA, "Frozen dependency declaration changed")
    # The unchanged official Linux protoc/gogo generation runs on the Ubuntu
    # host before entering musl, exactly as in the qualified T2 workflow. This
    # consumes only the same-attempt receipt and its exact 85-file output.
    generation_path = evidence / "generation/generation-receipt.json"
    generation = json.loads(generation_path.read_bytes())
    require(generation["app_sha"] == receipt["app_sha"] and generation["run_id"] == receipt["run_id"]
            and generation["run_attempt"] == receipt["run_attempt"] and generation["rpc_profile"] == read_profile.PROFILE,
            "Generation is not this exact controller/run/attempt")
    composition.validate_t2_generation(generation, qualified)
    rpc.verify_composed_source(heart, generation["source_sha256"], set(generation["tracked_paths"]), generation["module_sha256"])
    receipt["generation_receipt_sha256"] = digest(generation_path)
    receipt["phase"] = "COMPOSE_CURRENT_READ_AND_REVIEWED_DELTA"
    runtime = composition.compose(source, control, heart, work, generation, qualified, run)
    runtime.write(evidence / "runtime-source")
    inventory = json.loads(runtime.inventory)
    native.save(evidence / "runtime-source.json", dict(variant=runtime.variant, heart_sha=signed.HEART,
        patch_sha256=runtime.patch_sha256, inventory_sha256=runtime.inventory_sha256, runtime_version=runtime.version, inventory=inventory,
        app_capability="UNCHANGED", ios_acceptance="NOT_RUN"))
    applied = composition.verify_source(heart, inventory, generation["module_sha256"])
    native.save(evidence / "native-source-before.json", applied)
    private = work / "private"
    private.mkdir(mode=0o700)
    try:
        tantivy = build_custom_heart.fetch_tantivy(heart, "linux-amd64-musl")
        require(tantivy["archive_sha256"] == modules.TANTIVY, "Unexpected native Tantivy")
        native.save(evidence / "tantivy.json", tantivy)
        gowork = work / "go.work"
        gowork.write_text("go 1.26.5\n\nuse " + str(heart) + "\n\nreplace " + modules.GENPROTO_PATH
                         + " => " + modules.GENPROTO_PATH + " " + modules.GENPROTO_VERSION + "\n", encoding="utf8")
        env = dict(os.environ, GOMAXPROCS="2", CGO_ENABLED="1", GOTOOLCHAIN="local", GOFLAGS="-mod=readonly", GOWORK=str(gowork),
                   CGO_LDFLAGS="-L" + str(heart / "deps/libs/linux-amd64-musl"))
        run(["go", "mod", "download"], "download-modules", heart, env, 900)
        env["GOPROXY"] = "off"
        run(["go", "list", "-m", "-json", "all"], "resolved-modules", heart, env, 120)
        run(["go", "list", "-m", "-json", modules.GENPROTO_PATH], "genproto", heart, env, 120)
        genproto = modules.validate_genproto_selection(json.loads((evidence / "genproto.log").read_bytes()))
        ldflags = ("-extldflags=-static -X github.com/anyproto/anytype-heart/util/vcs.GitCommit=" + signed.HEART
                   + " -X github.com/anyproto/anytype-heart/util/vcs.GitSummary=" + runtime.version
                   + " -X github.com/anyproto/anytype-heart/clientlibrary/service.t5ACLFixtureSHA=" + fixture_sha)
        receipt["phase"] = "ONLY_CHANGED_FINALIZATION_COMPONENTS"
        run(["go", "test", "-p", "1", "-parallel", "1", "-count=1", "-timeout=120s", "-json", "-tags", modules.TAGS,
             "-ldflags", ldflags, "-run", "^(" + "|".join(sorted(TOP_METHODS)) + ")$", "./core"],
            "coherent-components", heart, env, 1800)
        receipt["components"] = qualify_components(evidence / "coherent-components.log")
        native.save(evidence / "component-receipt.json", receipt["components"])
        overlay = work / "account-overlay.json"
        native.save(overlay, {"Replace": {str(heart / "clientlibrary/service" / name): str(control / FIXTURE_DIRECTORY / name)
                                          for name in sorted(FIXTURES)}})
        require(all(not (heart / "clientlibrary/service" / name).exists() for name in FIXTURES), "Account fixture would replace native source")
        binary = work / "pinkha-coherent-authority.test"
        receipt["phase"] = "ONE_COMBINED_ACCOUNT_BINARY_BUILD"
        run(["go", "test", "-c", "-p", "1", "-tags", modules.TAGS, "-overlay", str(overlay), "-ldflags", ldflags,
             "-o", str(binary), "./clientlibrary/service"], "compile-native-fixture", heart, env, 1800)
        identity = dict(heart_sha=signed.HEART, runtime_version=runtime.version, fixture_sha256=fixture_sha,
                        fixture_source_sha256=fixture_files, binary_sha256=digest(binary), app_sha=receipt["app_sha"], genproto=genproto,
                        patch_sha256=runtime.patch_sha256, inventory_sha256=runtime.inventory_sha256,
                        runtime_profile=composition.VARIANT, overlay=json.loads(overlay.read_bytes()))
        native.save(evidence / "build.json", identity)
        nonce = uuid4().hex
        native.save(private / "ownership.json", dict(protocol=signed.PROTOCOL, nonce=nonce, synthetic_only=True))
        account_root = private / "account-root"
        account_root.mkdir(mode=0o700)
        env.update(PINKHA_T5_ACL_ROOT=str(account_root), PINKHA_T5_ACL_REPORT=str(private / "native-observation.json"),
                   PINKHA_T5_ACL_NONCE=nonce, PINKHA_T5_ACL_OWNERSHIP=(private / "ownership.json").read_text(),
                   PINKHA_T5_ACL_FIXTURE_SHA256=fixture_sha, PINKHA_T5_ACL_RUNTIME_VERSION=runtime.version)
        receipt["phase"] = "ONE_ACTUAL_COMPOSED_SIGNED_ACCOUNT_JOURNEY"
        command = [str(binary), "-test.run", "^" + METHOD + "$", "-test.count=1", "-test.v", "-test.timeout=300s"]
        # The existing owner-scoped process runner kills only this session group
        # on cancellation/timeout and preserves its exact private output.
        pid = process_control.run_process(command, private, env, private / "native.log", 330)
        receipt["execution"] = dict(command=command, pid=pid, exit_code=0)
        require(digest(binary) == identity["binary_sha256"], "Composed native binary changed during execution")
        coherent = json.loads((private / "coherent-observation.json").read_bytes())
        t5 = json.loads((private / "native-observation.json").read_bytes())
        receipt["actual"] = validate_observations(coherent, t5, identity, pid, nonce, private)
        receipt["named_account_test"] = qualify_account(private / "native.log")
        receipt.update(status=PASS, phase="COMPLETE", runtime_profile=composition.VARIANT,
                       patch_sha256=runtime.patch_sha256, inventory_sha256=runtime.inventory_sha256,
                       original_t2_unaffected_terminals_retained=67, original_current_read_components_retained=2,
                       actual_top_level_methods=10, actual_terminal_cases=19, actual_fail=0, actual_skip=0)
    finally:
        receipt["evidence_export"] = export_private(private, evidence / "actual")
        if receipt.get("status") == PASS:
            qualify_complete_export(receipt["evidence_export"])
        require(source_inventory(control) == before, "Controller/fixture source changed during execution")
        after = composition.verify_source(heart, inventory, generation["module_sha256"])
        require(after == applied, "Composed source changed during native proof")
        native.save(evidence / "control-source-after.json", source_inventory(control))
        native.save(evidence / "native-source-after.json", after)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("control", "source", "heart", "work", "evidence"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    for name in ("control", "source", "heart", "work", "evidence"):
        setattr(args, name, getattr(args, name).resolve())
    args.evidence.mkdir(parents=True, exist_ok=True)
    receipt_path = args.evidence / "receipt.json"
    require(not receipt_path.exists(), "Refuse an existing composed attempt receipt")
    receipt = dict(status="NOT_RUN", phase="SOURCE_PREFLIGHT", runtime_profile=composition.VARIANT,
        run_id=os.environ.get("GITHUB_RUN_ID"), run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"), app_sha=os.environ.get("GITHUB_SHA"),
        commands=[], started_at=datetime.now(timezone.utc).isoformat(), ios_acceptance="NOT_RUN",
        network_acl_transport="NOT_RUN", automatic_t2_to_t5_projection="NOT_PROVEN")
    cancelled = False
    previous = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT)}
    def cancel(number, frame):
        nonlocal cancelled
        if not cancelled:
            cancelled = True
            raise KeyboardInterrupt(signal.Signals(number).name)
    for number in previous:
        signal.signal(number, cancel)
    def run(command, name, cwd, env, timeout=900):
        entry = dict(name=name, argv=list(map(str, command)), status="RUNNING")
        receipt["commands"].append(entry)
        native.save(receipt_path, receipt)
        path = args.evidence / (name + ".log")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            entry["pid"] = process_control.run_process(entry["argv"], cwd, env, path, timeout)
            entry["status"] = "PASS_EXIT_0"
        except BaseException as error:
            entry["status"] = "CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL"
            raise
        finally:
            native.save(receipt_path, receipt)
    try:
        require(re.fullmatch(r"[0-9a-f]{40}", receipt["app_sha"] or "")
                and (receipt["run_id"] or "").isdigit() and (receipt["run_attempt"] or "").isdigit(), "Real GitHub source/run/attempt required")
        execute(args, receipt, run)
    except BaseException as error:
        receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL", error_type=type(error).__name__, error=str(error))
    finally:
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        native.save(receipt_path, receipt)
        for number, handler in previous.items():
            signal.signal(number, handler)
    return int(receipt["status"] != PASS)


if __name__ == "__main__":
    raise SystemExit(main())
