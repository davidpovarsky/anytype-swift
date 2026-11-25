"""Original nine-query retry predicates with one explicit pending resolver import."""
import json
import re
from t5_native_account_retry_evidence import (
    require, pagination, PROTOCOL, DIRECTORY_STAGES, finite, digest, interval,
    validate_directory, successful_query, failed_query,
)
import combined_t5_pending_gateway as combined


def validate_receipt(receipt, baseline, baseline_bytes, *, source, run_id, run_attempt, token, root_sha,
                     credential_sha, current_directories, execution_window, pending_only=False, runtime_profile=None):
    require(type(pending_only) is bool, "Explicit pending-only mode required")
    require(runtime_profile is None or pending_only, "Runtime selection cannot change retained pagination acceptance")
    require(isinstance(baseline_bytes, bytes) and json.loads(baseline_bytes) == baseline,
            "The original starting-state receipt bytes are missing")
    prior_readbacks = None
    fixture = None
    if pending_only:
        import combined_t5_pending_gateway as pending
        fixture = baseline
        baseline, prior_readbacks, fixtures = pending.validate_prepared_fixture(
            fixture, source=source, run_id=run_id, token=token, root_sha=root_sha,
            runtime_profile=pending.RUNTIME_PROFILE if runtime_profile is None else runtime_profile)
        baseline_counts = {"actual_search_calls": 0}
        protocol, status = pending.PROTOCOL, pending.STATUS
    else:
        baseline_counts = pagination.validate_receipt(baseline, source=source, run_id=run_id, token=token, root_sha=root_sha)
        fixtures = pagination.validate_fixture(baseline)
        protocol, status = PROTOCOL, "PASS_NATIVE_ACCOUNT_RETRY"
    require(isinstance(receipt, dict) and receipt.get("protocolVersion") == protocol
            and receipt.get("status") == status, "Native existing-account retry receipt incomplete")
    for field in ("token", "appSourceSHA", "runID", "processID", "runtimeVersion", "accountID", "spaceID", "rootPathSHA256"):
        require(receipt.get(field) == baseline[field], "Retry belongs to another original account/process/runtime/source: " + field)
    require(type(receipt["processID"]) is int, "Actual native process identity type differs")
    require(isinstance(run_attempt, str) and run_attempt.isdigit() and int(run_attempt) > 0
            and receipt.get("runAttempt") == run_attempt, "Native retry run attempt differs")
    require(receipt.get("baselineReceiptSHA256Before") == receipt.get("baselineReceiptSHA256After") == digest(baseline_bytes),
            "Original pagination receipt changed before/after retry")
    require(re.fullmatch(r"[a-f0-9]{64}", credential_sha or "")
            and receipt.get("credentialFileSHA256Before") == receipt.get("credentialFileSHA256After") == credential_sha,
            "Original private credential bytes changed or were replaced")
    require(isinstance(current_directories, dict) and set(current_directories) == {"root", "account"},
            "Controller did not independently observe both existing directories")
    for value in current_directories.values():
        validate_directory(value)
    require(current_directories["root"]["pathSHA256"] == root_sha
            and current_directories["root"] != current_directories["account"], "Native root/account directory identities overlap")
    directories = receipt.get("directories")
    require(isinstance(directories, list) and [item.get("stage") for item in directories] == DIRECTORY_STAGES,
            "Existing directories were not checked before and after every restore")
    first_directories = {key: directories[0].get(key) for key in current_directories}
    for key, current in current_directories.items():
        first = first_directories[key]
        validate_directory(first)
        # Foundation Date and Python stat expose the same creation timestamp
        # through binary floating-point conversions. Path/device/inode remain
        # exact; cross-language creation-time conversion may differ by one ulp.
        require(all(first[field] == current[field] for field in ("pathSHA256", "device", "inode"))
                and abs(first["createdAt"] - current["createdAt"]) <= 0.000001,
                "Controller native directory identity differs from the original Swift observation")
    for item in directories:
        require(set(item) == {"stage", "root", "account"}
                and {key: item[key] for key in current_directories} == first_directories,
                "Existing root/account path, device, inode or creation date changed")
    restores, stops, queries = (receipt.get(name) for name in ("restores", "stops", "queries"))
    require(isinstance(restores, list) and [item.get("name") for item in restores] == ["first_restore", "retry_restore"],
            "Exactly two explicit restorations of the original existing account are required")
    for item in restores:
        require(item.get("selectedAccountID") == baseline["accountID"] and item.get("selectedSpaceID") == baseline["spaceID"]
                and item.get("walletRecovered") is True and item.get("accountSelected") is True,
                "Existing native wallet/account/Space was not actually restored")
    require(isinstance(stops, list) and [item.get("name") for item in stops] == ["account_stop", "final_stop"],
            "Actual native stop and final cleanup stops are required")
    for item in stops:
        require(item.get("removeData") is False and item.get("accountStopCompleted") is True
                and item.get("accountNotRunningConfirmed") is True, "Native account stop must retain data and confirm not running")
    require(isinstance(queries, list) and [item.get("name") for item in queries] == ["before_stop", "while_stopped", "after_restore"],
            "Success, native error and same-service successful retry must be observed in order")
    identities = []
    for query in queries:
        values = tuple(query.get(key) for key in ("serviceID", "searchRecorderID", "upstreamSearchID"))
        require(all(pagination.nonempty(value) for value in values) and len(set(values)) == 3,
                "Real production service, recorder and original search identities must be distinct")
        identities.append(values)
        require(query.get("activeSpaceID") == query.get("requestedSpaceID") == baseline["spaceID"],
                "Account error/retry query escaped the original active Space")
    require(identities[0] == identities[1] == identities[2], "Retry recreated the production service, recorder or original native search")
    require(all(finite(receipt.get(key)) for key in ("wrapperStartedAt", "baselineFinishedAt", "finishedAt", "appShutdownFinishedAt")),
            "Wrapper/native shutdown times are absent")
    events = [receipt["wrapperStartedAt"], receipt["baselineFinishedAt"]]
    for operation in (restores[0], queries[0], stops[0], queries[1], restores[1], queries[2], stops[1]):
        events.extend(interval(operation))
    events.extend([receipt["appShutdownFinishedAt"], receipt["finishedAt"]])
    require(events == sorted(events) and events[-1] - events[0] <= 900,
            "Actual native stop/error/restore sequence is reversed or exceeds the selected test deadline")
    require(isinstance(execution_window, (tuple, list)) and len(execution_window) == 2
            and all(finite(value) for value in execution_window)
            and execution_window[0] <= events[0] <= events[-1] <= execution_window[1],
            "Native retry is outside the actual selected XCTest execution")
    require(all(value["createdAt"] <= events[1] for value in current_directories.values()),
            "Native account directories were created after the accepted baseline")
    require(receipt.get("appShutdownCompleted") is True
            and all(receipt.get(key) is False for key in ("accountCreatedByTail", "walletCreatedByTail", "accountMigratedByTail")),
            "Tail recreated/migrated an account or failed final native shutdown")
    require(receipt.get("productLookupFlag") == "OFF" and receipt.get("wholeIndexCompleteness") == "NOT_PROVEN"
            and receipt.get("networkOutage") == "NOT_RUN" and receipt.get("uiErrorPresentation") == "NOT_RUN",
            "Stopped-account service proof cannot widen product, outage or UI acceptance")
    if pending_only:
        require(receipt["wrapperStartedAt"] <= fixture["setupCompletedAt"] <= receipt["baselineFinishedAt"],
                "Prepared fixture is outside the actual current pending-only method")
    successful_calls = (successful_query(queries[0], baseline, fixtures, prior_readbacks=prior_readbacks)
                        + successful_query(queries[2], baseline, fixtures, prior_readbacks=prior_readbacks))
    failed_query(queries[1], baseline["spaceID"])
    result = dict(selected_test_methods=1, baseline_body_invocations=0 if pending_only else 1,
        baseline_observations=0 if pending_only else 10,
        baseline_search_calls=baseline_counts["actual_search_calls"], retry_observations=3,
        retry_successful_search_calls=successful_calls, retry_failed_search_attempts=1,
        total_search_calls_in_wrapper=baseline_counts["actual_search_calls"] + successful_calls + 1,
        tail_existing_account_restores=2, tail_account_stops=2, same_production_service=True,
        unchanged_original_baseline=not pending_only, unchanged_private_credentials=True, same_existing_root_and_account_directories=True,
        whole_index_completeness="NOT_PROVEN", network_outage="NOT_RUN", ui_error_presentation="NOT_RUN", product_lookup_flag="OFF")

    if pending_only:
        result.update(pending_only=True, retained_pagination_run_id=pending.RETAINED_RUN,
                      retained_search_calls_not_reexecuted=36, fixture_setup_only=True,
                      unchanged_prepared_fixture=True, fixture_objects=10,
                      prepared_native_block_deletions=1, baseline_acceptance_rerun="NOT_RUN")
        require(result["total_search_calls_in_wrapper"] == 9, "Exactly nine pending service search calls required")
    return result


def validate_combined_receipt(receipt, baseline, baseline_bytes, **binding):
    require(binding.get("pending_only") is True
            and binding.get("runtime_profile") == combined.RUNTIME_PROFILE,
            "This consumer accepts only the exact combined pending-nine route")
    require(receipt.get("runtimeVersion") == combined.VERSION,
            "Actual combined runtime version differs")
    return validate_receipt(receipt, baseline, baseline_bytes, **binding)
