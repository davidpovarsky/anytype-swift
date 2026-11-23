"""The missing quote freshness observations on the one coherent App build.

This is a new disposable native fixture, not the historical r14 runtime pair or
the passed 36-query pagination body. Immutable original receipts remain scoped.
"""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
from uuid import uuid4

import owned_simulator_readiness as simulator
import run_t5_apple_pair as pair
import run_t5_native_ui as native_ui

RUNTIME_PROFILE = "r15-attachment-authorized-current-read-v1"
PROTOCOL = "pinkha-t5-remaining-quote-freshness-v1"
NATIVE_PASS = "PASS_ACTUAL_NATIVE_QUOTE_FRESHNESS"
PASS = "T5_REMAINING_QUOTE_FRESHNESS_EXISTING_BUILD_PASS"
SUITE = "TorahT5RemainingFreshnessTests"
METHOD = SUITE + "/nativeQuoteMoveAndBlockDeletion"
SWIFT = "AnyTypeTests/Pinkha/TorahT5RuntimePairTests.swift"
ORIGINAL_BYTES = 41696
ORIGINAL_SHA = "27d6b0d40618b33185a34e3378670e378ed9c1bbcfd1c828cd5569f8c27ace2a"
PRIVATE = "Library/Application Support/pinkha-t5-remaining-freshness"
COUNTS = dict(selected_methods=1, observations=6, host_service_queries=6,
              object_set_details=2, block_list_delete=1, native_mutations=3,
              original_pair_phases=0, historical_pagination_invocations=0, failed=0, skipped=0)
# name, reference, native membership, live host targets, moved canonical, quote reachable
STAGES = (
    ("baseline", "Genesis 3:3", (0, 1, 2), (0, 1, 2), False, True),
    ("moved_original", "Genesis 3:3", (0, 1), (0, 1), True, True),
    ("moved_other", "Genesis 3:4", (2,), (2,), True, True),
    ("restored_original", "Genesis 3:3", (0, 1, 2), (0, 1, 2), False, True),
    ("restored_other_empty", "Genesis 3:4", (), (), False, True),
    ("quote_block_removed", "Genesis 3:3", (0, 1, 2), (0, 1), False, False),
)


def source_contract(app):
    raw = (app / SWIFT).read_bytes().replace(b"\r\n", b"\n")
    pair.require(pair.sha_bytes(raw[:ORIGINAL_BYTES]) == ORIGINAL_SHA,
                 "The original runtime-pair body must remain byte-identical")
    addition = raw[ORIGINAL_BYTES:].decode("utf8")
    pair.require(addition.count("struct " + SUITE + " {") == 1
                 and addition.count("func nativeQuoteMoveAndBlockDeletion()") == 1
                 and "realSameAccountRuntimePairPhase(" not in addition
                 and "runHostFreshness(" not in addition,
                 "Exactly one independent remaining-freshness suite is required")
    return dict(status="ORIGINAL_PAIR_RETAINED_NEW_SUITE_SELECTED", path=SWIFT,
                original_bytes=ORIGINAL_BYTES, original_sha256=ORIGINAL_SHA,
                current_sha256=pair.sha_bytes(raw), method=METHOD,
                original_pair_execution="NOT_RUN", historical_pagination_execution="NOT_RUN")


def validate_counts(value):
    pair.require(isinstance(value, dict) and set(value) == set(COUNTS)
                 and all(type(value[key]) is int and value[key] == expected for key, expected in COUNTS.items()),
                 "Exact remaining quote freshness counts are required")


def validate_receipt(value, *, source, run_id, run_attempt, token, root_sha, runtime):
    expected = dict(protocolVersion=PROTOCOL, status=NATIVE_PASS, appSourceSHA=source,
                    runID=run_id, runAttempt=run_attempt, token=token, rootPathSHA256=root_sha,
                    runtimeProfile=RUNTIME_PROFILE, runtimeVersion=runtime,
                    actualCapability="verified", serverConfiguration="localOnly",
                    wholeIndexCompleteness="NOT_PROVEN", forcedNetworkOutage="NOT_RUN", productLookupFlag="OFF")
    pair.require(re.fullmatch(r"[a-f0-9]{40}", source or "") and run_id.isdigit()
                 and run_attempt.isdigit() and int(run_attempt) > 0
                 and re.fullmatch(r"[a-f0-9]{32}", token or "") and pair.is_digest(root_sha)
                 and all(value.get(key) == item for key, item in expected.items()),
                 "Native quote freshness source/run/account/runtime identity differs")
    pair.require(type(value.get("processID")) is int and value["processID"] > 0
                 and all(value.get(key) is True for key in ("accountStopCompleted", "accountNotRunningConfirmed", "appShutdownCompleted"))
                 and value.get("mixedVersionAccepted") is False
                 and value.get("runtimePairPhasesExecuted") == []
                 and type(value.get("historicalPaginationInvocations")) is int
                 and value["historicalPaginationInvocations"] == 0,
                 "Native quote fixture lifecycle or retained acceptance scope differs")
    ledger = value.get("ledger", {})
    pair.require(ledger.get("completedPhases") == []
                 and all(ledger.get(key) == value.get(key) for key in
                         ("token", "appSourceSHA", "rootPathSHA256", "accountID", "spaceID"))
                 and ledger.get("rootRelativePath") == pair.ROOT_RELATIVE_PATH
                 and all(isinstance(ledger.get(key), str) and ledger[key] for key in
                         ("accountID", "spaceID", "manifestID", "canonicalKey"))
                 and pair.is_digest(ledger.get("manifestSHA256")),
                 "Fresh native ledger owner or original fixture identity differs")
    documents = ledger.get("documents", [])
    pair.require(len(documents) == 3 and len({item.get("objectID") for item in documents}) == 3
                 and documents[0].get("typeKey") == "ot-page" and documents[1].get("typeKey") == "ot-note"
                 and documents[2].get("typeKey") not in (None, "", "ot-page", "ot-note")
                 and documents[0].get("blockID") is None and documents[0].get("blockText") is None,
                 "Actual distinct Page/Note/custom-sourceQuote fixture is required")
    ids = [item["objectID"] for item in documents]
    blocks = [item.get("blockID") for item in documents[1:]]
    pair.require(all(isinstance(item, str) and item for item in ids + blocks) and len(set(blocks)) == 2
                 and all(isinstance(item.get("initialName"), str) and pair.is_digest(item.get("canonicalSHA256"))
                         and pair.is_digest(item.get("publicSHA256")) for item in documents)
                 and all(isinstance(item.get("blockText"), str) and item["blockText"] for item in documents[1:]),
                 "Native fixture details or original quote text missing")
    originals = value.get("originalCanonical", {})
    pair.require(set(originals) == set(ids), "All original canonical payloads are required")
    parsed = []
    for index, document in enumerate(documents):
        raw = originals[document["objectID"]]
        pair.require(isinstance(raw, str) and pair.sha_bytes(raw.encode()) == document["canonicalSHA256"],
                     "Original canonical bytes were substituted")
        canonical = json.loads(raw)
        records = canonical.get("records", [])
        pair.require(canonical.get("version") == 2 and len(records) == 1, "One canonical v2 record required")
        record = records[0]
        item = record.get("item", {})
        pair.require(record.get("spaceId") == ledger["spaceID"] and record.get("objectId") == document["objectID"]
                     and record.get("blockId") == document.get("blockID")
                     and item.get("kind") == "ref" and item.get("providerID") == "sefaria"
                     and item.get("canonicalKey") == item.get("externalID") == "Genesis 3:3"
                     and item.get("role") == ("sourceQuote" if index == 2 else "context"),
                     "Canonical quote/context source or native target binding differs")
        parsed.append(canonical)
    moved = copy.deepcopy(parsed[2])
    moved["records"][0]["item"].update(canonicalKey="Genesis 3:4", externalID="Genesis 3:4")
    pair.require(isinstance(value.get("serviceID"), str) and value["serviceID"]
                 and type(value.get("serviceQueryCount")) is int and value["serviceQueryCount"] == 6
                 and value.get("nativeMutationCounts") == {"ObjectSetDetails": 2, "BlockListDelete": 1}
                 and all(type(count) is int for count in value["nativeMutationCounts"].values()),
                 "Exactly one retained host service, six queries and three native mutations required")
    rows = value.get("observations", [])
    pair.require([row.get("name") for row in rows] == [row[0] for row in STAGES],
                 "Six ordered original native observations required")
    for ordinal, (row, (_, reference, native, host, is_moved, reachable)) in enumerate(zip(rows, STAGES), 1):
        pair.require(row.get("spaceID") == ledger["spaceID"] and row.get("sourceReference") == reference
                     and row.get("serviceID") == value["serviceID"]
                     and type(row.get("serviceQueryOrdinal")) is int and row["serviceQueryOrdinal"] == ordinal
                     and row.get("coverage") == "indexedTargetsOnly"
                     and row.get("limitations") == (["indexFreshnessUnverified"] if reachable else
                                                     ["indexFreshnessUnverified", "staleCandidates"]),
                     "Same-service observation source, ordering or bounded coverage differs")
        expected_native = sorted(ids[index] for index in native)
        pair.require(row.get("nativeCandidatesBefore") == row.get("nativeCandidatesAfter") == expected_native,
                     "Actual native membership before and after host lookup differs")
        targets = row.get("targets", [])
        expected_targets = [dict(objectID=ids[index], blockID=documents[index].get("blockID"),
                                 canUnlink=documents[index].get("blockID") is None) for index in host]
        pair.require(all(type(item.get("canUnlink")) is bool for item in targets)
                     and sorted([dict(objectID=item.get("objectID"), blockID=item.get("blockID"),
                                      canUnlink=item.get("canUnlink")) for item in targets], key=pair.target_key)
                     == sorted(expected_targets, key=pair.target_key),
                     "Live host targets, quote exclusion or honest empty result differ")
        readbacks = row.get("readbacks", [])
        pair.require([item.get("objectID") for item in readbacks] == ids, "Complete original native readback order required")
        for index, readback in enumerate(readbacks):
            document = documents[index]
            raw = readback.get("canonicalRaw")
            pair.require(readback.get("spaceID") == ledger["spaceID"]
                         and readback.get("title") == document["initialName"]
                         and readback.get("typeKey") == document["typeKey"]
                         and isinstance(raw, str) and readback.get("canonicalSHA256") == pair.sha_bytes(raw.encode()),
                         "Quote mutation changed unrelated native document details")
            if index == 2 and is_moved:
                pair.require(json.loads(raw) == moved, "Quote move changed canonical metadata or unknown fields")
            else:
                pair.require(raw == originals[document["objectID"]], "Unrelated or restored canonical bytes differ")
        pair.validate_freshness_graph(row.get("quoteGraph"), documents[2], ledger["spaceID"], reachable)
        expected_text = pair.sha_bytes(documents[2]["blockText"].encode()) if reachable else None
        pair.require(row.get("quoteBlockTextSHA256") == expected_text, "Original live quote body was changed or invented")
    return dict(COUNTS)


def native_paths(container):
    container = container.resolve(strict=True)
    root, directory = container / pair.ROOT_RELATIVE_PATH, container / PRIVATE
    for path in (root, directory, directory / "receipt.json", directory / "secrets.json"):
        pair.require(path.exists() and not path.is_symlink() and path.resolve(strict=True).is_relative_to(container),
                     "Native quote evidence or account root escaped its owned container")
    pair.require(root.is_dir() and directory.is_dir(), "Actual private native directories required")
    return directory, pair.sha_bytes(str(root.resolve(strict=True)).encode())


def run_after_coherent_build(*, app, work, proof, build, selection, pair, ui, method_results,
                             source, run_id, run_attempt, build_context, owned_device):
    import coherent_heart_release as coherent
    profile = coherent.validate_build(build, source, pair, ui, build_context)
    pair.require(owned_device.key == "t5-remaining-freshness", "Original planned quote-freshness destination required")
    source_contract(app)
    private, public = work / "remaining-freshness", proof / "remaining-freshness"
    pair.require(not private.exists() and not public.exists(), "Fresh remaining-freshness evidence required")
    private.mkdir(mode=0o700); public.mkdir(parents=True)
    token = uuid4().hex
    result = dict(status="RUNNING", app_source_sha=source, run_id=run_id, run_attempt=run_attempt,
                  token=token, method=METHOD, runtime_profile=profile.name, runtime_binding=build["runtime_binding"],
                  **coherent.build_reference(build),
                  additional_app_builds=0, additional_ui_runner_builds=0, historical_pair_execution="NOT_RUN",
                  historical_pagination_execution="NOT_RUN", mixed_version_accepted=False,
                  whole_index_completeness="NOT_PROVEN", physical_device_accepted=False,
                  started_at=datetime.now(timezone.utc).isoformat())
    destination = None
    started = False
    failure = None
    try:
        name = owned_device.prepare()
        creation, log = pair.run_logged(["xcrun", "simctl", "create", name, selection["device"]["identifier"],
            selection["runtime"]["identifier"]], app, public / "simulator", "create", 120)
        udid = log.read_text().strip()
        pair.require(creation.get("return_code") == 0 and not creation.get("timed_out")
                     and re.fullmatch(native_ui.evidence.UUID, udid) and udid.lower() != selection["udid"].lower(),
                     "Actual fresh native quote simulator creation failed")
        destination = dict(selection, name=name, udid=udid)
        owned_device.record_created(udid)
        result.update(device_udid=udid, device_name=name)
        pair.write(public / "result.json", result)
        result["readiness"] = simulator.ensure_ready(app=app, evidence=public / "readiness", selection=destination,
            expected_name=name, pair=pair, require_initial_shutdown=True)
        pair.require(pair.app_container(udid, "data", required=False) is None, "Fresh quote simulator already contains an account")
        pair.run_logged(["xcrun", "simctl", "install", udid, build["app"]], app, public / "simulator", "install", 180)
        build_context.verify_current()
        environment = dict(PINKHA_SIMULATOR_UI_DISPOSABLE="1", PINKHA_T5_REMAINING_FRESHNESS="1",
            PINKHA_T5_FRESHNESS_TOKEN=token, PINKHA_T5_FRESHNESS_APP_SHA=source,
            PINKHA_T5_FRESHNESS_RUN_ID=run_id, PINKHA_T5_FRESHNESS_RUN_ATTEMPT=run_attempt,
            PINKHA_T5_FRESHNESS_RUNTIME_PROFILE=profile.name)
        started = True
        result["selection"] = native_ui.select_tests(pair=pair, ui=ui, method_results=method_results,
            app=app, configuration=Path(build["configuration"]), udid=udid, blueprint="AnytypeTests",
            selections=[METHOD], environment=environment, directory=private / "phase")
        container = pair.app_container(udid, "data")
        directory, root_sha = native_paths(container)
        original = json.loads((directory / "receipt.json").read_bytes())
        result["actual_counts"] = validate_receipt(original, source=source, run_id=run_id, run_attempt=run_attempt,
            token=token, root_sha=root_sha, runtime=profile.version)
        installed = ui.code_carriers(pair.app_container(udid, "app"))["sha256"]
        pair.require(installed == build["code_sha256"], "Installed quote-freshness App differs from the frozen build")
        build_context.verify_current()
        controller = dict(app_source_sha=source, run_id=run_id, run_attempt=run_attempt, token=token,
            device_udid=udid, root_sha256=root_sha, installed_code_sha256=installed,
            source_contract=source_contract(app), original_receipt_sha256=pair.digest(directory / "receipt.json"),
            **coherent.build_reference(build))
        pair.write(private / "controller.json", controller)
        result.update(account_id=original["accountID"], space_id=original["spaceID"],
                      process_id=original["processID"], installed_code_sha256=installed)
    except BaseException as error:
        failure = error
        result.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL",
                      error_type=type(error).__name__, error=str(error))
        raise
    finally:
        cleanup_failure = None
        try:
            if started:
                container = pair.app_container(destination["udid"], "data", required=False)
                pair.require(container is not None, "Original native quote account is unavailable for credential scan")
                directory = container / PRIVATE
                secret_path = directory / "secrets.json"
                pair.require(secret_path.is_file() and not secret_path.is_symlink()
                             and secret_path.resolve().is_relative_to(container.resolve()),
                             "Complete original disposable credentials required before publication")
                secrets = json.loads(secret_path.read_bytes())
                receipt_path = directory / "receipt.json"
                if receipt_path.is_file():
                    pair.require(not receipt_path.is_symlink() and receipt_path.resolve().is_relative_to(container.resolve()),
                                 "Native quote receipt escaped its container")
                    shutil.copyfile(receipt_path, private / "native-receipt.json")
                allowed = [path for path in private.rglob("*") if path.is_file()
                           and path.suffix in (".json", ".log") and not any(part.endswith(".xcresult") for part in path.parts)]
                policy = native_ui.evidence.publish_evidence(private, public / "actual", allowed,
                    secret_record=secrets, token=token, contains_secret=pair.contains_secret)
                pair.write(public / "evidence-policy.json", policy)
                result["credential_scanned_evidence_published"] = True
        except BaseException as error:
            cleanup_failure = error
            result.update(status="FAIL", publication_error_type=type(error).__name__, publication_error=str(error))
        try:
            if destination is not None:
                result["shutdown"] = simulator.shutdown_owned(app=app, evidence=public / "shutdown",
                    selection=destination, expected_name=destination["name"], pair=pair,
                    readiness_receipt_path=public / "readiness/readiness.json")
        except BaseException as error:
            cleanup_failure = cleanup_failure or error
            result.update(status="FAIL", shutdown_error_type=type(error).__name__, shutdown_error=str(error))
        finally:
            result["finished_at"] = datetime.now(timezone.utc).isoformat()
            pair.write(public / "result.json", result)
        if failure is None and cleanup_failure is not None:
            raise cleanup_failure
    pair.require(result.get("credential_scanned_evidence_published") is True
                 and result.get("shutdown", {}).get("status") == "OWNED_SIMULATOR_SHUTDOWN_COMMAND_SUCCEEDED",
                 "Complete credential-scanned quote evidence and owned shutdown required")
    result["status"] = PASS
    pair.write(public / "result.json", result)
    try:
        validate_saved(public, source=source, run_id=run_id, run_attempt=run_attempt, build=build, ui=ui,
                       method_results=method_results)
    except BaseException as error:
        result.update(status="FAIL", validation_error_type=type(error).__name__, validation_error=str(error))
        pair.write(public / "result.json", result)
        raise
    return result


def validate_saved(public, *, source, run_id, run_attempt, build, ui, method_results):
    import coherent_heart_release as coherent
    read = lambda path: json.loads(path.read_bytes())
    result = read(public / "result.json")
    pair.require(result.get("status") == PASS and result.get("app_source_sha") == source
                 and result.get("run_id") == run_id and result.get("run_attempt") == run_attempt
                 and result.get("method") == METHOD and result.get("runtime_profile") == RUNTIME_PROFILE
                 and result.get("runtime_binding") == build["runtime_binding"]
                 and coherent.reference_matches(result, build)
                 and result.get("installed_code_sha256") == build["code_sha256"]
                 and result.get("mixed_version_accepted") is False and result.get("physical_device_accepted") is False
                 and result.get("whole_index_completeness") == "NOT_PROVEN"
                 and result.get("historical_pair_execution") == result.get("historical_pagination_execution") == "NOT_RUN"
                 and all(type(result.get(key)) is int and result[key] == 0 for key in
                         ("additional_app_builds", "additional_ui_runner_builds"))
                 and result.get("credential_scanned_evidence_published") is True
                 and result.get("shutdown", {}).get("status") == "OWNED_SIMULATOR_SHUTDOWN_COMMAND_SUCCEEDED",
                 "Original existing-build native quote result differs or widened acceptance")
    validate_counts(result.get("actual_counts"))
    actual = public / "actual"
    coherent.publication(actual, read(public / "evidence-policy.json"))
    controller, native = read(actual / "controller.json"), read(actual / "native-receipt.json")
    source_proof = controller.get("source_contract", {})
    pair.require(source_proof.get("status") == "ORIGINAL_PAIR_RETAINED_NEW_SUITE_SELECTED"
                 and source_proof.get("path") == SWIFT and source_proof.get("method") == METHOD
                 and source_proof.get("original_bytes") == ORIGINAL_BYTES
                 and source_proof.get("original_sha256") == ORIGINAL_SHA
                 and pair.is_digest(source_proof.get("current_sha256"))
                 and source_proof.get("original_pair_execution") == source_proof.get("historical_pagination_execution") == "NOT_RUN",
                 "Original runtime-pair retention proof differs")
    pair.require(all(controller.get(key) == result.get(key) for key in
                     ("app_source_sha", "run_id", "run_attempt", "token", "device_udid", "installed_code_sha256"))
                 and coherent.reference_matches(controller, build)
                 and controller.get("original_receipt_sha256") == pair.digest(actual / "native-receipt.json")
                 and result.get("account_id") == native.get("accountID") and result.get("space_id") == native.get("spaceID")
                 and result.get("process_id") == native.get("processID"),
                 "Original native quote receipt owner, App or process differs")
    runtime = ui.heart_profiles.select(RUNTIME_PROFILE).version
    validate_receipt(native, source=source, run_id=run_id, run_attempt=run_attempt, token=result["token"],
                     root_sha=controller["root_sha256"], runtime=runtime)
    native_ui.evidence.validate_selection(read(actual / "phase/summary.json"),
        method_results(read(actual / "phase/tests.json")), [METHOD], result["device_udid"])
    selected = read(actual / "phase/selection.json")
    pair.require(selected.get("blueprint") == "AnytypeTests" and selected.get("methods") == [METHOD]
                 and selected.get("device_udid") == result["device_udid"], "Original native quote XCTest selection differs")
    return result
