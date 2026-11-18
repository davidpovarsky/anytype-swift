"""Qualify the separate native selected-block receipt; require actual XCTest separately.

The document-only UI22 fixture/receipt contract remains in hanlin_acceptance_evidence.
This module cannot turn receipt JSON alone into an actual UI or full SDK PASS.
"""
import hashlib
import json
import re

from hanlin_acceptance_evidence import (
    NAVIGATION_CONTEXT_KEYS, apple_timestamp, bounded_text, require, uuid_text,
    validate_fixture as validate_document_fixture,
)

REQUIRED_CHECKS = frozenset({
    "middleware_logging_disabled", "native_single_block_selection_context",
    "read_denied_before_native_consent", "native_selected_text_read", "unselected_text_excluded",
    "read_receipt_contains_metadata_only", "native_selected_block_mounted_on_return",
    "closed_selection_host_denies_read", "no_provider_configuration",
})
BASE_FIXTURE_KEYS = frozenset({
    "fixtureID", "createdAt", "sourceSHA", "runID", "runAttempt", "accountID", "spaceID",
    "alternateSpaceID", "sourceObjectID", "sourceTitle", "sourceBlockID", "sourceText",
    "createdTitle", "cancelledTitle",
})


def validate_fixture(value, source_sha, run_id, run_attempt, now):
    require(isinstance(value, dict) and set(value) == {"base", "excludedBlockID", "excludedText"},
            "Selected-block fixture schema missing or changed")
    base = value["base"]
    require(isinstance(base, dict) and set(base) == BASE_FIXTURE_KEYS,
            "Selected-block base fixture schema missing or changed")
    validate_document_fixture(base, source_sha, run_id, run_attempt, now)
    excluded = bounded_text(value["excludedBlockID"], "unselected block")
    require(excluded != base["sourceBlockID"], "Selected and unselected blocks must be distinct")
    require(value["excludedText"] == "Hanlin unselected body " + uuid_text(base["fixtureID"], "fixture ID"),
            "Unselected paragraph has the wrong fixture nonce")
    return value


def fixture_environment(value, source_sha, run_id, run_attempt, now, raw_json):
    validate_fixture(value, source_sha, run_id, run_attempt, now)
    require(isinstance(raw_json, str) and len(raw_json.encode("utf-8")) <= 16384,
            "Oversized selected-block fixture JSON")
    require(json.loads(raw_json) == value, "Selected-block fixture JSON differs from the validated object")
    return {
        "PINKHA_HANLIN_SELECTION_UI_TESTING": "1",
        "PINKHA_SIMULATOR_UI_DISPOSABLE": "1",
        "PINKHA_HANLIN_SELECTION_FIXTURE_JSON": raw_json,
        "PINKHA_HANLIN_SELECTION_SOURCE_SHA": source_sha,
        "PINKHA_HANLIN_SELECTION_RUN_ID": run_id,
        "PINKHA_HANLIN_SELECTION_RUN_ATTEMPT": run_attempt,
    }


def validate_result(value, fixture, source_sha, run_id, run_attempt, now):
    validate_fixture(fixture, source_sha, run_id, run_attempt, now)
    base = fixture["base"]
    required = {"fixtureID", "sourceSHA", "runID", "runAttempt", "sessionID", "navigationContext",
                "processID", "startedAt", "finishedAt", "phase", "checks", "selectedRead", "nativeReturn",
                "deniedReadAttempts", "deniedReadInvocationIDs", "providerConfigured"}
    require(isinstance(value, dict) and required <= set(value) and set(value) <= required | {"failure"},
            "Selected-block result schema missing or changed")
    for key in ["fixtureID", "sourceSHA", "runID", "runAttempt"]:
        require(value[key] == base[key], "Selected-block result belongs to another " + key)
    require(value["phase"] == "HANLIN_SELECTION_ACCEPTANCE_PASS" and value.get("failure") is None,
            "Selected-block native result did not finish successfully")
    require(value["providerConfigured"] is False, "Selected-block test configured an AI provider")
    checks = value["checks"]
    require(isinstance(checks, dict) and set(checks) == REQUIRED_CHECKS and all(x is True for x in checks.values()),
            "Selected-block checks are incomplete or failed")
    session = uuid_text(value["sessionID"], "selected presentation")
    require(type(value["processID"]) is int and value["processID"] > 0, "Selected-block process identity missing")

    context = value["navigationContext"]
    require(isinstance(context, dict) and set(context) == NAVIGATION_CONTEXT_KEYS,
            "Selected-block original context schema missing or changed")
    for key, expected in [("app", "anytype"), ("account", base["accountID"]), ("workspace", base["spaceID"]),
                          ("space", base["spaceID"]), ("objectReference", base["sourceObjectID"])]:
        require(context[key] == expected, "Selected-block original context differs in " + key)
    uuid_text(context["sceneID"], "selected context scene")
    uuid_text(context["generation"], "selected context generation")
    require(context["selectionReferences"] == [base["sourceBlockID"]], "Selected-block context must contain exactly the prepared block")
    require(isinstance(context["sourceRevision"], str) and re.fullmatch(r"[0-9a-f]{64}", context["sourceRevision"]),
            "Selected-block source revision missing")

    read = value["selectedRead"]
    read_keys = {"invocationID", "objectReference", "spaceReference", "sourceRevision", "title", "blockReferences",
                 "textSHA256", "coverage", "effectState", "metadataContentsCount"}
    require(isinstance(read, dict) and set(read) == read_keys, "Selected-block read receipt missing or changed")
    bounded_text(read["invocationID"], "read invocation ID")
    for key, expected in [("objectReference", base["sourceObjectID"]), ("spaceReference", base["spaceID"]),
                          ("sourceRevision", context["sourceRevision"]), ("title", base["sourceTitle"]),
                          ("blockReferences", [base["sourceBlockID"]]), ("coverage", "selectedTextBlocksOnly"),
                          ("effectState", "confirmedNoEffect"),
                          ("textSHA256", hashlib.sha256(base["sourceText"].encode("utf-8")).hexdigest())]:
        require(read[key] == expected, "Selected-block read differs in " + key)
    require(type(read["metadataContentsCount"]) is int and read["metadataContentsCount"] == 0,
            "Selected-block read receipt retained payload")

    returned = value["nativeReturn"]
    return_keys = {"requestID", "queuedRequestID", "sessionID", "context", "objectReference", "blockReference",
                   "presentationAcknowledged"}
    require(isinstance(returned, dict) and set(returned) == return_keys, "Actual selected-block return receipt missing or changed")
    request = uuid_text(returned["requestID"], "selected return request")
    require(request == uuid_text(returned["queuedRequestID"], "selected queued request"),
            "Selected-block return acknowledged another queued request")
    require(uuid_text(returned["sessionID"], "selected return session") == session
            and returned["context"] == context, "Selected-block return changed presentation or context")
    require(returned["objectReference"] == base["sourceObjectID"] and returned["blockReference"] == base["sourceBlockID"],
            "Selected-block return changed its document or block target")
    require(returned["presentationAcknowledged"] is True, "Selected-block queued or unmounted return is not accepted")

    require(type(value["deniedReadAttempts"]) is int and value["deniedReadAttempts"] == 3,
            "Selected-block needs pre-consent and two post-close read denials")
    denied = value["deniedReadInvocationIDs"]
    require(isinstance(denied, list) and len(denied) == 3, "Selected-block read denial identities missing")
    denied_ids = {uuid_text(item, "denied selected read") for item in denied}
    require(len(denied_ids) == 3 and read["invocationID"].upper() not in denied_ids,
            "Selected-block denials reused a cached invocation")
    started = apple_timestamp(value["startedAt"], "selected start date")
    finished = apple_timestamp(value["finishedAt"], "selected finish date")
    require(apple_timestamp(base["createdAt"], "fixture date") <= started <= finished <= now,
            "Selected-block execution dates are inconsistent")
    return dict(status="SELECTION_RECEIPT_VERIFIED_XCTEST_REQUIRED_SEPARATELY",
                fixture_id=base["fixtureID"], session_id=session, process_id=value["processID"],
                source_sha=source_sha, run_id=run_id, run_attempt=run_attempt,
                required_checks=len(REQUIRED_CHECKS), selected_block_id=base["sourceBlockID"],
                excluded_block_id=fixture["excludedBlockID"], native_return_request_id=request,
                coverage="selectedTextBlocksOnly", selected_block_receipt_verified=True,
                selected_block_ui_verified=False, provider_configured=False, full_sdk_acceptance=False)
