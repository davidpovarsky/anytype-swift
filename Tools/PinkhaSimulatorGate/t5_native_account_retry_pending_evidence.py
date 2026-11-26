"""The unexecuted R07 tail, without replaying retained pagination acceptance.

A READY fixture is independently observed native setup, never a replacement
PASS pagination receipt. The shared retry validator owns the nine real calls.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import sys

import t5_native_pagination_evidence as pagination
from run_t5_apple_pair import require

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "PinkhaNativeDerived"))
import heart_runtime_profile as heart_profiles

PROTOCOL = "pinkha-t5-native-account-retry-pending-v1"
STATUS = "PASS_NATIVE_ACCOUNT_RETRY_PENDING"
METHOD = "TorahT5NativeAccountRetryPendingTests/nativeStoppedAccountPendingNineOnly"
FIXTURE_PROTOCOL = "pinkha-t5-native-account-retry-fixture-v1"
STATE_PROTOCOL = "pinkha-t5-native-account-retry-fixture-state-v1"
RETAINED_RUN = "44579466213"
RETAINED_SOURCE = "14f03b1955d2ecaf1a687e94abff07ce0e608790"
RETAINED_ARTIFACT = 14565181129
RETAINED_RECEIPT_SHA = "9681f1f6a871f37918687eace71360ff5ba248ba9474c39b5cc7cfe3d1c8f2cf"
ORIGINAL_SWIFT_BYTES = 28741
ORIGINAL_SWIFT_SHA = "dff9dd58471659cc19d082ea0961f2ccff9666ad86c4aa052c85a3aa4e5d4990"
RETAINED_REPORT = "docs/validation/20261119-t5-pagination-original/VERIFIED_NATIVE_PAGINATION_ACCEPTANCE.json"
RUNTIME_PROFILE = "r15-attachment-v1"
RUNTIME_RUN = "44943967103"
COHERENT_RUNTIME_PROFILE = "r15-attachment-authorized-current-read-v1"


def expected_runtime_version(runtime_profile=RUNTIME_PROFILE):
    require(runtime_profile in {RUNTIME_PROFILE, COHERENT_RUNTIME_PROFILE},
            "Pending-nine runtime must be an explicitly reviewed profile")
    return heart_profiles.select(runtime_profile).version


def restore_original_pagination_source(raw):
    """Invert only the additional native presentation observations, never assertions."""
    changes = [
        (b"    let title: String\n    let nativeLayout: Int\n    let nativeSnippet: String\n    let displayTitle: String\n    let typeID: String\n    let isArchived: Bool",
         b"    let title: String\n    let typeID: String\n    let isArchived: Bool"),
        (b"title: value.name,\n            nativeLayout: value.resolvedLayoutValue.rawValue, nativeSnippet: value.snippet, displayTitle: value.objectName,\n            typeID: value.type",
         b"title: value.name,\n            typeID: value.type"),
    ]
    restored = raw
    for added, original in changes:
        require(restored.count(added) == 1, "Exact reviewed native presentation observation differs")
        restored = restored.replace(added, original)
    require(hashlib.sha256(restored[:ORIGINAL_SWIFT_BYTES]).hexdigest() == ORIGINAL_SWIFT_SHA,
            "Original pagination assertions, native actions or fixture helpers changed")
    return restored


def validate_retained_source(app, *, runtime_binding=None):
    """Bind this route to the recorded original result without replaying it."""
    app = Path(app)
    path = app / RETAINED_REPORT
    raw = path.read_bytes()
    report = json.loads(raw)
    require(report.get("status") == "VERIFIED_BOUNDED_APPLE_NATIVE_PAGINATION_PASS"
            and report.get("run_id") == RETAINED_RUN and report.get("source_sha") == RETAINED_SOURCE
            and report.get("artifact_id") == RETAINED_ARTIFACT
            and report.get("native_receipt_sha256") == RETAINED_RECEIPT_SHA,
            "Exact retained original pagination qualification required")
    counts = report.get("native_semantic_counts", {})
    require(counts.get("actual_search_calls") == 36 and counts.get("observations") == 10
            and report.get("bindings", {}).get("runtime_source_run") == "44393343388",
            "Retained pagination scope/runtime source differs")
    original = (app / "AnyTypeTests/Pinkha/TorahT5NativePaginationTests.swift").read_bytes().replace(b"\r\n", b"\n")
    restore_original_pagination_source(original)
    pending = original.decode().split("struct TorahT5NativeAccountRetryPendingTests {", 1)
    require(len(pending) == 2, "Exact pending-only suite missing")
    suite = pending[1].split("\nextension TorahT5NativePaginationTests {", 1)[0]
    require(suite.count("@Test(") == 1
            and "try await original.prepareStoppedAccountRetryFixture()" in suite
            and "preparedFixtureOnly: true" in suite
            and "nativePaginationCurrentSpaceAndMutationAcceptance()" not in suite,
            "Pending suite must invoke preparation and the shared tail only")
    runtime_profile, runtime_run = RUNTIME_PROFILE, RUNTIME_RUN
    if runtime_binding is not None:
        require(runtime_binding.get("runtime_profile") == COHERENT_RUNTIME_PROFILE,
                "Retained pagination override is only the coherent runtime")
        require(heart_profiles.verify_binding(runtime_binding) == expected_runtime_version(COHERENT_RUNTIME_PROFILE),
                "Coherent pending-nine runtime binding differs")
        runtime_profile, runtime_run = COHERENT_RUNTIME_PROFILE, runtime_binding["heart_source_run_id"]
    return dict(status="REUSED_VERIFIED_PASS", original_run_id=RETAINED_RUN,
                original_source_sha=RETAINED_SOURCE, original_artifact_id=RETAINED_ARTIFACT,
                original_receipt_sha256=RETAINED_RECEIPT_SHA,
                qualification_sha256=hashlib.sha256(raw).hexdigest(), original_search_calls=36,
                replayed_baseline_body_invocations=0, replayed_baseline_search_calls=0,
                restored_original_swift_prefix_sha256=ORIGINAL_SWIFT_SHA,
                original_assertions_and_native_actions_unchanged=True,
                current_readback_observation_fields=["nativeLayout", "nativeSnippet", "displayTitle"],
                current_application_acceptance="NOT_RUN", original_private_account_reused=False,
                pending_runtime_profile=runtime_profile, pending_runtime_source_run_id=runtime_run,
                pending_runtime_version=expected_runtime_version(runtime_profile),
                retained_runtime_source_run_id="44393343388", original_runtime_result_relabelled=False)


def validate_prepared_fixture(fixture, *, source, run_id, token, root_sha, runtime_profile=RUNTIME_PROFILE):
    runtime = expected_runtime_version(runtime_profile)
    require(isinstance(fixture, dict) and set(fixture) == {
        "protocolVersion", "status", "retainedPaginationRunID", "baselineBodyInvocations",
        "baselineSearchCalls", "state", "preparedReadbacks", "setupCompletedAt"},
        "Exact pending fixture receipt fields required")
    require(fixture.get("protocolVersion") == FIXTURE_PROTOCOL and fixture.get("status") == "READY_NATIVE_FIXTURE"
            and fixture.get("retainedPaginationRunID") == RETAINED_RUN
            and type(fixture.get("baselineBodyInvocations")) is int and fixture["baselineBodyInvocations"] == 0
            and type(fixture.get("baselineSearchCalls")) is int and fixture["baselineSearchCalls"] == 0,
            "Fixture preparation cannot claim pagination PASS or replay the retained body")
    require(re.fullmatch("[a-f0-9]{40}", source or "") and re.fullmatch("[a-f0-9]{32}", token or "")
            and isinstance(run_id, str) and run_id.isdigit() and re.fullmatch("[a-f0-9]{64}", root_sha or ""),
            "Controller source/run/token/root identity missing")
    state = fixture.get("state")
    require(isinstance(state, dict) and state.get("protocolVersion") == STATE_PROTOCOL
            and state.get("status") == "READY_NATIVE_FIXTURE_STATE"
            and state.get("appSourceSHA") == source and state.get("runID") == run_id and state.get("token") == token
            and state.get("rootPathSHA256") == root_sha and state.get("runtimeVersion") == runtime
            and type(state.get("processID")) is int and state["processID"] > 0,
            "Prepared native fixture provenance/runtime differs")
    require(all(pagination.nonempty(state.get(key)) for key in ("accountID", "spaceID", "foreignSpaceID"))
            and state["spaceID"] != state["foreignSpaceID"], "Distinct native account/Spaces required")
    require((state.get("providerID"), state.get("canonicalReference")) == pagination.SOURCE
            and state.get("indexValue") == pagination.INDEX, "Original fixture source identity differs")
    require(state.get("observations") == [] and state.get("nativeMutationCounts") == {"BlockListDelete": 1}
            and type(state["nativeMutationCounts"]["BlockListDelete"]) is int,
            "Only one deleted-block setup mutation is allowed; baseline observations must stay absent")
    require(all(state.get(key) is True for key in (
        "accountStopCompleted", "accountNotRunningConfirmed", "appShutdownCompleted")),
        "Prepared existing account must actually stop and shut down without deletion")
    require(state.get("productLookupFlag") == "OFF" and state.get("wholeIndexCompleteness") == "NOT_PROVEN"
            and state.get("aclRevocation") == "NOT_PROVEN", "Fixture setup cannot widen acceptance")
    completed = fixture.get("setupCompletedAt")
    require(type(completed) in (int, float) and math.isfinite(completed) and completed > 0,
            "Actual fixture completion time required")
    fixtures = pagination.validate_fixture(state)
    originals = [fixtures[role] for role in pagination.ROLES[:7]]
    readbacks = fixture.get("preparedReadbacks")
    require(isinstance(readbacks, list) and len(readbacks) == 7
            and {value.get("objectID") for value in readbacks} == {obj["objectID"] for obj in originals},
            "Seven independent prepared native readbacks required")
    current = {value["objectID"]: value for value in readbacks}
    for obj in originals:
        value, prior = current[obj["objectID"]], obj["original"]
        _, graph, reachable = pagination.validate_readback(value, obj)
        original_graph, original_reachable = pagination.graph_nodes(prior)
        require(all(value[key] == prior[key] for key in ("canonicalRaw", "canonicalSHA256", "title", "typeID", "nativeLayout", "displayTitle"))
                and (obj["role"] == "block" or value["nativeSnippet"] == prior["nativeSnippet"])
                and prior["updatedAt"] <= value["updatedAt"] <= completed,
                "Fixture setup changed unrelated canonical bytes/metadata or native dates")
        if obj["role"] == "block":
            deleted = obj["targets"][0]["blockID"]
            require(reachable == original_reachable - {deleted}
                    and set(graph) in (set(original_graph), set(original_graph) - {deleted}),
                    "Fixture must remove only the original block target from reachability")
            require(all(graph[node] == [child for child in original_graph[node] if child != deleted]
                        for node in graph if node != deleted), "Unrelated native graph changed during fixture setup")
            if deleted in graph:
                require(graph[deleted] == original_graph[deleted], "Retained orphan block record changed")
        else:
            require(graph == original_graph, "Unrelated fixture block graph changed")
    return state, readbacks, fixtures
