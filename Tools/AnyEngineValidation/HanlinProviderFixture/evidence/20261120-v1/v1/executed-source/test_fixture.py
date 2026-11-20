"""Fixture-only controls; never substitutes for the mounted Apple UI test."""
from __future__ import annotations

import argparse
import copy
import http.client
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid

import fixture
from protocol import (ALLOW_CALL, CANCEL_CALL, CANCEL_MESSAGE, CONTRACT, CREATE_SCHEMA,
                      CREATE_TOOL, MARKERS, MODEL, PROMPTS, READ_CALL, READ_SCHEMA, READ_TOOL,
                      FixtureError, Protocol, canonical, digest, strict_json, text_chunks, tool_chunks)

SCENARIO = {
    "selectedBlockID": "selected-native-block-1", "selectedText": "שָׁלוֹם 🙂 literal # - * [x]",
    "unselectedText": "UNSELECTED_PRIVATE_CANARY_7cc127", "documentTitle": "Owned source fixture",
    "cancelledTitle": "Owned cancelled fixture page", "approvedTitle": "Owned approved fixture page",
    "objectReference": "native-owned-source-object", "spaceReference": "native-owned-source-space",
}


def tools(read: bool = True) -> list:
    result = [{"type": "function", "function": {"name": CREATE_TOOL, "parameters": CREATE_SCHEMA}}]
    if read:
        result.append({"type": "function", "function": {"name": READ_TOOL, "parameters": READ_SCHEMA}})
    return copy.deepcopy(result)


def request(messages: list, read: bool = True) -> dict:
    return {"model": MODEL, "stream": True, "tools": tools(read), "messages": copy.deepcopy(messages)}


def user(prompt: str) -> dict:
    return {"role": "user", "content": prompt}


def call(identifier: str, name: str, arguments: dict) -> dict:
    return {"role": "assistant", "tool_calls": [{"id": identifier, "type": "function",
             "function": {"name": name, "arguments": canonical(arguments).decode()}}]}


def result(identifier: str, content: str) -> dict:
    return {"role": "tool", "tool_call_id": identifier, "content": content}


def snapshot() -> dict:
    return {"objectReference": SCENARIO["objectReference"], "spaceReference": SCENARIO["spaceReference"],
            "sourceRevision": "original-native-revision-1", "title": SCENARIO["documentTitle"],
            "coverage": "selectedTextBlocksOnly",
            "blocks": [{"reference": SCENARIO["selectedBlockID"], "text": SCENARIO["selectedText"]}]}


def rounds() -> list[dict]:
    read_history = [user(PROMPTS[1]), call(READ_CALL, READ_TOOL, {}),
                    result(READ_CALL, canonical(snapshot()).decode())]
    cancel_history = read_history + [call(CANCEL_CALL, CREATE_TOOL, {"title": SCENARIO["cancelledTitle"]}),
                                     result(CANCEL_CALL, CANCEL_MESSAGE)]
    allow_history = [user(PROMPTS[2]), call(ALLOW_CALL, CREATE_TOOL, {"title": SCENARIO["approvedTitle"]}),
                    result(ALLOW_CALL, "")]
    return [request([user(PROMPTS[0])], read=False), request([user(PROMPTS[1])]),
            request(read_history), request(cancel_history), request([user(PROMPTS[2])]),
            request(allow_history)]


def prepared(phase: int) -> Protocol:
    state = Protocol(str(uuid.uuid4()))
    state.register(canonical(SCENARIO))
    for value in rounds()[:phase]:
        index, _ = state.accept(canonical(value))
        state.response_delivered(index)
    return state


class ProtocolControls(unittest.TestCase):
    def refuses(self, state, value, code):
        with self.assertRaises(FixtureError) as caught:
            state.accept(value if isinstance(value, bytes) else canonical(value))
        self.assertTrue(caught.exception.code == code, "fixed rejection code mismatch")
        self.assertTrue(state.summary()["state"] == "failed", "rejection did not fail closed")
        self.assertFalse(state.summary()["complete"], "rejected scenario reported complete")

    def test_full_six_round_contract_and_scope(self):
        state = prepared(6)
        value = state.summary()
        self.assertTrue(value["complete"] and value["providerRequests"] == 6)
        self.assertTrue(all(value["checks"].values()))
        self.assertTrue(value["registeredObjectCompared"] and value["registeredSpaceCompared"])
        self.assertTrue(value["observedSpaceSHA256"] == digest(SCENARIO["spaceReference"].encode()))

    def test_final_response_must_actually_be_written(self):
        state = prepared(5)
        phase, chunks = state.accept(canonical(rounds()[5]))
        self.assertTrue(chunks[-1] == b"data: [DONE]\n\n")
        self.assertFalse(state.summary()["complete"])
        state.response_delivered(phase)
        self.assertTrue(state.summary()["complete"])

    def test_read_catalog_cannot_be_present_before_allow(self):
        value = rounds()[0]; value["tools"] = tools()
        self.refuses(prepared(0), value, "read_catalog_consent")

    def test_disclosed_source_even_in_nested_escaped_json_is_refused(self):
        value = rounds()[0]
        value["messages"].insert(0, {"role": "system", "content": json.dumps({"hidden": SCENARIO["selectedText"]})})
        self.refuses(prepared(0), value, "source_disclosed_before_read_result")

    def test_source_in_keys_and_whitespace_prefixed_nested_json_is_refused(self):
        for content in ({SCENARIO["selectedText"]: "value"}, " \n\t" + json.dumps({"x": SCENARIO["selectedText"]})):
            value = rounds()[0]; value["extra"] = content
            self.refuses(prepared(0), value, "source_disclosed_before_read_result")

    def test_unselected_source_cannot_appear_anywhere(self):
        value = rounds()[2]
        value["messages"].insert(0, {"role": "system", "content": SCENARIO["unselectedText"]})
        self.refuses(prepared(2), value, "unselected_source_disclosed")

    def test_schema_boolean_is_not_integer_one(self):
        value = rounds()[1]
        value["tools"][0]["function"]["parameters"]["properties"]["title"]["minLength"] = True
        self.refuses(prepared(1), value, "tool_schema")

    def test_extra_title_argument_cannot_be_advertised(self):
        value = rounds()[1]
        value["tools"][0]["function"]["parameters"]["properties"]["body"] = {"type": "string"}
        self.refuses(prepared(1), value, "tool_schema")

    def test_catalog_alias_is_exact(self):
        value = rounds()[1]; value["tools"][1]["function"]["name"] = "other_read_tool"
        self.refuses(prepared(1), value, "tool_alias")

    def test_call_id_cannot_be_replaced(self):
        value = rounds()[2]; value["messages"][1]["tool_calls"][0]["id"] = "unissued"
        self.refuses(prepared(2), value, "unissued_or_duplicate_call")

    def test_call_arguments_must_be_original_empty_json(self):
        value = rounds()[2]; value["messages"][1]["tool_calls"][0]["function"]["arguments"] = '{"other":1}'
        self.refuses(prepared(2), value, "changed_tool_identity_or_arguments")

    def test_duplicate_call_is_refused(self):
        value = rounds()[2]; value["messages"].insert(2, copy.deepcopy(value["messages"][1]))
        self.refuses(prepared(2), value, "unissued_or_duplicate_call")

    def test_orphan_result_is_refused(self):
        value = rounds()[2]; del value["messages"][1]
        self.refuses(prepared(2), value, "orphan_or_duplicate_tool_result")

    def test_selected_block_id_text_and_count_are_exact(self):
        for change in ("id", "text", "extra"):
            with self.subTest(change=change):
                value = rounds()[2]; payload = snapshot()
                if change == "id": payload["blocks"][0]["reference"] = "different-block"
                if change == "text": payload["blocks"][0]["text"] += " changed"
                if change == "extra": payload["blocks"].append({"reference": "extra", "text": "extra"})
                value["messages"][-1]["content"] = canonical(payload).decode()
                self.refuses(prepared(2), value, "selected_snapshot_block_or_text")

    def test_whole_document_coverage_cannot_satisfy_selected_read(self):
        value = rounds()[2]; payload = snapshot(); payload["coverage"] = "documentTextBlocksOnly"
        value["messages"][-1]["content"] = canonical(payload).decode()
        self.refuses(prepared(2), value, "selected_snapshot_coverage_or_title")

    def test_wrong_object_and_space_are_refused(self):
        for key, code in (("objectReference", "selected_snapshot_wrong_object"),
                          ("spaceReference", "selected_snapshot_wrong_space")):
            with self.subTest(key=key):
                value = rounds()[2]; payload = snapshot(); payload[key] = "different-native-scope"
                value["messages"][-1]["content"] = canonical(payload).decode()
                self.refuses(prepared(2), value, code)

    def test_unregistered_space_is_explicit_and_hashable_not_claimed_equal(self):
        state = Protocol(str(uuid.uuid4())); scenario = dict(SCENARIO); del scenario["spaceReference"]
        state.register(canonical(scenario))
        for value in rounds()[:3]:
            phase, _ = state.accept(canonical(value)); state.response_delivered(phase)
        self.assertFalse(state.summary()["registeredSpaceCompared"])
        self.assertTrue(state.summary()["observedSpaceSHA256"] == digest(SCENARIO["spaceReference"].encode()))

    def test_cancel_cannot_be_empty_success_or_generic_cancel_word(self):
        for content in ("", "cancel", "Creation unavailable; reconcile the original scope before retrying"):
            value = rounds()[3]; value["messages"][-1]["content"] = content
            self.refuses(prepared(3), value, "cancel_creation_was_not_refused")

    def test_allow_cannot_be_refusal_or_fabricated_object(self):
        for content in (CANCEL_MESSAGE, '{"objectId":"fabricated"}'):
            value = rounds()[5]; value["messages"][-1]["content"] = content
            self.refuses(prepared(5), value, "allowed_creation_not_empty_success")

    def test_mutated_previous_result_is_refused(self):
        value = rounds()[3]; value["messages"][2]["content"] += " "
        self.refuses(prepared(3), value, "changed_historical_tool_result")

    def test_missing_or_wrong_pending_result_cannot_advance(self):
        value = rounds()[2]; value["messages"].append(user("unrelated"))
        self.refuses(prepared(2), value, "wrong_pending_continuation")

    def test_duplicate_keys_invalid_utf8_and_surrogates_are_refused(self):
        for data, code in ((b'{"model":"x","model":"y"}', "duplicate_json_key"),
                           (b'\xff', "invalid_json"), (b'{"x":"\\ud800"}', "invalid_json")):
            with self.subTest(code=code): self.refuses(prepared(0), data, code)

    def test_extra_round_invalidates_prior_complete(self):
        self.refuses(prepared(6), rounds()[4], "provider_round_overflow")

    def test_duplicate_registration_cannot_reset(self):
        state = prepared(1)
        with self.assertRaises(FixtureError): state.register(canonical(SCENARIO))
        self.assertTrue(state.phase == 1)

    def test_safe_summary_contains_no_business_payload(self):
        state = prepared(6); encoded = canonical(state.summary())
        for text in SCENARIO.values():
            self.assertFalse(text.encode() in encoded, "business value entered safe metadata")
        self.assertFalse(CANCEL_MESSAGE.encode() in encoded)


class HTTPSControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private = tempfile.TemporaryDirectory(prefix="pinkha-fixture-tests-private-")
        cls.safe = tempfile.TemporaryDirectory(prefix="pinkha-fixture-tests-safe-")
        directory = Path(cls.private.name)
        os.chmod(directory, 0o700)
        root, fingerprint = fixture.generate_identity(directory, OPENSSL)
        cls.base = {"schemaVersion": 1, "contract": CONTRACT, "runID": str(uuid.uuid4()),
                    "privateDirectory": str(directory), "rootCAPath": str(root),
                    "rootCAFingerprintSHA256": fingerprint,
                    "serverCertificatePath": str(directory / "server-cert.pem"),
                    "serverKeyPath": str(directory / "server-key.pem"),
                    "modelKey": "fixture-" + "a" * 40, "controlToken": "control-" + "b" * 40,
                    "safeResultPath": str(Path(cls.safe.name) / "result.json"), "maxAgeSeconds": 60}

    @classmethod
    def tearDownClass(cls):
        cls.private.cleanup(); cls.safe.cleanup()

    def setUp(self):
        self.config = dict(self.base); self.config["runID"] = str(uuid.uuid4())
        self.server = fixture.FixtureServer(self.config, Path(self.private.name) / fixture.CONFIG_NAME)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02})
        self.thread.start()
        self.context = ssl.create_default_context(cafile=self.config["rootCAPath"])
        self.connection = http.client.HTTPSConnection("127.0.0.1", self.server.server_port,
                                                     timeout=3, context=self.context)

    def tearDown(self):
        self.connection.close(); self.server.shutdown(); self.server.server_close()
        self.thread.join(timeout=5)
        self.assertFalse(self.thread.is_alive(), "owned HTTPS thread did not stop")

    def http(self, method, path, data=None, token=None):
        headers = {}
        if token is not None: headers["Authorization"] = "Bearer " + token
        if data is not None: headers["Content-Type"] = "application/json"
        self.connection.request(method, path, data, headers)
        response = self.connection.getresponse()
        content = response.read()
        self.assertTrue(response.getheader("Transfer-Encoding") is None)
        self.assertTrue(response.getheader("Content-Length") == str(len(content)))
        return response.status, content, response.getheader("Content-Type")

    def test_default_untrusted_root_is_rejected_then_explicit_ca_succeeds(self):
        other = http.client.HTTPSConnection("127.0.0.1", self.server.server_port, timeout=3)
        try:
            with self.assertRaises(ssl.SSLCertVerificationError): other.request("GET", "/__fixture/ready")
        finally: other.close()
        status, body, _ = self.http("GET", "/__fixture/ready")
        self.assertTrue(status == 200 and strict_json(body)["ready"] is True)

    def test_certificate_hostname_mismatch_is_not_bypassed(self):
        raw = socket.create_connection(("127.0.0.1", self.server.server_port), timeout=3)
        try:
            with self.assertRaises(ssl.SSLCertVerificationError):
                self.context.wrap_socket(raw, server_hostname="localhost")
        finally: raw.close()

    def test_actual_https_persistent_framing_and_six_rounds(self):
        status, _, _ = self.http("GET", "/__fixture/ready")
        self.assertTrue(status == 200)
        first_socket = self.connection.sock
        status, _, _ = self.http("POST", "/__fixture/scenario", canonical(SCENARIO), self.config["controlToken"])
        self.assertTrue(status == 201 and self.connection.sock is first_socket)
        for value in rounds():
            status, body, kind = self.http("POST", "/v1/chat/completions", canonical(value), self.config["modelKey"])
            self.assertTrue(status == 200 and kind == "text/event-stream; charset=utf-8")
            frames = body.split(b"\n\n")
            self.assertTrue(len(frames) == 4 and frames[-2] == b"data: [DONE]" and frames[-1] == b"")
            for frame in frames[:-2]: strict_json(frame.removeprefix(b"data: "))
        status, body, _ = self.http("GET", "/__fixture/status", token=self.config["controlToken"])
        self.assertTrue(status == 200 and strict_json(body)["complete"] is True)
        self.assertTrue(self.connection.sock is first_socket)

    def test_control_token_cannot_be_used_as_model_key(self):
        status, body, _ = self.http("POST", "/v1/chat/completions", canonical(rounds()[0]), self.config["controlToken"])
        self.assertTrue(status == 401 and strict_json(body)["error"]["code"] == "request_authentication")

    def test_model_key_cannot_read_control_state(self):
        status, body, _ = self.http("GET", "/__fixture/status", token=self.config["modelKey"])
        self.assertTrue(status == 401 and strict_json(body)["error"]["code"] == "request_authentication")

    def test_oversized_declared_body_is_rejected_without_read(self):
        self.connection.putrequest("POST", "/v1/chat/completions")
        self.connection.putheader("Authorization", "Bearer " + self.config["modelKey"])
        self.connection.putheader("Content-Type", "application/json")
        self.connection.putheader("Content-Length", "99999999")
        self.connection.endheaders()
        response = self.connection.getresponse(); body = response.read()
        self.assertTrue(response.status == 413 and strict_json(body)["error"]["code"] == "request_content_length")

    def test_unknown_path_never_reflects_input(self):
        canary = "PRIVATE_PATH_CANARY"
        status, body, _ = self.http("GET", "/" + canary)
        self.assertTrue(status == 404 and canary.encode() not in body)
        self.assertFalse(canary.encode() in canonical(self.server.protocol_state.summary()))

    def test_shutdown_closes_owned_idle_keepalive_and_inflight_body(self):
        status, _, _ = self.http("GET", "/__fixture/ready")
        self.assertTrue(status == 200)
        raw = socket.create_connection(("127.0.0.1", self.server.server_port), timeout=3)
        pending = self.context.wrap_socket(raw, server_hostname="127.0.0.1")
        pending.sendall(("POST /v1/chat/completions HTTP/1.1\r\nHost: 127.0.0.1:"
            + str(self.server.server_port) + "\r\nAuthorization: Bearer " + self.config["modelKey"]
            + "\r\nContent-Type: application/json\r\nContent-Length: 1000\r\n\r\n{").encode())
        try:
            deadline = time.monotonic() + 2
            while len(self.server.owned_sockets) < 2 and time.monotonic() < deadline: time.sleep(0.005)
            self.assertTrue(len(self.server.owned_sockets) == 2)
            self.server.shutdown(); self.server.server_close()
            self.assertFalse(any(t.is_alive() for t in self.server.owned_threads))
        finally: pending.close()


OPENSSL = None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--openssl")
    parser.add_argument("--result", required=True)
    args = parser.parse_args()
    OPENSSL = args.openssl or shutil.which("openssl")
    if OPENSSL is None: raise SystemExit("openssl_unavailable")
    suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(ProtocolControls),
                               unittest.defaultTestLoader.loadTestsFromTestCase(HTTPSControls)])
    started = time.monotonic()
    outcome = unittest.TextTestRunner(verbosity=2).run(suite)
    fixture.atomic_json(Path(args.result), {
        "schema": 1, "scope": "test_fixture_controls_not_Apple_or_native_acceptance",
        "status": "PASS" if outcome.wasSuccessful() else "FAIL", "tests": outcome.testsRun,
        "failures": len(outcome.failures), "errors": len(outcome.errors), "skips": len(outcome.skipped),
        "durationSeconds": round(time.monotonic() - started, 3),
        "sourceHashes": {p.name: digest(p.read_bytes()) for p in
                         (Path(__file__), Path(fixture.__file__), Path(__file__).with_name("protocol.py"))},
    })
    raise SystemExit(0 if outcome.wasSuccessful() else 1)
