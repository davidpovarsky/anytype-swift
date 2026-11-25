"""Exact original mounted observation predicates, bound to combined70fb.

The original standalone154 verifier is untouched. This specialized verifier
changes only the runtime equality to the actual one-Go manifest70fb identity.
Original overlay154, all original CAS/event/mark/process/count predicates,
and the original fixture deadline remain byte-for-byte equivalent.
"""
from __future__ import annotations
import base64
import hashlib
import json
import consumer_contract as native
from mounted_contract import fixture, native_block, snapshot, PROTOCOL, PASS, CAPTURE_CHECKS, REOPEN_CHECKS
require = native.require
ORIGINAL_OVERLAY = "2f76212f9fcd749aeb9e806b941e0fd0b54eba17e5cc842adb81c7eb3bae0f38"
COMBINED_VERSION = "pinkha-dual-runtime-v1-70fb5342f2ff31d1cf5f7ce44bed7b16f6373f6bf95eb031d165339cf0f26683"
ORIGIN_SOURCE_COMMIT = "39f0076780412c77f55c675d69bf7ca1ee35ea89"
ORIGIN_FUNCTION_SHA256 = "a922558044f3f5cca25087fc7a96027590bd48aeebe9ee3bdac264963b561e91"

def observations(fixture_value, capture, reopen, capture_raw, binding, *, now=None):
    before = fixture(fixture_value, binding, now=now)
    require(json.loads(capture_raw) == capture, "Capture receipt byte binding differs")
    for value, mode, phase, checks in ((capture, "capture", "PASS_CAPTURE_MOUNTED", CAPTURE_CHECKS),
                                        (reopen, "reopen", "PASS_COLD_REOPEN_MOUNTED", REOPEN_CHECKS)):
        require(value.get("protocol") == PROTOCOL and value.get("phase") == phase and value.get("mode") == mode
                and all(value.get(k) == binding[k] for k in binding), "Mounted observation source/phase differs")
        require(all(value.get(k) == fixture_value[k] for k in ("accountID", "spaceID", "objectID", "blockID",
                    "excludedBlockID", "preparationProcessID")), "Mounted observation identity differs")
        require(value.get("runtimeVersion") == COMBINED_VERSION and value.get("nativeManifestSHA256") == native.MANIFEST_SHA
                and native.uuid(value.get("generation")) and type(value.get("processID")) is int and value["processID"] > 1,
                "Actual runtime/generation/process missing")
        require(value.get("failure") is None and isinstance(value.get("checks"), dict) and set(value["checks"]) == checks
                and all(item is True for item in value["checks"].values()), "Incomplete mounted observations")
        require(type(value.get("startedAt")) in (int, float) and type(value.get("finishedAt")) in (int, float)
                and value["finishedAt"] >= value["startedAt"], "Original observation timestamps missing")
    require(capture.get("preparations") == 2 and capture.get("cancellations") == 1 and capture.get("applyAttempts") == 1
            and capture.get("documentPublications") == 1 and capture.get("publicationGeneration") == capture["generation"],
            "One explicit native document publication required")
    for value in (capture, reopen):
        require(all(type(value.get(k)) is int for k in ("preparations", "cancellations", "applyAttempts", "documentPublications")),
                "Noninteger operation count")
    require(capture.get("selection") == {"blockID": fixture_value["blockID"], "location": 0, "length": 6,
                "visibleTextSHA256": hashlib.sha256(b"Anchor").hexdigest()}, "Actual UIKit selection differs")
    require(capture.get("cancelNativeBlockSHA256") == hashlib.sha256(native.decode64(fixture_value["beforeBlockBase64"])).hexdigest(),
            "Cancel did not preserve original native block")
    receipt = capture.get("native")
    native.keys(receipt, {"anchorID", "marker", "changeID", "nativeChangeSHA256",
                           "beforeTextMarksSHA256", "afterTextMarksSHA256"})
    require(native.uuid(receipt["anchorID"]), "Actual anchor UUID missing")
    component = lambda text: base64.urlsafe_b64encode(text.encode("utf8")).decode("ascii").rstrip("=")
    marker = "pinkha-anchor://v1/" + component(fixture_value["spaceID"]) + "/" + component(fixture_value["objectID"]) + "/" + receipt["anchorID"]
    cancelled = capture.get("cancelledMarker")
    prefix = marker.rsplit("/", 1)[0] + "/"
    require(receipt["marker"] == marker and isinstance(cancelled, str) and cancelled.startswith(prefix)
            and native.uuid(cancelled.removeprefix(prefix)) and cancelled != marker,
            "Confirmed anchor reused cancelled or foreign intent")
    native.identity(receipt["changeID"]); native.hex_value(receipt["nativeChangeSHA256"])
    after = native_block(native.decode64(capture["afterBlockBase64"]), fixture_value["blockID"], "Anchor")
    require(after["marks"] == before["marks"] + [{"from": 0, "to": 6, "kind": 5, "param": marker}],
            "Original ordered native marks or added anchor differs")
    require([x[3] for x in before["fields"] if x[0] != 14] == [x[3] for x in after["fields"] if x[0] != 14]
            and [x[3] for x in before["body"] if x[0] != 3] == [x[3] for x in after["body"] if x[0] != 3],
            "Opaque non-mark native block bytes changed")
    require(receipt["beforeTextMarksSHA256"] == snapshot("Anchor", before["marks"])
            and receipt["afterTextMarksSHA256"] == snapshot("Anchor", after["marks"]),
            "Actual native digest disagrees with original protobuf")
    for value in (capture, reopen):
        require(native.decode64(value["documentMarksBase64"]) == after["raw_marks"]
                and value["renderedLinks"] == [{"marker": marker, "location": 0, "length": 6}],
                "Actual document/rendered link differs")
    require(len({fixture_value["preparationProcessID"], capture["processID"], reopen["processID"]}) == 3
            and reopen.get("captureProcessID") == capture["processID"] and reopen["generation"] != capture["generation"],
            "Preparation/capture/cold reopen are not distinct owned processes")
    require(reopen.get("preparations") == reopen.get("cancellations") == reopen.get("applyAttempts") ==
            reopen.get("documentPublications") == 0 and reopen.get("native") == receipt
            and reopen.get("afterBlockBase64") == capture["afterBlockBase64"]
            and reopen.get("captureReceiptSHA256") == hashlib.sha256(capture_raw).hexdigest(),
            "Cold reopen mutated, changed native data or lost original receipt identity")
    return {"status": PASS, "binding": binding, "capture_process_id": capture["processID"],
            "reopen_process_id": reopen["processID"], "native_change_id": receipt["changeID"],
            "native_change_sha256": receipt["nativeChangeSHA256"],
            "capture_receipt_sha256": hashlib.sha256(capture_raw).hexdigest(),
            "limitations": {"physicalDevice": "NOT_RUN", "shipping": "OFF", "fullProductAcceptance": False}}
