"""Finite, fail-closed test-provider protocol. Never a production model/provider.

Responses translate the pinned Hanlin ProviderResponseFixtures OpenAI Chat
builders. `canonical/` binds and exercises the original Swift implementations.
No request text, credential, tool payload or exception description is logged.
"""
from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from typing import Any

CONTRACT = "pinkha-mounted-hanlin-provider-fixture-v1"
MODEL = "pinkha-hanlin-acceptance-v1"
MAX_BODY = 262_144
MAX_TOOL_RESULT = 32_768
READ_TOOL = "anytype_read_context_text"
CREATE_TOOL = "anytype_create_page"
READ_SCHEMA = {"type": "object", "properties": {}, "additionalProperties": False}
CREATE_SCHEMA = {
    "type": "object",
    "properties": {"title": {"type": "string", "minLength": 1, "maxLength": 512}},
    "required": ["title"], "additionalProperties": False,
}
READ_CALL = "call_pinkha_read_selected_v1"
CANCEL_CALL = "call_pinkha_cancel_create_v1"
ALLOW_CALL = "call_pinkha_allow_create_v1"
PROMPTS = (
    "Check the available actions without reading source text.",
    "Read only the selected block, then offer the cancelled draft page.",
    "Offer the separately approved draft page.",
)
MARKERS = (
    "PINKHA_HANLIN_DENIED_READ_CHECKED",
    "PINKHA_HANLIN_CANCELLED_CREATE_CHECKED",
    "PINKHA_HANLIN_APPROVED_CREATE_CHECKED",
)
CANCEL_MESSAGE = "Host operation unavailable or no longer authorized"
CHECK_NAMES = (
    "scenario_registered_once", "denied_read_catalog_omits_read_tool",
    "denied_read_has_no_source_text", "allowed_read_exact_schema",
    "read_original_call_identity", "selected_payload_exact_block_and_text",
    "selected_payload_scope_shape_valid", "unselected_text_never_disclosed",
    "cancel_creation_exact_title_call", "cancel_creation_refused",
    "allowed_creation_new_exact_call", "allowed_creation_empty_success",
    "six_provider_requests_completed",
)


class FixtureError(Exception):
    """Only fixed, source-defined diagnostic codes cross the private boundary."""
    def __init__(self, code: str, status: int = 400):
        super().__init__(code)
        self.code = code
        self.status = status


def require(condition: bool, code: str, status: int = 400) -> None:
    if not condition:
        raise FixtureError(code, status)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def strict_json(data: bytes, maximum: int = MAX_BODY) -> Any:
    require(0 < len(data) <= maximum, "json_size")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result

    def bad_constant(_: str) -> None:
        raise FixtureError("nonfinite_json")

    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=bad_constant)
        stack = [(value, 0)]
        count = 0
        while stack:
            item, depth = stack.pop()
            count += 1
            require(count <= 8192 and depth <= 24, "json_complexity")
            if isinstance(item, dict):
                stack.extend((x, depth + 1) for x in item.values())
                require(all(len(k.encode("utf-8")) <= 4096 for k in item), "json_key")
            elif isinstance(item, list):
                stack.extend((x, depth + 1) for x in item)
            elif isinstance(item, str):
                item.encode("utf-8")  # Refuse unpaired surrogate escapes.
        return value
    except FixtureError:
        raise
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        raise FixtureError("invalid_json") from None


def bounded_string(value: Any, maximum: int, code: str, minimum: int = 1) -> str:
    require(isinstance(value, str), code)
    try:
        require(minimum <= len(value.encode("utf-8")) <= maximum, code)
        require("\x00" not in value, code)
    except UnicodeError:
        raise FixtureError(code) from None
    return value


def sse_openai(payload: dict[str, Any]) -> bytes:
    return b"data: " + canonical(payload) + b"\n\n"


def text_chunks(text: str, *, identifier: str, model: str = MODEL) -> list[bytes]:
    return [
        sse_openai({"id": identifier, "model": model, "choices": [{
            "index": 0, "delta": {"role": "assistant", "content": text},
            "finish_reason": None}]}),
        sse_openai({"id": identifier, "model": model, "choices": [{
            "index": 0, "delta": {}, "finish_reason": "stop"}]}),
        b"data: [DONE]\n\n",
    ]


def tool_chunks(call_id: str, name: str, arguments: str, *, identifier: str,
                model: str = MODEL) -> list[bytes]:
    return [
        sse_openai({"id": identifier, "model": model, "choices": [{
            "index": 0, "delta": {"role": "assistant", "tool_calls": [{
                "index": 0, "id": call_id, "type": "function",
                "function": {"name": name, "arguments": arguments}}]},
            "finish_reason": None}]}),
        sse_openai({"id": identifier, "model": model, "choices": [{
            "index": 0, "delta": {}, "finish_reason": "tool_calls"}]}),
        b"data: [DONE]\n\n",
    ]


@dataclass(frozen=True)
class Scenario:
    selected_block_id: str
    selected_text: str
    unselected_text: str
    document_title: str
    cancelled_title: str
    approved_title: str
    object_reference: str | None
    space_reference: str | None

    @classmethod
    def parse(cls, obj: Any) -> "Scenario":
        required = {"selectedBlockID", "selectedText", "unselectedText",
                    "documentTitle", "cancelledTitle", "approvedTitle"}
        optional = {"objectReference", "spaceReference"}
        require(isinstance(obj, dict) and required <= obj.keys()
                and obj.keys() <= required | optional, "scenario_fields")
        strings = {}
        for key in required:
            strings[key] = bounded_string(obj[key], 2048 if key.endswith("Text")
                                          else 512, "scenario_value")
            require(bool(strings[key].strip()), "scenario_blank")
        require(strings["selectedText"] != strings["unselectedText"]
                and strings["selectedText"] not in strings["unselectedText"]
                and strings["unselectedText"] not in strings["selectedText"],
                "scenario_canaries_overlap")
        require(len({strings[x] for x in ("documentTitle", "cancelledTitle", "approvedTitle")}) == 3,
                "scenario_titles_overlap")
        for field in ("documentTitle", "cancelledTitle", "approvedTitle"):
            require(all(strings[x] not in strings[field]
                        for x in ("selectedText", "unselectedText")), "scenario_canary_in_title")
        for key in optional:
            if key in obj:
                bounded_string(obj[key], 512, "scenario_scope")
        return cls(strings["selectedBlockID"], strings["selectedText"],
                   strings["unselectedText"], strings["documentTitle"],
                   strings["cancelledTitle"], strings["approvedTitle"],
                   obj.get("objectReference"), obj.get("spaceReference"))


def _contains(value: Any, needle: str, nested: int = 0) -> bool:
    """Also inspect JSON tool-result strings; escaped Hebrew is not a bypass."""
    if isinstance(value, str):
        if needle in value:
            return True
        stripped = value.lstrip(" \t\r\n")
        if nested < 2 and stripped[:1] in ("{", "["):
            try:
                return _contains(strict_json(value.encode("utf-8")), needle, nested + 1)
            except FixtureError:
                pass
        return False
    if isinstance(value, dict):
        return any(_contains(k, needle, nested) or _contains(v, needle, nested) for k, v in value.items())
    if isinstance(value, list):
        return any(_contains(v, needle, nested) for v in value)
    return False


def _message_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    require(isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict)
            and set(value[0]) == {"type", "text"} and value[0]["type"] == "text"
            and isinstance(value[0]["text"], str), "user_content")
    return value[0]["text"]


class Protocol:
    """All mutable state is locked; an invalid model request terminally fails."""
    def __init__(self, run_id: str):
        self.lock = threading.RLock()
        self.run_id = run_id
        self.scenario: Scenario | None = None
        self.phase = 0
        self.failed: str | None = None
        self.stopped = False
        self.registered_hash: str | None = None
        self.issued: dict[str, tuple[str, str]] = {}
        self.result_hashes: dict[str, str] = {}
        self.checks = {name: False for name in CHECK_NAMES}
        self.requests: list[dict[str, Any]] = []
        self.rejections: dict[str, int] = {}
        self.delivered = 0
        self.scope_hash: str | None = None
        self.scope_components: dict[str, str] = {}

    def register(self, data: bytes) -> dict[str, Any]:
        with self.lock:
            require(self.scenario is None and self.phase == 0 and self.failed is None,
                    "scenario_already_registered", 409)
            obj = strict_json(data, 16384)
            scenario = Scenario.parse(obj)
            self.scenario = scenario
            self.registered_hash = digest(canonical(obj))
            self.checks["scenario_registered_once"] = True
            return self.summary()

    def reject(self, code: str) -> None:
        with self.lock:
            if self.failed is None:
                self.failed = code
            self.rejections[code] = self.rejections.get(code, 0) + 1

    def summary(self) -> dict[str, Any]:
        with self.lock:
            complete = (self.phase == 6 and self.delivered == 6 and self.failed is None
                        and all(self.checks.values()))
            return {
                "schema": 1, "contract": CONTRACT, "runID": self.run_id,
                "scope": "test_provider_protocol_only_not_Apple_or_native_acceptance",
                "state": "failed" if self.failed else "complete" if complete else "awaiting_scenario"
                         if self.scenario is None else "running",
                "complete": complete, "phase": self.phase, "providerRequests": len(self.requests),
                "responsesDelivered": self.delivered, "stopped": self.stopped,
                "scenarioSHA256": self.registered_hash, "observedScopeSHA256": self.scope_hash,
                "observedObjectSHA256": self.scope_components.get("objectReference"),
                "observedSpaceSHA256": self.scope_components.get("spaceReference"),
                "observedRevisionSHA256": self.scope_components.get("sourceRevision"),
                "registeredObjectCompared": self.scenario is not None and self.scenario.object_reference is not None,
                "registeredSpaceCompared": self.scenario is not None and self.scenario.space_reference is not None,
                "checks": dict(self.checks), "failureCode": self.failed,
                "rejections": dict(self.rejections), "requestMetadata": list(self.requests),
            }

    def response_delivered(self, phase: int) -> None:
        with self.lock:
            require(self.delivered == phase and self.phase == phase + 1,
                    "response_delivery_order", 409)
            self.delivered += 1

    def accept(self, data: bytes) -> tuple[int, list[bytes]]:
        with self.lock:
            try:
                require(self.failed is None, "fixture_already_failed", 409)
                require(self.scenario is not None, "scenario_required", 409)
                require(self.phase < 6, "provider_round_overflow", 409)
                require(self.delivered == self.phase, "concurrent_provider_request", 409)
                request = strict_json(data)
                require(isinstance(request, dict), "provider_object")
                require(request.get("model") == MODEL and request.get("stream") is True,
                        "provider_model_or_stream")
                messages = request.get("messages")
                require(isinstance(messages, list) and 1 <= len(messages) <= 64
                        and all(isinstance(m, dict) for m in messages), "provider_messages")
                self._validate_tools(request)
                require(not _contains(request, self.scenario.unselected_text), "unselected_source_disclosed")
                if self.phase <= 1:
                    require(not _contains(request, self.scenario.selected_text), "source_disclosed_before_read_result")
                calls, results = self._validate_history(messages)
                phase = self.phase
                chunks = self._advance(messages, calls, results)
                self.requests.append({"round": phase, "bytes": len(data), "sha256": digest(data),
                                      "messageCount": len(messages), "toolCallCount": len(calls),
                                      "toolResultCount": len(results)})
                self.phase += 1
                return phase, chunks
            except FixtureError as error:
                self.reject(error.code)
                raise

    def _validate_tools(self, request: dict[str, Any]) -> None:
        tools = request.get("tools", [])
        require(isinstance(tools, list) and len(tools) <= 2, "tool_catalog_size")
        schemas = {}
        for tool in tools:
            require(isinstance(tool, dict) and set(tool) == {"type", "function"}
                    and tool["type"] == "function" and isinstance(tool["function"], dict), "tool_descriptor")
            function = tool["function"]
            require(set(function) <= {"name", "description", "parameters", "strict"}, "tool_function_fields")
            name = function.get("name")
            require(name in (READ_TOOL, CREATE_TOOL) and name not in schemas, "tool_alias")
            schema = function.get("parameters")
            require(canonical(schema) == canonical(READ_SCHEMA if name == READ_TOOL else CREATE_SCHEMA), "tool_schema")
            if "strict" in function:
                require(function["strict"] is False, "unexpected_provider_strict_mode")
            schemas[name] = schema
        require(CREATE_TOOL in schemas, "creation_tool_unavailable")
        require((READ_TOOL in schemas) == (self.phase != 0), "read_catalog_consent")

    def _validate_history(self, messages: list[dict[str, Any]]) -> tuple[dict, dict]:
        calls: dict[str, tuple[str, str]] = {}
        results: dict[str, str] = {}
        call_order: dict[str, int] = {}
        for index, message in enumerate(messages):
            require(message.get("role") in ("system", "developer", "user", "assistant", "tool"), "message_role")
            if "tool_calls" in message:
                require(message["role"] == "assistant" and isinstance(message["tool_calls"], list)
                        and 1 <= len(message["tool_calls"]) <= 3, "assistant_tool_calls")
                for call in message["tool_calls"]:
                    require(isinstance(call, dict) and set(call) == {"id", "type", "function"}
                            and call["type"] == "function" and isinstance(call["function"], dict)
                            and set(call["function"]) == {"name", "arguments"}, "assistant_tool_call_shape")
                    identifier = call["id"]
                    require(isinstance(identifier, str) and identifier in self.issued
                            and identifier not in calls, "unissued_or_duplicate_call")
                    current = (call["function"]["name"], call["function"]["arguments"])
                    require(current == self.issued[identifier], "changed_tool_identity_or_arguments")
                    calls[identifier] = current
                    call_order[identifier] = index
            if message["role"] == "tool":
                require(set(message) == {"role", "tool_call_id", "content"}, "tool_result_shape")
                identifier = message["tool_call_id"]
                require(isinstance(identifier, str) and identifier in calls and identifier not in results
                        and call_order[identifier] < index, "orphan_or_duplicate_tool_result")
                text = bounded_string(message["content"], MAX_TOOL_RESULT, "tool_result_size", minimum=0)
                if identifier in self.result_hashes:
                    require(digest(text.encode("utf-8")) == self.result_hashes[identifier], "changed_historical_tool_result")
                results[identifier] = text
        require(set(calls) == set(results), "missing_tool_result")
        return calls, results

    def _expected_continuation(self, messages: list[dict], results: dict, identifier: str) -> str:
        require(identifier in results and messages[-1].get("role") == "tool"
                and messages[-1].get("tool_call_id") == identifier, "wrong_pending_continuation")
        return results[identifier]

    def _expected_send(self, messages: list[dict], prompt: str) -> None:
        require(messages[-1].get("role") == "user"
                and _message_text(messages[-1].get("content")) == prompt, "wrong_send_prompt")

    def _issue(self, identifier: str, name: str, arguments: dict) -> list[bytes]:
        require(identifier not in self.issued, "call_reissued", 409)
        raw = canonical(arguments).decode("utf-8")
        self.issued[identifier] = (name, raw)
        return tool_chunks(identifier, name, raw, identifier="chatcmpl-pinkha-" + str(self.phase))

    def _advance(self, messages: list[dict], calls: dict, results: dict) -> list[bytes]:
        scenario = self.scenario
        assert scenario is not None
        if self.phase == 0:
            self._expected_send(messages, PROMPTS[0])
            require(not calls and not results, "unexpected_denied_history")
            self.checks["denied_read_catalog_omits_read_tool"] = True
            self.checks["denied_read_has_no_source_text"] = True
            return text_chunks(MARKERS[0], identifier="chatcmpl-pinkha-denied")
        if self.phase == 1:
            self._expected_send(messages, PROMPTS[1])
            require(not calls and not results, "unexpected_before_read_history")
            self.checks["allowed_read_exact_schema"] = True
            return self._issue(READ_CALL, READ_TOOL, {})
        if self.phase == 2:
            text = self._expected_continuation(messages, results, READ_CALL)
            value = strict_json(text.encode("utf-8"), MAX_TOOL_RESULT)
            require(isinstance(value, dict) and set(value) == {
                "objectReference", "spaceReference", "sourceRevision", "title", "blocks", "coverage"},
                "selected_snapshot_fields")
            require(value["coverage"] == "selectedTextBlocksOnly" and value["title"] == scenario.document_title,
                    "selected_snapshot_coverage_or_title")
            require(value["blocks"] == [{"reference": scenario.selected_block_id, "text": scenario.selected_text}],
                    "selected_snapshot_block_or_text")
            for key in ("objectReference", "spaceReference", "sourceRevision"):
                bounded_string(value[key], 1024, "selected_snapshot_scope")
            if scenario.object_reference is not None:
                require(value["objectReference"] == scenario.object_reference, "selected_snapshot_wrong_object")
            if scenario.space_reference is not None:
                require(value["spaceReference"] == scenario.space_reference, "selected_snapshot_wrong_space")
            self.scope_hash = digest(canonical({k: value[k] for k in (
                "objectReference", "spaceReference", "sourceRevision")}))
            self.scope_components = {k: digest(value[k].encode("utf-8")) for k in (
                "objectReference", "spaceReference", "sourceRevision")}
            self.result_hashes[READ_CALL] = digest(text.encode("utf-8"))
            for check in ("read_original_call_identity", "selected_payload_exact_block_and_text",
                          "selected_payload_scope_shape_valid", "unselected_text_never_disclosed",
                          "cancel_creation_exact_title_call"):
                self.checks[check] = True
            return self._issue(CANCEL_CALL, CREATE_TOOL, {"title": scenario.cancelled_title})
        if self.phase == 3:
            text = self._expected_continuation(messages, results, CANCEL_CALL)
            require(text == CANCEL_MESSAGE, "cancel_creation_was_not_refused")
            self.result_hashes[CANCEL_CALL] = digest(text.encode("utf-8"))
            self.checks["cancel_creation_refused"] = True
            return text_chunks(MARKERS[1], identifier="chatcmpl-pinkha-cancelled")
        if self.phase == 4:
            self._expected_send(messages, PROMPTS[2])
            self.checks["allowed_creation_new_exact_call"] = True
            return self._issue(ALLOW_CALL, CREATE_TOOL, {"title": scenario.approved_title})
        text = self._expected_continuation(messages, results, ALLOW_CALL)
        require(text == "", "allowed_creation_not_empty_success")
        self.result_hashes[ALLOW_CALL] = digest(text.encode("utf-8"))
        self.checks["allowed_creation_empty_success"] = True
        self.checks["six_provider_requests_completed"] = True
        return text_chunks(MARKERS[2], identifier="chatcmpl-pinkha-approved")
