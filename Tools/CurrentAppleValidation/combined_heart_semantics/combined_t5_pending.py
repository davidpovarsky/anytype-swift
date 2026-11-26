"""Additive exact combined-runtime pending fixture authority.

The original fixture predicate function below is byte-for-byte unchanged.
Only this module's explicit runtime profile resolver differs. Existing r15
validators, receipts and entry gates remain unchanged.
"""
import math
import re
from t5_native_account_retry_pending_evidence import (
    PROTOCOL, STATUS, METHOD, FIXTURE_PROTOCOL, STATE_PROTOCOL, RETAINED_RUN,
    pagination, require,
)
RUNTIME_PROFILE = "dual-engine-runtime-v1"
VERSION = "pinkha-dual-runtime-v1-70fb5342f2ff31d1cf5f7ce44bed7b16f6373f6bf95eb031d165339cf0f26683"


def expected_runtime_version(runtime_profile=RUNTIME_PROFILE):
    require(runtime_profile == RUNTIME_PROFILE, "Exact combined pending profile required")
    return VERSION


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
        require(all(value[key] == prior[key] for key in ("canonicalRaw", "canonicalSHA256", "title", "typeID"))
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
