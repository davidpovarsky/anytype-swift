#!/usr/bin/env python3
"""Read/write only a newly created synthetic page on a disposable test engine."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--space-id", required=True)
    parser.add_argument("--expected-account-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-disposable-writes", action="store_true", required=True)
    args = parser.parse_args()
    if not args.endpoint.startswith("http://127.0.0.1:"):
        raise ValueError("Only a loopback test engine is accepted")
    http = urllib.request.build_opener(NoRedirect)

    def request(method, path, body=None):
        raw = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(args.endpoint + path, raw,
                                     {"Content-Type": "application/json"}, method=method)
        try:
            with http.open(req, timeout=10) as response:
                raw = response.read()
                value = json.loads(raw) if raw else {}
                if isinstance(value, dict) and value.get("rejections"):
                    raise RuntimeError("successful HTTP response contains rejections")
                return value
        except urllib.error.HTTPError as error:
            raise RuntimeError("HTTP %s" % error.code) from None

    health = request("GET", "/v1/health")
    if health.get("account") != args.expected_account_id:
        raise RuntimeError("Disposable account identity mismatch")
    summary = {"schemaVersion": 1, "status": "RUNNING", "scope": "synthetic-native-search-component",
               "startedAtUTC": datetime.now(timezone.utc).isoformat(), "runtimeVersion": health.get("version"),
               "scriptSHA256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "checks": []}
    base = "/v1/spaces/" + args.space_id
    oid = None
    try:
        oid = request("POST", base + "/objects", {"type": "page", "initialProperties": {
            "any": {"name": "חיפוש מנוע — בדיקה מלאכותית"}}})["objectId"]
        path = base + "/objects/" + oid + "/editor/editor_blocks/blocks"
        request("POST", path, {"type": "paragraph", "text": "בראשית ברא אלהים — English markerword"})
        request("POST", path, {"type": "paragraph", "text": "שָׁלוֹם עוֹלָם נִקּוּד"})

        def search_case(name, query, expected, mode="fts"):
            deadline = time.monotonic() + 12
            response = {}
            while time.monotonic() < deadline:
                response = request("POST", base + "/search", {"query": query, "mode": mode,
                    "limit": 20, "maxData": -1, "filter": {"id": oid}})
                hits = response.get("hits", [])
                if all(hit.get("objectId") == oid for hit in hits) and any(
                        expected in hit.get("data", "") for hit in hits):
                    summary["checks"].append({"name": name, "status": "PASS",
                        "query": query, "returnedMode": response.get("mode"),
                        "vectorStatus": response.get("vectorStatus"), "hits": len(hits)})
                    return
                time.sleep(0.25)
            summary["checks"].append({"name": name, "status": "FAIL", "query": query,
                "returnedMode": response.get("mode"), "vectorStatus": response.get("vectorStatus")})

        search_case("hebrew_plain_term", "בראשית", "בראשית")
        search_case("hebrew_phrase", '"בראשית ברא"', "בראשית ברא")
        search_case("hebrew_prefix", "ברא*", "בראשית")
        search_case("mixed_language_ascii_term", "markerword", "markerword")
        search_case("pointed_hebrew_literal", "שָׁלוֹם", "שָׁלוֹם")
        search_case("unpointed_query_matches_pointed_text", "שלום", "שָׁלוֹם")
        search_case("hybrid_without_embedder_falls_back", "בראשית", "בראשית", mode="hybrid")
        empty = request("POST", base + "/search", {"query": "בראשית", "mode": "fts",
            "filter": {"id": "synthetic-missing-object"}, "limit": 20})
        summary["checks"].append({"name": "object_filter_excludes_other_objects",
                                  "status": "PASS" if not empty.get("hits") else "FAIL"})
        summary["status"] = ("PASS_NATIVE_SEARCH_COMPONENT" if all(
            check["status"] == "PASS" for check in summary["checks"]) else "FAIL_NATIVE_SEARCH_COMPONENT")
    except Exception as error:
        summary["status"] = "FAIL_NATIVE_SEARCH_COMPONENT"
        summary["fatalFailure"] = str(error) if isinstance(error, RuntimeError) else type(error).__name__
    finally:
        if oid:
            try:
                request("DELETE", base + "/objects/" + oid)
                summary["cleanup"] = "synthetic-page-delete-accepted"
            except Exception:
                summary["cleanup"] = "synthetic-page-delete-not-confirmed"
        summary["finishedAtUTC"] = datetime.now(timezone.utc).isoformat()
        summary["limitations"] = ["Synthetic lexical examples, not relevance benchmarking.",
            "No local or network embedding model used; semantic retrieval is not validated."]
        Path(args.output).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 0 if summary["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
