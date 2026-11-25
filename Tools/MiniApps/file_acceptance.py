"""Stage a real installable MiniApp and verify its actual original-app file journey."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import uuid
import zipfile

APP_ID = "org.itorah.miniapps.fileworkshop"
METHOD = "MiniAppsNativeAcceptanceUITests/testNativeFilesRoundTripColdReopenCancelAndReplay"
PACKAGE_SHA256 = "4b514641bae4700e6cc2a722eabad2f1316a6fb4558496b647a47c5a70a02c69"


def require(value, reason):
    if not value:
        raise ValueError(reason)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def container(udid, bundle, kind):
    path = Path(subprocess.check_output(
        ["xcrun", "simctl", "get_app_container", udid, bundle, kind], text=True, timeout=30).strip())
    require(path.is_absolute() and path.resolve(strict=True) == path and path.is_dir(),
            "Actual simulator container is absent or aliased")
    return path


def stage(app, udid, source_bundle, evidence, run_id):
    app, evidence = Path(app), Path(evidence)
    directory = app / "MiniApps/FileWorkshop"
    names = ["PACKAGE.json", "FileWorkshop.hanlinNativeScript", "source/script.json",
             "source/nativescript/app/package.json", "source/nativescript/app/bundle.mjs"]
    source_hashes = {}
    for name in names:
        path = directory / name
        require(path.is_file() and not path.is_symlink(), "Missing original File Workshop input")
        committed = subprocess.check_output(["git", "-C", str(app), "show", "HEAD:" +
                                              path.relative_to(app).as_posix()])
        require(path.read_bytes() == committed, "File Workshop input differs from committed source")
        source_hashes[name] = digest(path)
    archive = directory / "FileWorkshop.hanlinNativeScript"
    package = json.loads((directory / "PACKAGE.json").read_bytes())
    expected = {name.removeprefix("source/"): (directory / name).read_bytes()
                for name in names if name.startswith("source/")}
    with zipfile.ZipFile(archive) as zipped:
        require(len(zipped.namelist()) == len(expected) and set(zipped.namelist()) == set(expected)
                and all(zipped.read(name) == data for name, data in expected.items()),
                "Original File Workshop package members differ")
    require(digest(archive) == package["sha256"] == PACKAGE_SHA256
            and package["bytes"] == archive.stat().st_size and package["app_id"] == APP_ID
            and package["files"] == {name: hashlib.sha256(data).hexdigest() for name, data in expected.items()}
            and json.loads(expected["script.json"])["hanlinAppID"] == APP_ID,
            "Original installable File Workshop identity differs")
    destination = container(udid, "com.itorah.hanlinminiapps", "data") / "Documents" / archive.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    require(not destination.exists() and not destination.is_symlink(), "Input was already staged")
    with destination.open("xb") as stream:
        stream.write(archive.read_bytes())
    require(digest(destination) == PACKAGE_SHA256, "Staged package bytes changed")
    shared = container(udid, source_bundle, "group.com.itorah.shared")
    require(container(udid, "com.itorah.hanlinminiapps", "group.com.itorah.shared") == shared,
            "Source and producer do not share the actual common container")
    bridge = shared / "MiniAppsBridge/v1"
    require(bridge.is_dir() and bridge.resolve() == bridge, "Actual Bridge store is absent")
    report = "original-native-file-ui-" + str(uuid.UUID(run_id.removeprefix("local-"))) + ".json"
    row = {"status": "COMMITTED_PACKAGE_STAGED_FOR_ACTUAL_IMPORT_UI", "package_id": APP_ID,
           "archive": str(destination), "archive_sha256": PACKAGE_SHA256,
           "source_hashes": source_hashes, "bridge": str(bridge), "report_name": report,
           "native_import_executed": False, "registry_or_bridge_mutation": False}
    (evidence / "file-workshop-stage.json").write_text(json.dumps(row, indent=2, sort_keys=True) + "\n")
    return row


def verify(stage, source_data, fixture, source_bundle, evidence):
    bridge, source_data, evidence = Path(stage["bridge"]), Path(source_data), Path(evidence)
    report_path = bridge / stage["report_name"]
    require(report_path.is_file() and not report_path.is_symlink(), "Real file UI report missing")
    report = json.loads(report_path.read_bytes())
    require(report.get("status") == "REAL_NATIVE_FILE_UI_PASS"
            and report.get("sourceSHA") == fixture["sourceSHA"] and report.get("runID") == fixture["runID"]
            and report.get("documentID") == fixture["objectID"]
            and report.get("inputFileCounts") == [0, 1, 2, 2]
            and report.get("nativeFilesSeeded") == 0 and report.get("coldSourceReturn") is True
            and report.get("replayedCallbacks") == 2,
            "Actual file journey scope/source differs")
    ids = report["requestIDs"]
    require(len(ids) == len(set(ids)) == 4
            and all(str(uuid.UUID(value)) == value for value in ids), "Four real requests are required")
    hashes = [report["firstSHA256"], report["secondSHA256"]]
    require(hashes[0] != hashes[1] and all(re.fullmatch(r"[a-f0-9]{64}", value) for value in hashes),
            "Independent real file byte identities are missing")

    def attachment(item):
        identifier = str(uuid.UUID(item["attachmentID"]))
        path = bridge / "attachments" / identifier
        require(item.get("kind") == "file" and item.get("text") is None
                and path.is_file() and not path.is_symlink(), "Actual Bridge file is missing or aliased")
        return digest(path)

    records, native_ids = [], []
    for index, request_id in enumerate(ids):
        path = bridge / "requests" / (request_id + ".json")
        require(path.is_file() and not path.is_symlink(), "Actual request record missing")
        row = json.loads(path.read_bytes()); request, result = row["request"], row["result"]
        require(str(uuid.UUID(request["id"])) == request_id
                and request["appID"] == APP_ID and request["source"]["appID"] == source_bundle
                and request["source"]["documentID"] == fixture["objectID"]
                and row["acknowledged"] is True
                and str(uuid.UUID(result["requestID"])) == request_id,
                "Actual file request/result/acknowledgement ownership differs")
        inputs = [item for item in request["inputs"] if item["kind"] == "file"]
        require(len(inputs) == [0, 1, 2, 2][index], "Original native file input count differs")
        actual_hashes = [attachment(item) for item in inputs]
        require(actual_hashes == [] if index == 0 else
                actual_hashes == hashes[:1] if index == 1 else set(actual_hashes) == set(hashes),
                "Original file bytes did not survive native persistence and export")
        if index:
            mapping = json.loads(request["source"]["metadata"]["anytype.files.v1"])
            require(set(mapping) == {str(uuid.UUID(item["attachmentID"])) for item in inputs}
                    and len(set(mapping.values())) == len(inputs), "Original native file block mapping differs")
            native_ids.append(set(mapping.values()))
        if index < 2:
            require(result["status"] == "success" and result["operation"] == "insert"
                    and len(result["items"]) == 1 and attachment(result["items"][0]) == hashes[index]
                    and result["items"][0].get("name") == "document.txt",
                    "Actual native file return differs")
        else:
            require(result["status"] == "cancelled" and not result["items"],
                    "Cancellation unexpectedly returned a mutation")
        records.append(row)
    require(native_ids[0] < native_ids[1] == native_ids[2] == set(report["nativeBlockIDs"])
            and len(native_ids[1]) == 2, "Duplicate/cancel delivery changed original native block identities")
    journals = []
    root = source_data / "Library/Application Support/MiniAppsReceipts"
    for request_id in ids[:2]:
        paths = list(root.glob("*/" + request_id + ".json"))
        require(len(paths) == 1, "Original native file journal missing/ambiguous")
        journal = json.loads(paths[0].read_bytes())
        require(journal.get("completed") is True and str(uuid.UUID(journal["requestID"])) == request_id
                and len(journal.get("insertedBlocks", {})) == 1
                and len(journal.get("additions", [])) == 1
                and journal["additions"][0].get("kind") == "file",
                "Native file journal did not finish exactly one original block")
        journals.append(journal)
    require(set().union(*(set(j["insertedBlocks"].values()) for j in journals)) == native_ids[-1],
            "Original journals and actual exported native blocks differ")
    proof = {"status": "REAL_ORIGINAL_FILE_ROUND_TRIP_PASS", "report": report,
             "actual_shared_records": records, "completed_original_journals": journals,
             "native_atomic_update_and_receipt": False, "physical_device_accepted": False}
    (evidence / "native-file-roundtrip.json").write_text(json.dumps(proof, indent=2, ensure_ascii=False) + "\n")
    return proof
