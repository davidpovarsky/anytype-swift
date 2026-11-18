"""Build pinned r14/r15 native RPC binaries for a same-account/export sequence."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import run_t5_coverage_ci as coverage
import run_t5_pairs_ci as store_ci

ACCOUNT_DIRECTORY = "Tools/PinkhaNativeDerived/account_pairs"


def validate_account_result(result, include_freshness=False):
    reports = result.get("phase_reports", [])
    total = 5 if include_freshness else 4
    counts = dict(binaries=2, native_processes=total, passing_test_invocations=total, actual_export_files=24)
    if (result.get("status") != "NATIVE_ACCOUNT_PAIR_PASS"
            or result.get("actual_counts") != counts
            or result.get("export_status") != "ACTUAL_JSON_AND_PROTOBUF"
            or result.get("swift_pairing_status") != "NOT_RUN"
            or result.get("full_F10") != "NOT_PROVEN"
            or result.get("client_enablement") != store_ci.CLIENT_DISABLED
            or [report.get("phase") for report in reports] != store_ci.PHASES
            or any(report.get("closed") is not True or report.get("test_passed") is not True
                   or report.get("account_stop_completed") is not True or report.get("application_cleared") is not True
                   for report in reports)):
        raise RuntimeError("Actual native account receipt incomplete or overstates Apple acceptance")
    pids = [report.get("pid") for report in reports]
    if len(set(pids)) != 4 or any(type(pid) is not int or pid <= 0 for pid in pids):
        raise RuntimeError("Four distinct completed actual native process identities required")
    if result.get("include_freshness", False) is not include_freshness:
        raise RuntimeError("Controller freshness mode differs from the requested route")
    freshness = result.get("freshness_report")
    if include_freshness:
        if (not isinstance(freshness, dict)
                or result.get("freshness_status") != "PASS_NATIVE_RPC_MUTATIONS"
                or freshness.get("freshness_status") != "PASS_NATIVE_RPC_MUTATIONS"
                or freshness.get("phase") != "new-freshness"
                or len(freshness.get("checks", [])) != 16
                or freshness.get("coverage") != "indexedTargetsOnly"
                or freshness.get("space_wide_freshness") != "NOT_PROVEN"
                or freshness.get("host_target_exclusion_status") != "NOT_RUN_SWIFT_HOST"
                or freshness.get("swift_pairing_status") != "NOT_RUN"
                or freshness.get("client_enablement") != store_ci.CLIENT_DISABLED
                or any(freshness.get(key) is not True for key in
                       ["closed", "test_passed", "account_stop_completed", "application_cleared"])
                or any(freshness.get(key) != reports[-1].get(key) for key in
                       ["protocol", "heart_sha", "patch_sha256", "fixture_sha256", "runtime_version",
                        "account_root", "account_id", "space_id", "state_sha256"])):
            raise RuntimeError("Optional same-account native freshness process missing or overstates coverage")
        pids.append(freshness.get("pid"))
        nonces = [report.get("nonce") for report in reports] + [freshness.get("nonce")]
        if (len(set(pids)) != total or any(type(pid) is not int or pid <= 0 for pid in pids)
                or len(set(nonces)) != total
                or any(not isinstance(nonce, str) or not nonce for nonce in nonces)):
            raise RuntimeError("Fifth native process/nonce must be distinct and source-bound")
    elif freshness is not None or result.get("freshness_status", "NOT_REQUESTED") != "NOT_REQUESTED":
        raise RuntimeError("Unrequested freshness cannot silently widen the four-process receipt")
    return counts


def execute(args, control, evidence):
    if os.name != "posix":
        raise RuntimeError("Actual native account pairing requires Linux CI")
    identity = coverage.require_identity(control)
    source = args.source.resolve()
    hearts = {"old": args.heart_old.resolve(), "new": args.heart_new.resolve()}
    work, artifacts = args.work.resolve(), args.artifacts.resolve()
    paths = [control, source, *hearts.values(), work, artifacts, evidence]
    if len(set(paths)) != len(paths):
        raise RuntimeError("Separate control/source/native/work/artifact/evidence directories required")
    for tree, pin in [(control, identity["integration_sha"]), (source, coverage.SOURCE),
                      *[(heart, coverage.HEART) for heart in hearts.values()]]:
        if coverage.git(tree, "rev-parse", "HEAD") != pin or coverage.git(tree, "status", "--porcelain"):
            raise RuntimeError("Exact clean fresh checkout required: " + str(tree))
    frozen = dict(coverage.HASHES)
    frozen[store_ci.GENPROTO_DECLARATION] = store_ci.GENPROTO_DECLARATION_SHA
    frozen[store_ci.APPROVAL_ROOT + "/revision-14/native-heart-integration.patch"] = store_ci.OLD_PATCH
    frozen[store_ci.APPROVAL_ROOT + "/revision-14/native-heart-integration.json"] = store_ci.OLD_INVENTORY
    for path, expected in frozen.items():
        if coverage.digest(source / path) != expected:
            raise RuntimeError("Reviewed source input differs: " + path)
    store_ci.verify_pair_inputs(control)
    version = subprocess.check_output(["go", "version"], text=True).strip()
    if version != "go version go1.26.5 linux/amd64":
        raise RuntimeError("Expected exact Linux Go 1.26.5")
    if shutil.disk_usage(work).free < 8 * 1024**3:
        raise RuntimeError("Disk reserve below 8 GiB")
    build_root = work / "build"
    build_root.mkdir(exist_ok=False)
    artifacts.mkdir(parents=True, exist_ok=True)
    if any(artifacts.iterdir()):
        raise RuntimeError("Fresh empty binary artifact directory required")
    commands = []

    def run(command, name, cwd=source, env=None, timeout=900):
        commands.append(dict(name=name, argv=[str(value) for value in command], cwd=str(cwd),
                             environment={key: (env or os.environ).get(key) for key in
                                          ["GOWORK", "GOFLAGS", "GOPROXY", "GOTOOLCHAIN", "GOMAXPROCS",
                                           "CGO_ENABLED", "CGO_LDFLAGS", "CC", "CXX"]}))
        coverage.write_receipt(evidence / "commands.json", commands)
        with (evidence / (name + ".log")).open("x", encoding="utf8") as log:
            result = subprocess.run(command, cwd=cwd, env=env, stdout=log,
                                    stderr=subprocess.STDOUT, timeout=timeout)
        if result.returncode:
            raise RuntimeError(name + " failed; see retained log")

    helper_path = source / "Tools/PinkhaNativeDerived/build_custom_heart.py"
    native_helper = store_ci.load_module("account_native_builder", helper_path)
    pair_root = control / ACCOUNT_DIRECTORY
    account = store_ci.load_module("native_account_pair_controller", pair_root / "run_account_pairs.py")
    fixture = pair_root / "account_pair_phase_test.go"
    fixture_sha = coverage.digest(fixture)
    fixture_inputs = {name: coverage.digest(pair_root / name) for name in
                      ["account_pair_phase_test.go", "run_account_pairs.py", "test_controls.py", "test_freshness_controls.py"]}
    run([sys.executable, "-B", "-m", "unittest", "discover", "-s", str(pair_root), "-p", "test_*controls.py", "-v"],
        "account-controller-controls", cwd=pair_root)
    manifest = {"schema": 1, "protocol": account.PROTOCOL, "include_freshness": args.include_freshness}
    verified_builds = {}
    for role, revision in [("old", 14), ("new", 15)]:
        heart = hearts[role]
        approval = source / store_ci.APPROVAL_ROOT / ("revision-" + str(revision))
        patch, inventory = approval / "native-heart-integration.patch", approval / "native-heart-integration.json"
        patch_sha = store_ci.OLD_PATCH if role == "old" else coverage.PATCH
        run([sys.executable, "-B", str(helper_path), "--heart-source", str(heart),
             "--patch", str(patch), "--inventory", str(inventory),
             "--approved-patch-sha256", patch_sha, "--apply-approved-patch",
             "--target", "verify", "--evidence", str(evidence / (role + "-source"))],
            role + "-source-preflight")
        tantivy = native_helper.fetch_tantivy(heart, "linux-amd64-musl")
        if tantivy["archive_sha256"] != store_ci.TANTIVY:
            raise RuntimeError("Unexpected pinned Tantivy artifact")
        role_work = build_root / role
        role_work.mkdir()
        gowork = role_work / "go.work"
        gowork.write_text("go 1.26.5\n\nuse " + str(heart) + "\n\nreplace "
                          + store_ci.GENPROTO_PATH + " => " + store_ci.GENPROTO_PATH
                          + " " + store_ci.GENPROTO_VERSION + "\n", encoding="utf8")
        destination = heart / "clientlibrary/service/pinkha_t5_account_pair_phase_test.go"
        if destination.exists():
            raise RuntimeError("Account fixture overlay would replace native source")
        overlay = role_work / "overlay.json"
        overlay.write_text(json.dumps({"Replace": {str(destination): str(fixture)}}) + "\n", encoding="utf8")
        env = dict(os.environ, GOWORK=str(gowork), GOTOOLCHAIN="local", CGO_ENABLED="1",
                   GOMAXPROCS="2", GOFLAGS="-mod=readonly",
                   CGO_LDFLAGS="-L" + str(heart / "deps/libs/linux-amd64-musl"))
        run(["go", "mod", "download"], role + "-pinned-module-download", cwd=heart, env=env)
        env["GOPROXY"] = "off"
        run(["go", "list", "-m", "-json", "all"], role + "-resolved-modules", cwd=heart, env=env)
        run(["go", "list", "-m", "-json", store_ci.GENPROTO_PATH], role + "-genproto-selection",
            cwd=heart, env=env)
        selected = json.loads((evidence / (role + "-genproto-selection.log")).read_text(encoding="utf8"))
        genproto = store_ci.validate_genproto_selection(selected)
        summary = account.runtime_version(role)
        ldflags = ("-extldflags=-static"
                   " -X github.com/anyproto/anytype-heart/util/vcs.GitCommit=" + coverage.HEART
                   + " -X github.com/anyproto/anytype-heart/util/vcs.GitSummary=" + summary
                   + " -X github.com/anyproto/anytype-heart/clientlibrary/service.accountPairFixtureSHA=" + fixture_sha)
        binary = artifacts / ("pinkha-r" + str(revision) + "-native-account.test")
        run(["go", "test", "-c", "-p", "1", "-tags", store_ci.TAGS, "-overlay", str(overlay),
             "-ldflags", ldflags, "-o", str(binary), "./clientlibrary/service"],
            role + "-compile", cwd=heart, env=env)
        entry = dict(binary=str(binary), binary_sha256=account.digest(binary),
                     source=str(heart), inventory=str(inventory), patch=str(patch), fixture_sha256=fixture_sha)
        verified = account.verify_artifact(role, entry)
        manifest[role] = entry
        verified_builds[role] = verified
        coverage.write_receipt(evidence / (role + "-build.json"),
                               dict(status="BINARY_BUILT_SOURCE_VERIFIED", **verified, go_version=version,
                                    linked_summary=summary, tantivy=tantivy, genproto_resolution=genproto,
                                    overlay=json.loads(overlay.read_text()), gowork=gowork.read_text()))
    manifest_path = evidence / "manifest.json"
    coverage.write_receipt(manifest_path, manifest)
    workspace = work / "account-sequence"
    try:
        run([sys.executable, "-B", str(pair_root / "run_account_pairs.py"),
             "--manifest", str(manifest_path), "--workspace", str(workspace)],
            "native-account-controller", cwd=control,
            env=dict(os.environ, GOTOOLCHAIN="local", GOPROXY="off", GOMAXPROCS="2"), timeout=1800 if args.include_freshness else 1500)
    finally:
        if workspace.is_dir():
            copy_receipt = account.preserve_evidence(workspace, evidence / "account-sequence", args.include_freshness)
            coverage.write_receipt(evidence / "evidence-copy.json", copy_receipt)
    result_path = evidence / "account-sequence/result.json"
    result = json.loads(result_path.read_text(encoding="utf8"))
    counts = validate_account_result(result, args.include_freshness)
    store_ci.verify_pair_inputs(control)
    if coverage.require_identity(control) != identity or coverage.git(source, "status", "--porcelain"):
        raise RuntimeError("Source/control identity changed during actual account pairing")
    for path, expected in frozen.items():
        if coverage.digest(source / path) != expected:
            raise RuntimeError("Frozen source changed: " + path)
    for name, expected in fixture_inputs.items():
        if coverage.digest(pair_root / name) != expected:
            raise RuntimeError("Account test/controller changed: " + name)
    for role in hearts:
        if (account.verify_artifact(role, manifest[role]) != verified_builds[role]
                or result["identities"][role] != verified_builds[role]):
            raise RuntimeError("Native binary/source changed after account sequence")
    return dict(status=account.STATUS, **identity, source_sha=coverage.SOURCE,
                heart_sha=coverage.HEART, fixture_inputs=fixture_inputs, actual_counts=counts,
                binary_sha256={role: manifest[role]["binary_sha256"] for role in hearts},
                account_receipt_sha256=coverage.digest(result_path), go_version=version,
                export_status="ACTUAL_JSON_AND_PROTOBUF", include_freshness=args.include_freshness,
                freshness_status=result["freshness_status"],
                host_target_exclusion_status="NOT_RUN_SWIFT_HOST", space_wide_freshness="NOT_PROVEN")


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    for name in ["source", "heart-old", "heart-new", "work", "artifacts", "evidence"]:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--include-freshness", action="store_true")
    args = parser.parse_args(argv)
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=False)
    receipt = dict(status="RUNNING", started_at=datetime.now(timezone.utc).isoformat(),
                   component="index-freshness" if args.include_freshness else "account-pairs", full_F10="NOT_PROVEN", export_status="NOT_RUN",
                   swift_pairing_status="NOT_RUN", client_enablement=store_ci.CLIENT_DISABLED,
                   scope="two exact Linux RPC binaries reopen one synthetic account in four compatibility processes"
                         + (" followed by a fifth native mutation process; Swift target exclusion NOT_RUN" if args.include_freshness else ""))
    path = evidence / "ci-result.json"
    coverage.write_receipt(path, receipt)
    try:
        receipt.update(execute(args, Path(__file__).resolve().parents[2], evidence))
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
    receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
    coverage.write_receipt(path, receipt)
    print(json.dumps(receipt))
    return 0 if receipt["status"] == "NATIVE_ACCOUNT_PAIR_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
