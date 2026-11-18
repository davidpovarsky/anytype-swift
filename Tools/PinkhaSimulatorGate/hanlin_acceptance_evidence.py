"""Validate SDK06 native evidence independently of the app's diagnostic label.

These checks only qualify the native receipt. The caller must separately require
the named preparation and UI XCTest executions, exact source, and executable bytes.
"""
from datetime import datetime, timezone
import math
import re
from uuid import UUID

APPLE_DATE_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc).timestamp()
REQUIRED_CHECKS = frozenset({
    "middleware_logging_disabled", "read_denied_before_native_consent",
    "real_native_context_text_read", "native_cancel_prevents_write",
    "native_confirm_creates_exact_page", "created_page_read_back_by_journal_id",
    "replay_does_not_create_duplicate", "cancelled_title_absent_from_native_index",
    "no_provider_configuration", "closed_presentation_denies_read_and_create",
    "native_source_permission_change_denied", "native_active_space_change_denied",
    "native_account_logout_denied", "original_commit_metadata_survives_logout",
    "background_presentation_had_live_read_access", "native_background_foreground_observed",
    "backgrounded_presentation_denies_read_and_create", "pending_read_consent_dismissed_on_document_exit",
    "departed_document_presentation_denies_read_and_create", "fresh_presentation_requires_new_native_consent",
    "fresh_presentation_reads_original_document_only",
})
SCENE_EVENT_KEYS = frozenset({
    "sceneWillDeactivate", "sceneDidEnterBackground", "sceneWillEnterForeground", "sceneDidActivate",
    "applicationWillResignActive", "applicationDidBecomeActive",
})
INVALIDATION_CAUSES = frozenset({
    "nativeAuthorityChanged", "presentationRemoved", "interactivePresentationDismissal", "explicitCloseOrOwner",
})


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def bounded_text(value, name, maximum=256):
    require(isinstance(value, str) and value.strip() and len(value.encode("utf-8")) <= maximum,
            "Missing or oversized native " + name)
    return value


def uuid_text(value, name):
    bounded_text(value, name, 36)
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as error:
        raise ValueError("Invalid native " + name) from error
    require(value.upper() == str(parsed).upper(), "Noncanonical native " + name)
    return str(parsed).upper()


def apple_timestamp(value, name):
    require(type(value) in {int, float} and math.isfinite(value), "Invalid native " + name)
    return APPLE_DATE_EPOCH + value


def validate_fixture(value, source_sha, run_id, run_attempt, now):
    require(isinstance(value, dict), "Native fixture must be an object")
    require(isinstance(source_sha, str) and re.fullmatch(r"[0-9a-f]{40}", source_sha),
            "Invalid expected source identity")
    require(isinstance(run_id, str) and run_id.isdigit() and int(run_id) > 0
            and isinstance(run_attempt, str) and run_attempt.isdigit() and int(run_attempt) > 0,
            "Invalid expected CI identity")
    for key, expected in [("sourceSHA", source_sha), ("runID", run_id), ("runAttempt", run_attempt)]:
        require(value.get(key) == expected, "Native fixture belongs to another " + key)
    nonce = uuid_text(value.get("fixtureID"), "fixture ID")
    for key in ["accountID", "spaceID", "alternateSpaceID", "sourceObjectID", "sourceBlockID"]:
        bounded_text(value.get(key), key)
    require(value["spaceID"] != value["alternateSpaceID"], "Native alternate Space must be distinct")
    bounded_text(value.get("sourceTitle"), "source title", 512)
    for key, prefix in [("sourceText", "Hanlin native body "), ("createdTitle", "Hanlin native created "),
                        ("cancelledTitle", "Hanlin native cancelled ")]:
        require(value.get(key) == prefix + nonce, "Native fixture nonce differs in " + key)
    created = apple_timestamp(value.get("createdAt"), "fixture date")
    require(0 <= now - created < 3600, "Native fixture is stale or from the future")
    return value


def fixture_environment(value, source_sha, run_id, run_attempt, now, raw_json):
    validate_fixture(value, source_sha, run_id, run_attempt, now)
    require(isinstance(raw_json, str) and len(raw_json.encode("utf-8")) <= 16384,
            "Oversized native fixture JSON")
    # Preserve the exact JSON obtained from the newly prepared app container.
    import json
    require(json.loads(raw_json) == value, "Native fixture JSON differs from the validated object")
    return {
        "PINKHA_HANLIN_NATIVE_UI_TESTING": "1",
        "PINKHA_SIMULATOR_UI_DISPOSABLE": "1",
        "PINKHA_HANLIN_NATIVE_FIXTURE_JSON": raw_json,
        "PINKHA_HANLIN_NATIVE_SOURCE_SHA": source_sha,
        "PINKHA_HANLIN_NATIVE_RUN_ID": run_id,
        "PINKHA_HANLIN_NATIVE_RUN_ATTEMPT": run_attempt,
    }


def validate_result(value, fixture, source_sha, run_id, run_attempt, now):
    validate_fixture(fixture, source_sha, run_id, run_attempt, now)
    require(isinstance(value, dict), "Native result must be an object")
    for key in ["fixtureID", "sourceSHA", "runID", "runAttempt"]:
        require(value.get(key) == fixture[key], "Native result belongs to another " + key)
    require(value.get("phase") == "NATIVE_ACCEPTANCE_PASS", "Native result did not finish successfully")
    require(value.get("failure") is None, "Native result records a failure")
    require(value.get("providerConfigured") is False, "Native test configured an AI provider")
    checks = value.get("checks")
    require(isinstance(checks, dict) and set(checks) == REQUIRED_CHECKS
            and all(flag is True for flag in checks.values()), "Native checks are incomplete or failed")
    created = bounded_text(value.get("createdObjectID"), "created object")
    require(created != fixture["sourceObjectID"], "Native create reused the source object")
    sessions = [uuid_text(value.get(key), key) for key in
                ["sessionID", "backgroundSessionID", "staleConsentSessionID", "freshSessionID"]]
    require(len(set(sessions)) == 4, "Native presentations reused a session identity")
    causes = value.get("invalidationCauses")
    require(isinstance(causes, dict) and len(causes) == 4
            and {uuid_text(key, "invalidation session") for key in causes} == set(sessions)
            and all(cause in INVALIDATION_CAUSES for cause in causes.values()),
            "Native invalidation observations differ from the four presentations")
    for key in ["sceneEventCounts", "backgroundCycleSceneDelta", "documentExitSceneDelta"]:
        counts = value.get(key)
        require(isinstance(counts, dict) and set(counts) == SCENE_EVENT_KEYS
                and all(type(count) is int and count >= 0 for count in counts.values()),
                "Invalid native scene observations: " + key)
    totals = value["sceneEventCounts"]
    background = value["backgroundCycleSceneDelta"]
    document_exit = value["documentExitSceneDelta"]
    require(all(background[key] + document_exit[key] <= totals[key] for key in SCENE_EVENT_KEYS),
            "Native disjoint scene deltas exceed their total observations")
    require(all(background[key] > 0 for key in
                ["sceneDidEnterBackground", "sceneWillEnterForeground", "sceneDidActivate"]),
            "Native background and foreground transitions were not observed")
    attribution = ("navigationWithSceneTransition" if any(document_exit.values())
                   else "navigationWithoutSceneTransition")
    require(value.get("documentExitAttribution") == attribution,
            "Native document-exit attribution contradicts the observed scene transitions")
    require(type(value.get("processID")) is int and value["processID"] > 0,
            "Native result has no actual process identity")
    started = apple_timestamp(value.get("startedAt"), "start date")
    finished = apple_timestamp(value.get("finishedAt"), "finish date")
    fixture_time = apple_timestamp(fixture["createdAt"], "fixture date")
    require(fixture_time <= started <= finished <= now, "Native execution dates are inconsistent")
    return dict(status="NATIVE_RECEIPT_VERIFIED_XCTEST_REQUIRED_SEPARATELY",
                fixture_id=value["fixtureID"], session_id=value["sessionID"], process_id=value["processID"],
                created_object_id=created, required_checks=len(REQUIRED_CHECKS),
                source_sha=source_sha, run_id=run_id, run_attempt=run_attempt,
                provider_configured=False, presentation_count=len(sessions),
                document_exit_attribution=attribution, invalidation_causes=causes,
                full_sdk_acceptance=False)
