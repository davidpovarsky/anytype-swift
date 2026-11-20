#!/usr/bin/env python3
"""Read-only, bounded extraction of the Runtime schema-2 diagnostic prefix.

This tool never performs HTTP requests, executes tests, changes a session, or
copies the raw input log. Its outputs contain only fixed, allowlisted metadata.
"""
import argparse
import collections
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PREFIX = b"PINKHA_RUNTIME_HTTP_METRICS "
MAX_LOG_BYTES = 128 * 1024 * 1024
MAX_LINE_BYTES = 1024 * 1024
MAX_EVENT_BYTES = 128 * 1024
MAX_MARKERS = 512
MAX_EVENTS = 256
MAX_OBSERVATIONS = 128
PRODUCER_SOURCE_SHA256 = "39cfc7ba724c407421fc0174b438f93d7807a2c02e986e079d522be982dc8585"
UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z")

def sha(path, max_bytes=None):
    h = hashlib.sha256()
    total = 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            total += len(block)
            if max_bytes is not None and total > max_bytes:
                raise ValueError("hash_input_byte_limit_exceeded")
            h.update(block)
    return h.hexdigest()

def integer(value, low=0):
    return type(value) is int and low <= value <= 9223372036854775807

def real(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1e15

def date(value):
    return value is None or real(value)

def choice(*values):
    return lambda value: type(value) is str and value in values

BOOL = lambda value: type(value) is bool
INT = lambda value: integer(value)
COUNT = lambda value: integer(value, -1)
SIGNED = lambda value: integer(value, -9223372036854775808)
STATUS = lambda value: integer(value) and 100 <= value <= 599
BASE = {
    "schemaVersion": lambda value: type(value) is int and value == 2,
    "observationID": lambda value: type(value) is str and bool(UUID.fullmatch(value)),
    "route": choice("health", "auth", "spaces", "pinkha/capabilities", "other"),
    "phase": choice("start", "end", "error"),
    "timestampUnixMs": real, "elapsedMonotonicMs": real,
    "metricsCallbackCount": INT, "metricsAvailableAtEmit": BOOL,
    "expectedContentLength": COUNT, "returnedBodyByteCount": INT,
    "status": STATUS,
    "errorDomain": choice("NSURLErrorDomain", "NSCocoaErrorDomain", "NSPOSIXErrorDomain", "other"),
    "errorCode": SIGNED,
}
REQUIRED_BASE = set(BASE) - {
    "expectedContentLength", "returnedBodyByteCount", "status", "errorDomain", "errorCode"
}
METRICS = {
    "callbackTimestampUnixMs": real, "callbackElapsedMonotonicMs": real,
    "taskIdentifier": INT,
    "taskIntervalStartUnixMs": date, "taskIntervalEndUnixMs": date,
    "taskDurationMs": real, "redirectCount": INT, "transactionCount": INT,
    "omittedTransactionCount": INT, "taskBytesSent": COUNT,
    "taskBytesReceived": COUNT, "taskExpectedBytesToReceive": COUNT,
    "expectedContentLength": COUNT, "status": STATUS,
}
REQUIRED_METRICS = set(METRICS) - {"expectedContentLength", "status"}
TRANSACTION = {
    **{key: date for key in (
        "fetchStartUnixMs", "domainLookupStartUnixMs", "domainLookupEndUnixMs",
        "connectStartUnixMs", "connectEndUnixMs", "secureConnectionStartUnixMs",
        "secureConnectionEndUnixMs", "requestStartUnixMs", "requestEndUnixMs",
        "responseStartUnixMs", "responseEndUnixMs"
    )},
    "protocol": choice("unknown", "other", "http/1.0", "http/1.1", "h2", "h3"),
    "reusedConnection": BOOL, "proxyConnection": BOOL, "resourceFetchType": INT,
    **{key: COUNT for key in (
        "requestHeaderBytesSent", "requestBodyBytesSent", "requestBodyBytesBeforeEncoding",
        "responseHeaderBytesReceived", "responseBodyBytesReceived", "responseBodyBytesAfterDecoding"
    )},
    "responsePresent": BOOL, "expectedContentLength": COUNT, "status": STATUS,
}
REQUIRED_TRANSACTION = set(TRANSACTION) - {"expectedContentLength", "status"}

class InvalidEvent(Exception):
    pass

def pick(value, fields, required, extra=()):
    if type(value) is not dict or not required.issubset(value):
        raise InvalidEvent("missing_or_nonobject_fields")
    if any(not validator(value[key]) for key, validator in fields.items() if key in value):
        raise InvalidEvent("invalid_scalar")
    return ({key: value[key] for key in fields if key in value},
            len(set(value) - set(fields) - set(extra)))

def sanitize(value):
    if type(value) is not dict or type(value.get("schemaVersion")) is not int:
        raise InvalidEvent("missing_schema")
    if value["schemaVersion"] != 2:
        raise InvalidEvent("other_schema_ignored")
    if value.get("phase") == "diagnostic_encode_failed":
        return {"schemaVersion": 2, "phase": "diagnostic_encode_failed"}, max(0, len(value) - 2)
    event, unknown = pick(value, BASE, REQUIRED_BASE, ("metrics",))
    if "metrics" not in value:
        raise InvalidEvent("missing_metrics_field")
    metrics = value["metrics"]
    if metrics is None:
        if event["metricsAvailableAtEmit"] or event["metricsCallbackCount"] != 0:
            raise InvalidEvent("incoherent_metrics_snapshot")
        event["metrics"] = None
    else:
        if not event["metricsAvailableAtEmit"] or event["metricsCallbackCount"] < 1:
            raise InvalidEvent("incoherent_metrics_snapshot")
        cleaned, more = pick(metrics, METRICS, REQUIRED_METRICS, ("transactions",))
        unknown += more
        transactions = metrics.get("transactions")
        if type(transactions) is not list or len(transactions) > 16:
            raise InvalidEvent("unbounded_or_missing_transactions")
        expected = min(16, cleaned["transactionCount"])
        if len(transactions) != expected or cleaned["omittedTransactionCount"] != max(0, cleaned["transactionCount"] - 16):
            raise InvalidEvent("incoherent_transaction_count")
        cleaned["transactions"] = []
        for row in transactions:
            clean_row, more = pick(row, TRANSACTION, REQUIRED_TRANSACTION)
            cleaned["transactions"].append(clean_row)
            unknown += more
        event["metrics"] = cleaned
    if event["phase"] == "end" and not {"expectedContentLength", "returnedBodyByteCount"}.issubset(event):
        raise InvalidEvent("missing_end_fields")
    if event["phase"] == "error" and not {"errorDomain", "errorCode"}.issubset(event):
        raise InvalidEvent("missing_error_fields")
    if event["phase"] == "start" and event["metrics"] is not None:
        raise InvalidEvent("unexpected_start_metrics")
    return event, unknown

def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidEvent("duplicate_json_key")
        result[key] = value
    return result

def extract(path):
    events, rejected = [], []
    counts = collections.Counter()
    before = path.stat()
    if before.st_size > MAX_LOG_BYTES:
        raise ValueError("input_exceeds_128_MiB_limit")
    hasher = hashlib.sha256()
    decoder = json.JSONDecoder(object_pairs_hook=no_duplicate_keys)
    line_no = 0
    total = 0
    with path.open("rb") as stream:
        while block := stream.readline(MAX_LINE_BYTES + 1):
            line_no += 1
            total += len(block)
            hasher.update(block)
            if total > MAX_LOG_BYTES:
                raise ValueError("input_grew_past_128_MiB_limit")
            if len(block) > MAX_LINE_BYTES:
                counts["overlongPhysicalLines"] += 1
                while not block.endswith(b"\n"):
                    block = stream.readline(MAX_LINE_BYTES + 1)
                    if not block:
                        break
                    total += len(block)
                    hasher.update(block)
                    if total > MAX_LOG_BYTES:
                        raise ValueError("input_grew_past_128_MiB_limit")
                continue
            marker_count = block.count(PREFIX)
            if not marker_count:
                continue
            counts["prefixMarkers"] += marker_count
            if counts["prefixMarkers"] > MAX_MARKERS:
                raise ValueError("prefix_marker_limit_exceeded")
            if marker_count != 1:
                rejected.append({"line": line_no, "reason": "multiple_markers_not_reconstructed"})
                continue
            payload = block.split(PREFIX, 1)[1]
            if len(payload) > MAX_EVENT_BYTES:
                rejected.append({"line": line_no, "reason": "event_byte_limit_exceeded"})
                continue
            try:
                text = payload.decode("utf-8")
                value, end = decoder.raw_decode(text.lstrip())
                event, unknown = sanitize(value)
                if len(events) >= MAX_EVENTS:
                    raise ValueError("accepted_event_limit_exceeded")
                event = {"sourceLine": line_no, **event}
                if text.lstrip()[end:].strip():
                    counts["eventsWithUncopiedTrailingText"] += 1
                    event["trailingNonWhitespacePresent"] = True
                counts["discardedUnknownFieldCount"] += unknown
                events.append(event)
            except InvalidEvent as error:
                rejected.append({"line": line_no, "reason": str(error)})
            except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
                rejected.append({"line": line_no, "reason": "incomplete_or_invalid_json_not_reconstructed"})
    after = path.stat()
    if after.st_size > MAX_LOG_BYTES:
        raise ValueError("input_grew_past_128_MiB_limit")
    after_hash = sha(path, MAX_LOG_BYTES)
    stable = (before.st_size == after.st_size == total
              and before.st_mtime_ns == after.st_mtime_ns
              and hasher.hexdigest() == after_hash)
    return events, rejected, dict(counts), {
        "path": str(path), "bytesRead": total, "linesRead": line_no,
        "sha256AtRead": hasher.hexdigest(), "sha256After": after_hash,
        "sizeBefore": before.st_size, "sizeAfter": after.st_size,
        "stableDuringRead": stable,
    }

def delta(later, earlier):
    return None if later is None or earlier is None else round(later - earlier, 3)

def request_summary(observation_id, events):
    starts = [x for x in events if x["phase"] == "start"]
    terminals = [x for x in events if x["phase"] in ("end", "error")]
    result = {
        "observationID": observation_id,
        "routeLabels": sorted({x["route"] for x in events}),
        "sourceLines": [x["sourceLine"] for x in events],
        "startCount": len(starts), "terminalCount": len(terminals),
        "unambiguousPair": len(starts) == len(terminals) == 1
                           and len({x["route"] for x in events}) == 1
                           and starts[0]["sourceLine"] < terminals[0]["sourceLine"],
    }
    if len(terminals) != 1:
        result["awaitBoundary"] = "TERMINAL_NOT_OBSERVED" if not terminals else "AMBIGUOUS_TERMINALS"
        return result
    terminal = terminals[0]
    for key in (
        "phase", "timestampUnixMs", "elapsedMonotonicMs", "status",
        "errorDomain", "errorCode", "expectedContentLength", "returnedBodyByteCount",
        "metricsAvailableAtEmit", "metricsCallbackCount"
    ):
        if key in terminal:
            result[key] = terminal[key]
    result["awaitBoundary"] = "DATA_AWAIT_RETURNED" if terminal["phase"] == "end" else "DATA_AWAIT_THROWN"
    if len(starts) == 1:
        result["startTimestampUnixMs"] = starts[0]["timestampUnixMs"]
        result["observedAwaitWallMs"] = delta(terminal["timestampUnixMs"], starts[0]["timestampUnixMs"])
        result["observedAwaitMonotonicMs"] = delta(terminal["elapsedMonotonicMs"], starts[0]["elapsedMonotonicMs"])
    metrics = terminal["metrics"]
    if metrics is None:
        result["metricsBoundary"] = "UNKNOWN_ABSENT_AT_TERMINAL_SNAPSHOT"
        return result
    result["metricsBoundary"] = "LATEST_BOUNDED_CALLBACK_SNAPSHOT"
    result["latestSnapshotOnly"] = metrics["transactionCount"] > 16 or terminal["metricsCallbackCount"] > 1
    result["callbackTimestampUnixMs"] = metrics["callbackTimestampUnixMs"]
    result["callbackToTerminalMonotonicMs"] = delta(terminal["elapsedMonotonicMs"], metrics["callbackElapsedMonotonicMs"])
    result["callbackToTerminalWallMs"] = delta(terminal["timestampUnixMs"], metrics["callbackTimestampUnixMs"])
    result["taskIntervalEndToTerminalWallMs"] = delta(terminal["timestampUnixMs"], metrics["taskIntervalEndUnixMs"])
    result["task"] = {key: value for key, value in metrics.items() if key != "transactions"}
    result["transactions"] = []
    for index, row in enumerate(metrics["transactions"]):
        item = {"index": index, **row}
        item["requestStartToEndWallMs"] = delta(row["requestEndUnixMs"], row["requestStartUnixMs"])
        item["requestEndToFirstResponseByteWallMs"] = delta(row["responseStartUnixMs"], row["requestEndUnixMs"])
        item["firstToLastResponseByteWallMs"] = delta(row["responseEndUnixMs"], row["responseStartUnixMs"])
        item["lastResponseByteToTerminalWallMs"] = delta(terminal["timestampUnixMs"], row["responseEndUnixMs"])
        item["requestStartObserved"] = row["requestStartUnixMs"] is not None
        item["responseFirstByteTimeObserved"] = row["responseStartUnixMs"] is not None
        item["responseLastByteTimeObserved"] = row["responseEndUnixMs"] is not None
        item["negativeDerivedIntervalPresent"] = any(
            value is not None and value < 0 for key, value in item.items() if key.endswith("WallMs")
        )
        result["transactions"].append(item)
    result["negativeDerivedObservationIntervalPresent"] = any(
        type(value) in (int, float) and value < 0
        for key, value in result.items() if key.endswith(("WallMs", "MonotonicMs"))
    )
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True, type=Path, help="Actual closed Apple job log; read-only.")
    parser.add_argument("--output-dir", required=True, type=Path, help="New directory for sanitized metadata only.")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--job-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_commit):
        parser.error("--source-commit must be the externally verified 40-character commit")
    if any(not re.fullmatch(r"[0-9]{1,20}", value) for value in (args.run_id, args.job_id)):
        parser.error("run/job IDs must be numeric")
    log = args.log.resolve(strict=True)
    output = args.output_dir.resolve()
    if output.exists():
        parser.error("--output-dir must not exist; prior observations are immutable")
    self_hash = sha(Path(__file__).resolve())
    events, rejected, counts, input_info = extract(log)
    groups = collections.defaultdict(list)
    for event in events:
        if "observationID" in event:
            groups[event["observationID"]].append(event)
    if len(groups) > MAX_OBSERVATIONS:
        raise ValueError("observation_limit_exceeded")
    requests = [request_summary(key, rows) for key, rows in groups.items()]
    complete = (input_info["stableDuringRead"] and not rejected
                and not counts.get("overlongPhysicalLines")
                and not counts.get("discardedUnknownFieldCount")
                and not any(x["phase"] == "diagnostic_encode_failed" for x in events)
                and all(x["unambiguousPair"] for x in requests))
    source_stable = self_hash == sha(Path(__file__).resolve())
    status = ("NO_SCHEMA2_EVENTS_OBSERVED" if not events else
              "EXTRACTED_METADATA_ONLY" if complete and source_stable else
              "PARTIAL_OR_AMBIGUOUS_METADATA_ONLY")
    report = {
        "schemaVersion": 1, "status": status,
        "generatedAtUTC": datetime.now(timezone.utc).isoformat(),
        "executionClaim": "NONE: this extractor does not execute or certify tests",
        "sourceProvenance": {
            "claimedCommit": args.source_commit, "claimedRunID": args.run_id, "claimedJobID": args.job_id,
            "expectedProducerTestSHA256": PRODUCER_SOURCE_SHA256,
            "verifiedByExtractor": False,
            "note": "Commit/job and expected producer binding require the independent CI source/artifact receipt.",
        },
        "extractor": {"path": str(Path(__file__).resolve()), "sha256": self_hash, "stable": source_stable},
        "input": input_info,
        "bounds": {"maxLogBytes": MAX_LOG_BYTES, "maxLineBytes": MAX_LINE_BYTES,
                   "maxEventBytes": MAX_EVENT_BYTES, "maxPrefixMarkers": MAX_MARKERS,
                   "maxAcceptedEvents": MAX_EVENTS, "maxObservations": MAX_OBSERVATIONS,
                   "maxTransactionsPerSnapshot": 16},
        "counts": {**counts, "acceptedEvents": len(events), "rejectedEvents": len(rejected),
                   "observations": len(requests), "awaitReturned": sum(x.get("phase") == "end" for x in requests),
                   "awaitThrew": sum(x.get("phase") == "error" for x in requests),
                   "missingTerminalMetrics": sum(x.get("metricsAvailableAtEmit") is False for x in requests)},
        "rejected": rejected, "requests": requests,
        "interpretationLimits": [
            "No root cause or transport fix is inferred. A passing instrumented run does not erase earlier failures.",
            "Response object/status, task byte counters, and native access logs do not prove delivery of a complete body to the await.",
            "Missing metrics or responseEnd is unknown. Reused connections can normally omit DNS/connect dates.",
            "ResponseStart marks the first byte, not necessarily complete response headers.",
            "Task, wire, decoded and expected byte counters are distinct. No content-length comparison or cross-transaction sum is performed.",
            "Only the latest callback snapshot and first sixteen transactions are retained; multiple callbacks or omissions limit coverage.",
            "Callback-to-terminal intervals describe observations, not a proven queue bottleneck. Negative wall intervals are flagged.",
            "No log lines or JSON are reconstructed after interleaving/truncation. Unprefixed text and unknown fields are never copied.",
            "Diagnostic output before dispatch and after await may perturb timing, although the metrics callback performs no output.",
        ],
    }
    output.mkdir(parents=True, exist_ok=False)
    event_path = output / "events.sanitized.jsonl"
    event_path.write_text("".join(json.dumps(x, sort_keys=True, ensure_ascii=True) + "\n" for x in events), encoding="utf-8")
    report["sanitizedEventsSHA256"] = sha(event_path)
    report_path = output / "analysis.json"
    report_path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "observations": len(requests), "acceptedEvents": len(events),
                      "rejectedEvents": len(rejected), "inputStable": input_info["stableDuringRead"],
                      "analysisSHA256": sha(report_path)}, sort_keys=True))
    return 0 if complete and source_stable and events else 2

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        # Never echo arbitrary input, filesystem exceptions, or log contents.
        print(json.dumps({"status": "EXTRACTION_FAILED", "errorType": type(error).__name__}), file=sys.stderr)
        sys.exit(2)
