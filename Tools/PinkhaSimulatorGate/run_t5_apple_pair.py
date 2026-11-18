"""Run the same app source with verified r14/r15 on one fresh OS27 account.

Only this job's compile commands enable the lookup flag. Product enablement and
the wider UI/freshness acceptance remain separate. Native logs stay private
until checked against both disposable credentials; app data is never uploaded.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import zipfile
from uuid import uuid4

PROTOCOL = "pinkha-t5-apple-runtime-pair-v1"
METHOD = "TorahT5RuntimePairTests/realSameAccountRuntimePairPhase"
PHASES = [("old-create", "old"), ("new-upgrade", "new"),
          ("old-edit", "old"), ("new-recover", "new")]
HEART = "d98420b1113536afd08cde6de9a5816f6d27ffff"
NATIVE_SOURCE = "947fbde24d5657d0e1229f45bb3993648884a8a1"
PATCHES = {
    "old": "fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077",
    "new": "5a0906158569d47642d9fc978932cdf254550a31c864a1fb34bd1f8e4e7c10f2",
}
INVENTORIES = {
    "old": "952073d8dccc991f21bffe5d3ded4e1d5369bb2c30f247ae5204d47cb03aee14",
    "new": "f0e4a4c2d1b4c1baa11347362cfd18368ad272a8902b2beaf8de52270f809ee7",
}
OLD_RUN = "44203168617"
OLD_ARTIFACT = 14383247626
BUILDER_SHA = "0ebbe2f6227418eac2c532b0058290158319ba9f786baaf445de444887e8c669"
APPROVAL = "docs/pinkha/torah-integration/evidence/native-derived/8494cfb347/approval"
BUNDLE = "io.anytype.app"
FLAGS = [
    "OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED -D PINKHA_NATIVE_T5_LOOKUP_V1",
    "ENABLE_TESTABILITY=YES", "ONLY_ACTIVE_ARCH=YES", "SWIFT_OPTIMIZATION_LEVEL=-Onone",
    "CODE_SIGN_IDENTITY=-", "CODE_SIGNING_ALLOWED=YES", "CODE_SIGNING_REQUIRED=YES",
    "PROVISIONING_PROFILE_SPECIFIER=",
]
SLICE_IDENTITIES = {
    ("ios-arm64/Lib.framework/Lib", "arm64"),
    ("ios-arm64_x86_64-simulator/Lib.framework/Lib", "arm64"),
    ("ios-arm64_x86_64-simulator/Lib.framework/Lib", "x86_64"),
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def digest(path, normalize=False):
    if normalize:
        return sha_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def is_digest(value):
    return isinstance(value, str) and re.fullmatch("[a-f0-9]{64}", value) is not None


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf8")
    temporary.replace(path)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def runtime_version(role):
    value = "v0.51.7-nightly.20261014.1-pinkha-native-derived-v1-" + PATCHES[role]
    return value + "-pinkha-native-t5-lookup-v1-" + PATCHES[role] if role == "new" else value


def target_key(value):
    return value["objectID"], value.get("blockID") or ""


def validate_ledger(ledger, token, source, phase):
    require(ledger.get("token") == token and ledger.get("appSourceSHA") == source, "Foreign ledger owner/source")
    for key in ["rootPathSHA256", "manifestSHA256"]:
        require(is_digest(ledger.get(key)), "Invalid original ledger digest")
    for key in ["accountID", "spaceID", "manifestID", "canonicalKey"]:
        require(isinstance(ledger.get(key), str) and ledger[key], "Missing original native identity")
    expected_phases = [name for name, _ in PHASES[:[name for name, _ in PHASES].index(phase) + 1]]
    require(ledger.get("completedPhases") == expected_phases, "Actual persisted phase sequence differs")
    documents = ledger.get("documents", [])
    require(len(documents) == 3 and len({item.get("objectID") for item in documents}) == 3,
            "Three distinct original native documents required")
    require(documents[0].get("typeKey") == "ot-page" and documents[1].get("typeKey") == "ot-note"
            and documents[2].get("typeKey") not in [None, "", "ot-page", "ot-note"],
            "Actual Page, Note and custom Type fixture required")
    require(documents[0].get("blockID") is None and documents[0].get("blockText") is None,
            "The first target must be document context only")
    blocks = [item.get("blockID") for item in documents[1:]]
    require(all(isinstance(value, str) and value for value in blocks) and len(set(blocks)) == 2,
            "Two distinct original block identities required")
    for item in documents:
        require(isinstance(item.get("objectID"), str) and item["objectID"]
                and isinstance(item.get("initialName"), str), "Missing actual initial document details")
        require(is_digest(item.get("canonicalSHA256")) and is_digest(item.get("publicSHA256")),
                "Missing original canonical/public baseline")
    return documents


def validate_phase(report, phase, role, token, nonce, source, ledger, ledger_sha, prior=None):
    documents = validate_ledger(ledger, token, source, phase)
    require(report.get("protocolVersion") == PROTOCOL and report.get("status") == "PASS"
            and report.get("phase") == phase and report.get("token") == token
            and report.get("nonce") == nonce and report.get("appSourceSHA") == source,
            "Stale or foreign actual Apple phase receipt")
    require(type(report.get("processID")) is int and report["processID"] > 0, "Actual host process identity missing")
    require(report.get("runtimeVersion") == runtime_version(role), "Actual AppGetVersion differs from installed revision")
    expanded = role == "new"
    require(report.get("actualCapability") == ("verified" if expanded else "unavailable"),
            "Production runtime capability differs; fixture roles must not grant capability")
    require(report.get("coverage") == ("indexedTargetsOnly" if expanded else "indexedDocumentsOnly"),
            "Actual Swift lookup coverage differs")
    expected_limits = {"indexFreshnessUnverified"}
    if not expanded:
        expected_limits |= {"blockAssociationsNotIndexed", "sourceQuotesNotIndexed"}
    require(set(report.get("limitations", [])) == expected_limits, "Actual coverage disclosure changed or widened")
    for key in ["rootPathSHA256", "accountID", "spaceID", "manifestID", "manifestSHA256", "canonicalKey"]:
        require(report.get(key) == ledger[key], "Original account, root, Space or manifest changed")
    require(report.get("nextLedgerSHA256") == ledger_sha, "Receipt does not bind the actual persisted ledger")
    require(report.get("previousLedgerSHA256") == (prior["nextLedgerSHA256"] if prior else None),
            "Broken native process/ledger chain")
    if prior:
        for key in ["rootPathSHA256", "accountID", "spaceID", "manifestID", "manifestSHA256", "canonicalKey"]:
            require(report[key] == prior[key], "Prior native account or manifest identity changed")
        preserved = ["objectID", "canonicalSHA256", "publicSHA256", "blockID", "blockTextSHA256"]
        require([[item.get(key) for key in preserved] for item in report.get("documents", [])]
                == [[item.get(key) for key in preserved] for item in prior["documents"]],
                "A later ledger attempted to redefine the original canonical/public/block baseline")
    for key in ["accountStopCompleted", "accountNotRunningConfirmed", "appShutdownCompleted"]:
        require(report.get(key) is True, "Native account stop/readback boundary was not proven")
    initial = phase == "old-create"
    for key in ["walletCreated", "accountCreated"]:
        require(report.get(key) is initial, "A later phase recreated a native account")
    for key in ["walletRecovered", "accountSelected"]:
        require(report.get(key) is (not initial), "The original native account was not recovered/selected")
    require(type(report.get("migrationPerformed")) is bool
            and (not initial or report["migrationPerformed"] is False), "Invalid migration observation")
    readbacks = report.get("documents", [])
    require(len(readbacks) == 3 and [item.get("objectID") for item in readbacks]
            == [item["objectID"] for item in documents], "Actual live native readbacks are incomplete")
    for index, (item, original) in enumerate(zip(readbacks, documents)):
        for key in ["canonicalSHA256", "publicSHA256", "blockID"]:
            require(item.get(key) == original.get(key), "Canonical, public projection, or actual block changed")
        expected_text = sha_bytes(original["blockText"].encode()) if original.get("blockID") else None
        require(item.get("blockTextSHA256") == expected_text, "Actual block text was not preserved")
        if expanded:
            require(type(item.get("nativeRelatedVersion")) is int and item["nativeRelatedVersion"] == 1,
                    "New native private projection did not recover")
        expected_name = ("T5 ordinary edit by r14" if index == 0 and phase in ["old-edit", "new-recover"]
                         else original["initialName"])
        require(item.get("title") == expected_name, "Actual initial title or ordinary old-runtime edit was lost")
    expected = [dict(objectID=item["objectID"], blockID=item.get("blockID") if expanded else None,
                     canUnlink=item.get("blockID") is None) for item in documents[:3 if expanded else 1]]
    targets = report.get("targets", [])
    require(len(targets) == len(expected) and
            sorted([dict(objectID=item.get("objectID"), blockID=item.get("blockID"),
                         canUnlink=item.get("canUnlink")) for item in targets], key=target_key)
            == sorted(expected, key=target_key), "Actual app lookup returned the wrong native targets")


def validate_xcresult(summary, methods, udid):
    normalized = {name.removesuffix("()"): outcome for name, outcome in methods.items()}
    require(all(type(summary.get(key)) is int for key in ["passedTests", "failedTests", "skippedTests"])
            and summary.get("passedTests") == 1 and summary.get("failedTests") == 0
            and summary.get("skippedTests") == 0 and normalized == {METHOD: "Passed"},
            "Exactly one actual named Swift test must pass without skips")
    devices = [item.get("device", {}) for item in summary.get("devicesAndConfigurations", [])]
    require(devices and all(item.get("deviceId", "").lower() == udid.lower()
            and item.get("osVersion", "").split(".")[0] == "27"
            and item.get("architecture") == "arm64" for item in devices),
            "Actual XCTest device/architecture/runtime differs")


def validate_sequence(reports, build_receipts):
    require([report.get("phase") for report in reports] == [name for name, _ in PHASES],
            "All four actual Apple phases are required")
    pids = [report["processID"] for report in reports]
    nonces = [report["nonce"] for report in reports]
    require(len(set(pids)) == 4 and len(set(nonces)) == 4, "Four distinct native processes/nonces required")
    for key in ["appSourceSHA", "token", "rootPathSHA256", "accountID", "spaceID", "manifestID", "manifestSHA256", "canonicalKey"]:
        require(len({report[key] for report in reports}) == 1, "Native account/source continuity was lost")
    preserved = ["objectID", "canonicalSHA256", "publicSHA256", "blockID", "blockTextSHA256"]
    baseline = [[item.get(key) for key in preserved] for item in reports[0]["documents"]]
    for report in reports:
        require([[item.get(key) for key in preserved] for item in report["documents"]] == baseline,
                "Original native canonical/public/block observations changed between processes")
    require(set(build_receipts) == {"old", "new"}, "Both packaged applications must be built")
    old, new = build_receipts["old"], build_receipts["new"]
    for key in ["app_source_sha", "package_lock_hashes", "hanlin_snapshot_sha256", "kit_sha", "flags"]:
        require(old.get(key) == new.get(key), "The two apps used different source, dependencies or flags")
    require(old.get("flags") == FLAGS, "Test-only build flags differ")
    require(old.get("code_sha256") != new.get("code_sha256"), "The supposedly different packaged runtimes are identical")
    for role in ["old", "new"]:
        require(build_receipts[role].get("runtime_version") == runtime_version(role), "Packaged runtime pairing differs")
    return dict(app_builds=2, actual_native_processes=4, named_swift_tests_passed=4, failed=0, skipped=0)


def run_logged(argv, cwd, directory, name, timeout, check=True, output=None):
    directory.mkdir(parents=True, exist_ok=True)
    log_path = output or directory / (name + ".log")
    require(not log_path.exists(), "Refuse stale command output")
    metadata = dict(argv=[str(item) for item in argv], cwd=str(cwd),
                    started_at=datetime.now(timezone.utc).isoformat(), timeout_seconds=timeout)
    env = dict(os.environ, GH_PROMPT_DISABLED="1")
    env.pop("GH_DEBUG", None)
    with log_path.open("xb") as stream:
        process = subprocess.Popen(argv, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                                   env=env, start_new_session=True)
        metadata["controller_process_id"] = process.pid
        try:
            metadata["return_code"] = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            metadata["timed_out"] = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
            metadata["return_code"] = process.returncode
    metadata["finished_at"] = datetime.now(timezone.utc).isoformat()
    write(directory / (name + ".command.json"), metadata)
    if check:
        require(metadata["return_code"] == 0 and not metadata.get("timed_out"), name + " failed; original private output retained")
    return metadata, log_path


def download_runtime(role, run_id, work, proof, repo):
    require(run_id.isdigit() and (role != "old" or run_id == OLD_RUN), "Explicit original runtime run IDs required")
    directory = work / ("runtime-" + role)
    directory.mkdir()
    def api(endpoint, name):
        output = directory / (name + ".json")
        run_logged(["gh", "api", "repos/" + repo + "/" + endpoint], work, directory, name, 120, output=output)
        return json.loads(output.read_text(encoding="utf8"))
    run = api("actions/runs/" + run_id, "source-run")
    require(str(run.get("id")) == run_id and run.get("status") == "completed"
            and run.get("conclusion") == "success", "Original runtime build did not complete successfully")
    response = api("actions/runs/" + run_id + "/artifacts?per_page=100", "artifact-list")
    name = "Pinkha-Universal-Verified-Heart-r" + ("14" if role == "old" else "15")
    matches = [item for item in response.get("artifacts", []) if item.get("name") == name]
    require(len(matches) == 1, "Exactly one original runtime artifact is required")
    artifact = matches[0]
    require(not artifact.get("expired") and (role != "old" or artifact.get("id") == OLD_ARTIFACT)
            and artifact.get("workflow_run", {}).get("head_sha") == run.get("head_sha"),
            "Runtime artifact has the wrong source identity")
    expected_digest = artifact.get("digest", "").removeprefix("sha256:")
    require(is_digest(expected_digest), "Original artifact digest is unavailable")
    archive = directory / "original-github-artifact.zip"
    run_logged(["gh", "api", "repos/" + repo + "/actions/artifacts/" + str(artifact["id"]) + "/zip"],
               work, directory, "download-original-artifact", 300, output=archive)
    require(digest(archive) == expected_digest and archive.stat().st_size == artifact.get("size_in_bytes"),
            "Downloaded original artifact bytes differ")
    tar_name = name + ".tar.gz"
    with zipfile.ZipFile(archive) as zipped:
        require(zipped.namelist() == [tar_name], "Unexpected runtime artifact payload")
        zipped.extract(tar_name, directory)
    proof.mkdir(parents=True)
    for filename in ["source-run.json", "artifact-list.json"]:
        shutil.copyfile(directory / filename, proof / filename)
    write(proof / "download.json", dict(source_run_id=run_id, artifact_id=artifact["id"],
          artifact_sha256=expected_digest, runtime_archive_sha256=digest(directory / tar_name),
          original_source_sha=run["head_sha"], runtime_archive_bytes=(directory / tar_name).stat().st_size))
    return directory / tar_name, run


def install_runtime(role, archive, source_run, app, native_source, work, proof, helper):
    revision = "14" if role == "old" else "15"
    approval = native_source / APPROVAL / ("revision-" + revision)
    patch = approval / "native-heart-integration.patch"
    inventory_path = approval / "native-heart-integration.json"
    require(digest(patch, True) == PATCHES[role] and digest(inventory_path, True) == INVENTORIES[role],
            "Immutable native patch or inventory differs")
    inventory = json.loads(inventory_path.read_text(encoding="utf8"))
    require(inventory.get("heart_sha") == HEART and inventory.get("patch_sha256") == PATCHES[role],
            "Unexpected native source pin")
    staging = work / ("unpacked-" + role)
    staging.mkdir()
    with tarfile.open(archive) as packed:
        packed.extractall(staging, filter="data")
    require({path.name for path in staging.iterdir()} == {"Lib.xcframework", "PinkhaNativeHeartBuild.json"},
            "Unexpected native runtime archive content")
    framework = staging / "Lib.xcframework"
    receipt = json.loads((staging / "PinkhaNativeHeartBuild.json").read_text(encoding="utf8"))
    require(receipt.get("status") == "PASS" and receipt.get("target") == "ios"
            and receipt.get("heart_sha") == HEART and receipt.get("patch_sha256") == PATCHES[role]
            and receipt.get("files") == inventory["files"], "Artifact does not bind the exact native inventory")
    if role == "new":
        require(receipt.get("source_sha") == NATIVE_SOURCE
                and receipt.get("integration_sha") == source_run["head_sha"]
                and receipt.get("helper_sha256") == BUILDER_SHA
                and receipt.get("expected_app_get_version") == runtime_version(role)
                and receipt.get("app_get_version_status") == "NOT_RUN_BUILD_ONLY"
                and receipt.get("native_test_invocations") == 0,
                "r15 build-only runtime provenance is incomplete")
    entries = receipt.get("artifacts", [])
    paths = [item.get("path") for item in entries]
    require(len(paths) == len(set(paths)), "Duplicate native artifact paths")
    actual_paths = {str(path.relative_to(framework)) for path in framework.rglob("*") if path.is_file()}
    require(actual_paths == set(paths), "Native framework file inventory differs")
    for item in entries:
        path = (framework / item["path"]).resolve(strict=True)
        require(path.is_relative_to(framework.resolve()) and digest(path) == item["sha256"],
                "Native framework bytes or path differ")
    marker = runtime_version(role) if role == "new" else "pinkha-native-derived-v1-" + PATCHES[role]
    slices = helper.verify_framework_slices(framework, marker)
    require({(item["path"], item["architecture"]) for item in slices} == SLICE_IDENTITIES
            and len(slices) == 3, "All three original Apple architectures must be verified")
    ordering = lambda item: (item["path"], item["architecture"])
    require(sorted(slices, key=ordering) == sorted(receipt.get("binary_slices", []), key=ordering),
            "Actual architecture hashes differ from the original build")
    destination = app / "Dependencies/Middleware"
    require(not destination.exists() or (destination.is_dir() and not any(destination.iterdir())),
            "Refuse to overwrite an unrelated middleware installation")
    destination.mkdir(parents=True, exist_ok=True)
    shutil.move(str(framework), destination / "Lib.xcframework")
    shutil.copyfile(staging / "PinkhaNativeHeartBuild.json", destination / "PinkhaNativeHeartBuild.json")
    shutil.copyfile(staging / "PinkhaNativeHeartBuild.json", proof / "original-runtime-build.json")
    write(proof / "installation.json", dict(role=role, patch_sha256=PATCHES[role],
          inventory_sha256=INVENTORIES[role], binary_slices=slices, heart_sha=HEART,
          app_source_sha=git(app, "rev-parse", "HEAD"), expected_app_get_version=runtime_version(role)))
    return destination


def lock_hashes(app):
    paths = git(app, "ls-files", "-z").split("\0")
    return {path: digest(app / path) for path in paths if path.endswith("Package.resolved")}


def rewrite_product_paths(value, original, snapshot):
    if isinstance(value, str):
        return value.replace(str(original), str(snapshot))
    if isinstance(value, dict):
        return {key: rewrite_product_paths(child, original, snapshot) for key, child in value.items()}
    if isinstance(value, list):
        return [rewrite_product_paths(child, original, snapshot) for child in value]
    return value


def build_app(role, app, derived, work, proof, udid, source, helpers):
    ui, native = helpers
    product_root = work / role / "Products"
    proof.mkdir(parents=True)
    before_locks = lock_hashes(app)
    hanlin = app / "Dependencies/Hanlin/.pinkha-source.json"
    require(hanlin.is_file(), "Prepared canonical Hanlin SDK is missing")
    hanlin_sha = digest(hanlin)
    native.prepare_source_cache(app, derived)
    command = [
        "xcodebuild", "build-for-testing", "-project", "Anytype.xcodeproj", "-scheme", "Anytype",
        "-configuration", "Release-Anytype", "-destination", "platform=iOS Simulator,id=" + udid,
        "-derivedDataPath", str(derived), "-parallel-testing-enabled", "NO",
        "-only-testing:AnytypeTests/TorahT5RuntimePairTests", *FLAGS,
    ]
    _, log = run_logged(command, app, proof, "build-" + role, 5400)
    require(git(app, "rev-parse", "HEAD") == source and not git(app, "status", "--porcelain"),
            "Tracked application source changed during build")
    require(before_locks == lock_hashes(app) and digest(hanlin) == hanlin_sha, "Build dependency inputs changed")
    products = derived / "Build/Products"
    source_configuration = ui.test_configuration(products, "AnytypeTests")
    require(not product_root.exists(), "Refuse stale packaged application products")
    shutil.copytree(products, product_root, symlinks=True)
    configuration = product_root / source_configuration.name
    data = plistlib.loads(configuration.read_bytes())
    configuration.write_bytes(plistlib.dumps(rewrite_product_paths(data, products, product_root)))
    built = product_root / "Release-Anytype-iphonesimulator/Anytype.app"
    ui.verify_signed_simulator(built, proof)
    ui.verify_runtime_copies(built, runtime_version(role).encode(), proof)
    (proof / "native-source-marker").mkdir()
    ui.verify_runtime_copies(built, HEART.encode(), proof / "native-source-marker")
    carriers = ui.code_carriers(built)
    lock = json.loads((app / "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved").read_text())
    pins = [item["state"]["revision"] for item in lock["pins"] if item["identity"].lower() == "torahinspectorkit"]
    require(len(pins) == 1, "One exact Kit dependency revision required")
    checkouts = [path for path in (derived / "SourcePackages/checkouts").iterdir()
                 if path.name.lower() == "torahinspectorkit"]
    require(len(checkouts) == 1 and git(checkouts[0], "rev-parse", "HEAD") == pins[0], "Resolved Kit differs from app lock")
    receipt = dict(role=role, app_source_sha=source, flags=FLAGS, runtime_version=runtime_version(role),
                   package_lock_hashes=before_locks, hanlin_snapshot_sha256=hanlin_sha, kit_sha=pins[0],
                   code_sha256=carriers["sha256"], code_carriers=carriers,
                   app=str(built), configuration=str(configuration), build_log_sha256=digest(log))
    write(proof / "build.json", receipt)
    return receipt


def app_container(udid, kind, required=True):
    result = subprocess.run(["xcrun", "simctl", "get_app_container", udid, BUNDLE, kind],
                            capture_output=True, text=True)
    if not required and result.returncode:
        return None
    require(result.returncode == 0 and result.stdout.strip(), "Owned simulator application container unavailable")
    return Path(result.stdout.strip()).resolve(strict=True)


def contains_secret(path, needles):
    overlap = max(map(len, needles), default=1) - 1
    previous = b""
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(128 * 1024), b""):
            combined = previous + data
            if any(needle in combined for needle in needles):
                return True
            previous = combined[-overlap:] if overlap else b""
    return False


def preserve_native_evidence(work, proof, container, token):
    destination = proof / "actual-phases"
    require(not destination.exists(), "Refuse stale public native evidence")
    candidates = []
    secrets_path = container / "Library/Application Support/pinkha-t5-runtime-pair/secrets.json" if container else None
    if not secrets_path or not secrets_path.is_file():
        write(proof / "native-evidence-policy.json", dict(status="WITHHELD_NO_SECRET_INVENTORY",
              raw_xcresult_uploaded=False, account_data_uploaded=False))
        return False
    secret_record = json.loads(secrets_path.read_text(encoding="utf8"))
    require(secret_record.get("token") == token and all(isinstance(secret_record.get(key), str) and secret_record[key]
            for key in ["mnemonic", "accountKey"]), "Disposable secret guard is incomplete")
    values = [secret_record[key] for key in ["mnemonic", "accountKey"]]
    needles = [value.encode(encoding) for value in values for encoding in ["utf8", "utf-16-le", "utf-16-be"]]
    allowed = ["test.log", "test.command.json", "summary.json", "tests.json", "receipt.json",
               "result.json", "selection.json", "install.log", "install.command.json",
               "terminate.log", "terminate.command.json", "export-summary.command.json", "export-tests.command.json"]
    for phase, _ in PHASES:
        directory = work / "phases" / phase
        for filename in allowed:
            path = directory / filename
            if path.is_file():
                require(not path.is_symlink() and path.resolve().is_relative_to(work.resolve()), "Native evidence escaped owned work")
                require(not contains_secret(path, needles), "Disposable credential found; all native evidence withheld")
                candidates.append((path, destination / phase / filename))
    for source, target in candidates:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    write(proof / "native-evidence-policy.json", dict(status="PASS", copied_files=[
          str(target.relative_to(proof)) for _, target in candidates], raw_xcresult_uploaded=False,
          account_data_uploaded=False, secrets_uploaded=False, scanned_complete_credential_encodings=3))
    return True


def run_phase(phase, role, build, app, work, udid, source, token, nonce, container, prior, ui, method_results):
    directory = work / "phases" / phase
    directory.mkdir(parents=True)
    record = dict(status="RUNNING", phase=phase, role=role, actual_test_counts=None)
    write(directory / "result.json", record)
    try:
        run_logged(["xcrun", "simctl", "terminate", udid, BUNDLE], app, directory, "terminate", 30, check=False)
        run_logged(["xcrun", "simctl", "install", udid, build["app"]], app, directory, "install", 120)
        actual_container = app_container(udid, "data")
        require(container is None or actual_container == container, "Application update replaced the original data container")
        if prior:
            previous_path = actual_container / "Library/Application Support/pinkha-t5-runtime-pair/ledger.json"
            require(previous_path.is_file() and digest(previous_path) == prior["nextLedgerSHA256"],
                    "App install changed or removed the preceding account ledger")
        with Path(build["configuration"]).open("rb") as stream:
            configuration = plistlib.load(stream)
        environment = {
            "PINKHA_T5_APPLE_PAIR": "1", "PINKHA_T5_PAIR_PHASE": phase, "PINKHA_T5_PAIR_TOKEN": token,
            "PINKHA_T5_PAIR_NONCE": nonce, "PINKHA_T5_PAIR_APP_SHA": source,
        }
        ui.inject(configuration, "AnytypeTests", environment)
        selected = Path(build["configuration"]).with_name("UI27-t5-pair-" + phase + ".xctestrun")
        require(not selected.exists(), "Refuse stale XCTest selection")
        selected.write_bytes(plistlib.dumps(configuration))
        write(directory / "selection.json", dict(method=METHOD, environment=environment,
              device_udid=udid, xctestrun_sha256=digest(selected), packaged_code_sha256=build["code_sha256"]))
        bundle = directory / "original.xcresult"
        command = ["xcodebuild", "test-without-building", "-xctestrun", str(selected),
                   "-destination", "platform=iOS Simulator,id=" + udid, "-parallel-testing-enabled", "NO",
                   "-test-timeouts-enabled", "YES", "-default-test-execution-time-allowance", "300",
                   "-maximum-test-execution-time-allowance", "300",
                   "-only-testing:AnytypeTests/TorahT5RuntimePairTests", "-resultBundlePath", str(bundle)]
        outcome, _ = run_logged(command, app, directory, "test", 600, check=False)
        record.update(command_exit_code=outcome["return_code"], timed_out=outcome.get("timed_out", False))
        if bundle.exists():
            for mode in ["summary", "tests"]:
                run_logged(["xcrun", "xcresulttool", "get", "test-results", mode, "--path", str(bundle), "--format", "json"],
                           app, directory, "export-" + mode, 120, check=False, output=directory / (mode + ".json"))
        actual_container = app_container(udid, "data")
        require(container is None or actual_container == container, "XCTest replaced the original data container")
        installed = app_container(udid, "app")
        require(ui.code_carriers(installed)["sha256"] == build["code_sha256"],
                "Actual installed executable bytes differ from the selected packaged runtime")
        summary = json.loads((directory / "summary.json").read_text(encoding="utf8"))
        methods = method_results(json.loads((directory / "tests.json").read_text(encoding="utf8")))
        record["actual_test_counts"] = {key: summary.get(key) for key in ["passedTests", "failedTests", "skippedTests"]}
        require(outcome["return_code"] == 0 and not outcome.get("timed_out"), "Actual selected Swift test process failed")
        validate_xcresult(summary, methods, udid)
        fixture_directory = actual_container / "Library/Application Support/pinkha-t5-runtime-pair"
        receipt_path = fixture_directory / ("result-" + phase + ".json")
        ledger_path = fixture_directory / "ledger.json"
        report = json.loads(receipt_path.read_text(encoding="utf8"))
        ledger = json.loads(ledger_path.read_text(encoding="utf8"))
        shutil.copyfile(receipt_path, directory / "receipt.json")
        validate_phase(report, phase, role, token, nonce, source, ledger, digest(ledger_path), prior)
        record.update(status="PASS", actual_host_process_id=report["processID"],
                      account_root_path_sha256=report["rootPathSHA256"], container_path_sha256=sha_bytes(str(actual_container).encode()),
                      installed_code_sha256=build["code_sha256"], actual_methods=methods)
        return report, actual_container
    finally:
        if record["status"] != "PASS":
            record["status"] = "FAIL"
        write(directory / "result.json", record)


def execute(args, result):
    require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual Apple silicon Mac required")
    require(sys.version_info >= (3, 12), "Python3.12 required for safe original archive extraction")
    app, native_source, work, proof, derived = [path.resolve() for path in
                                             [args.app, args.native_source, args.work, args.evidence, args.derived]]
    require(len({app, native_source, work, proof, derived}) == 5, "Separate source/work/proof/derived paths required")
    require(not work.exists(), "Fresh controller-owned private work directory required")
    work.mkdir(parents=True, mode=0o700)
    source = git(app, "rev-parse", "HEAD")
    require(source == os.environ.get("GITHUB_SHA") and not git(app, "status", "--porcelain")
            and os.environ.get("GITHUB_RUN_ID", "").isdigit(), "Exact clean published App source/run required")
    require(git(native_source, "rev-parse", "HEAD") == NATIVE_SOURCE
            and not git(native_source, "status", "--porcelain"), "Exact immutable native inventory checkout required")
    preflight = json.loads((proof / "preflight/preflight.json").read_text(encoding="utf8"))
    require(preflight.get("status") == "PREFLIGHT_PASS_UI_NOT_RUN"
            and preflight.get("source_sha") == source, "Actual source-bound Xcode27 preflight required")
    selection = preflight["selected"]["ipad"]
    udid = selection["udid"]
    require(selection["name"] == "Pinkha-UI27-" + os.environ["GITHUB_RUN_ID"] + "-ipad",
            "Fresh job-owned simulator identity differs")
    require(shutil.disk_usage(work).free >= 8 * 1024**3, "Free disk reserve below8GiB")
    helper_path = app / "Tools/PinkhaNativeDerived"
    require(digest(helper_path / "build_custom_heart.py", True) == BUILDER_SHA, "Reviewed runtime helper source changed")
    sys.path.insert(0, str(helper_path))
    sys.path.insert(0, str(app / "Tools/PinkhaSimulatorGate"))
    import build_custom_heart as heart_helper
    import build_native_ipa as native_helper
    import run_ui27 as ui
    from validate_release import method_results
    result.update(app_source_sha=source, run_id=os.environ["GITHUB_RUN_ID"], device_udid=udid,
                  app_flags=FLAGS, expected_runtime_versions={role: runtime_version(role) for role in ["old", "new"]})
    write(proof / "result.json", result)
    run_logged(["xcrun", "simctl", "boot", udid], app, proof / "simulator", "boot", 120)
    run_logged(["xcrun", "simctl", "bootstatus", udid, "-b"], app, proof / "simulator", "boot-status", 180)
    require(app_container(udid, "data", required=False) is None, "Fresh simulator unexpectedly contains an app account")
    builds = {}
    for role, run_id in [("old", args.heart_r14_run_id), ("new", args.heart_r15_run_id)]:
        runtime_proof = proof / ("runtime-" + role)
        archive, source_run = download_runtime(role, run_id, work, runtime_proof, os.environ["GITHUB_REPOSITORY"])
        installed = install_runtime(role, archive, source_run, app, native_source, work, runtime_proof, heart_helper)
        builds[role] = build_app(role, app, derived, work, proof / ("build-" + role), udid, source, (ui, native_helper))
        shutil.move(str(installed), work / ("installed-framework-" + role))
        result["completed_builds"] = list(builds)
        write(proof / "result.json", result)
    token, reports, container = uuid4().hex, [], None
    result["phase"] = "ACTUAL_NATIVE_EXECUTION"
    write(proof / "result.json", result)
    try:
        for phase, role in PHASES:
            result["active_phase"] = phase
            write(proof / "result.json", result)
            report, container = run_phase(phase, role, builds[role], app, work, udid, source,
                                         token, uuid4().hex, container, reports[-1] if reports else None, ui, method_results)
            reports.append(report)
            result["completed_phases"] = [item["phase"] for item in reports]
            write(proof / "result.json", result)
        result["actual_counts"] = validate_sequence(reports, builds)
        require(git(app, "rev-parse", "HEAD") == source and not git(app, "status", "--porcelain"),
                "Application source changed during the actual native sequence")
    finally:
        if container is None:
            container = app_container(udid, "data", required=False)
        try:
            secret_scan_passed = preserve_native_evidence(work, proof, container, token)
        finally:
            run_logged(["xcrun", "simctl", "shutdown", udid], app, proof / "simulator", "shutdown", 120, check=False)
    require(secret_scan_passed, "Complete private credential inventory required before public acceptance")
    result.update(status="APPLE_SAME_ACCOUNT_RUNTIME_PAIR_PASS", phase_reports=reports,
                  exact_same_app_source=True, full_F10="NOT_PROVEN", product_lookup_flag="OFF")


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    for name in ["app", "native-source", "work", "evidence", "derived"]:
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ["heart-r14-run-id", "heart-r15-run-id"]:
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    args.evidence.mkdir(parents=True, exist_ok=True)
    result = dict(status="RUNNING", phase="PREFLIGHT", started_at=datetime.now(timezone.utc).isoformat(),
                  completed_builds=[], completed_phases=[], actual_counts=None,
                  product_lookup_flag="OFF", test_only_lookup_flag="IDENTICAL_BOTH_APP_BUILDS",
                  full_F10="NOT_PROVEN", release_accepted=False, full_matrix_accepted=False,
                  scope="same exact app source; two original Apple runtimes; four native test processes on one fresh OS27 iPad account",
                  limitations=["Actual Linux account/export proof is separate", "Space-wide index freshness remains unproven",
                               "No visual UI, physical-device, TestFlight or release acceptance from this route"])
    write(args.evidence / "result.json", result)
    try:
        execute(args, result)
    except BaseException as error:
        result.update(status="FAIL", error_type=type(error).__name__, error=str(error))
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    write(args.evidence / "result.json", result)
    print(json.dumps({key: result[key] for key in ["status", "completed_builds", "completed_phases", "actual_counts",
                                                    "product_lookup_flag", "full_F10"]}))
    return 0 if result["status"] == "APPLE_SAME_ACCOUNT_RUNTIME_PAIR_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
