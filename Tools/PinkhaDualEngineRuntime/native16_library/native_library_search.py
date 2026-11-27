"""Finite source inverse and original-attachment checks for one Library journey.

This module launches nothing. The existing NativeUI controller still owns the
qualified App, exact two-file runner, original descriptor, one-case XCTest
result, simulator account, and private evidence custody.
"""
from __future__ import annotations

from pathlib import Path
import re
import uuid

TARGET = "PinkhaAnyNativeUITests"
SELECTOR = "NativeLaunchTests/testLibrarySearchReplacementAndColdReopenUseCurrentQuery"
ALLOWANCE = 900
PASS = "PASS_NATIVE_LIBRARY_SEARCH_METHOD_VISUAL_REVIEW_PENDING"
SOURCE_BEFORE = "e32f68676df1330c0255aa7ffa93b71c16f158570250013c607084f440c54375"
SOURCE_AFTER = "31c64474cebf4890050f9077d3c44fac63264d878a77bd6f55811cc407e02422"
SOURCE_PROOF = "docs/validation/20261127-wave2-library-search-ui/source-proof.json"
SOURCE_PROOF_SHA = "0cbdc25d324c981e45f81a4de3bb965c4b96d048fbffcb884c667856d447654b"
ADDITION_SHA = "7aa590a857aded09116f058ccdd080be43185600b8e407597ea995ef17ddadc1"
PHASES = ("alpha-result", "replacement-beta-result", "no-match", "cleared-hierarchy",
          "opened-alpha", "cold-beta-result", "cold-opened-beta")
PREFIX = "native-library-search-"


def qualify_source(c, current, proof_raw):
    c.require(c.sha(current) == SOURCE_AFTER and c.sha(proof_raw) == SOURCE_PROOF_SHA,
              "Exact reviewed Library method and insertion proof required")
    proof = c.decode(proof_raw)
    addition, anchor = proof["additionText"].encode(), proof["anchor"].encode()
    c.require(proof["schema"] == "pinkha-native-library-search-source-preparation/v1"
              and proof["sourceBeforeSHA256"] == SOURCE_BEFORE
              and proof["sourceAfterSHA256"] == SOURCE_AFTER
              and proof["additionSHA256"] == c.sha(addition) == ADDITION_SHA
              and proof["additionBytes"] == len(addition)
              and proof["sourceAfterBytes"] == len(current)
              and proof["insertionCount"] == 1 and current.count(addition) == 1
              and proof["inverseRestoresEveryOriginalByte"] is True
              and proof["all18OriginalMethodBodiesAndHelpersByteIdentical"] is True
              and proof["addedSelector"] == TARGET + "/" + SELECTOR
              and proof["executionTimeAllowanceSeconds"] == ALLOWANCE
              and proof["requiredCapturePhases"] == list(PHASES),
              "The one-method Library source insertion differs")
    restored = current.replace(addition, b"", 1)
    c.require(c.sha(restored) == SOURCE_BEFORE and len(restored) == proof["sourceBeforeBytes"]
              and restored.count(anchor) == 1 and restored.replace(anchor, addition + anchor, 1) == current,
              "Library insertion must restore every original NativeLaunch byte")
    original = re.findall(rb"^    func (test\w+)\(", restored, re.M)
    prepared = re.findall(rb"^    func (test\w+)\(", current, re.M)
    added = SELECTOR.split("/")[-1].encode()
    c.require(len(original) == proof["originalMethodCount"] == 18
              and len(prepared) == proof["preparedMethodCount"] == 19
              and [name.decode() for name in original] == proof["originalTestMethods"]
              and prepared.count(added) == 1
              and [name for name in prepared if name != added] == original,
              "All 18 original NativeLaunch method declarations must remain unchanged")
    return restored


def validate_metadata(c, records):
    c.require(set(records) == set(PHASES), "Seven actual Library capture phases required")
    first = records[PHASES[0]]
    scope = first.get("ownedScope")
    c.require(isinstance(scope, str) and str(uuid.UUID(scope)).upper() == scope,
              "Original owned Library account UUID required")
    suffix = scope.replace("-", "").lower()
    identities = first.get("identities")
    c.require(isinstance(identities, dict) and set(identities) == {"alpha", "beta"},
              "Both mounted document identities required")
    expected = {}
    for key, word in (("alpha", "ראשון"), ("beta", "שני")):
        identity = identities[key]
        c.require(isinstance(identity, dict) and set(identity) == {
            "title", "query", "hierarchyRowIdentifier", "objectIDFromHierarchy", "blockIdentifier", "bodySHA256"
        } and all(isinstance(value, str) and 0 < len(value) <= 1024 for value in identity.values()),
            "Exact bounded original mounted identity fields required")
        query = "library" + key + suffix
        body = "מסמך " + word + " לחיפוש " + query
        c.require(identity["title"] == "Library " + key.capitalize() + " " + suffix
                  and identity["query"] == query and identity["bodySHA256"] == c.sha(body.encode())
                  and identity["hierarchyRowIdentifier"] == "any-native-hierarchy-row-" + identity["objectIDFromHierarchy"]
                  and identity["blockIdentifier"].startswith("any-native-block-")
                  and len(identity["blockIdentifier"]) > len("any-native-block-"),
                  "Native hierarchy/block identity or original document body differs")
        expected[key] = identity
    for key in ("objectIDFromHierarchy", "blockIdentifier"):
        c.require(identities["alpha"][key] != identities["beta"][key], "Distinct native document/block identities required")
    queries = {"alpha-result": expected["alpha"]["query"],
               "replacement-beta-result": expected["beta"]["query"],
               "no-match": "libraryabsent" + suffix, "cleared-hierarchy": "",
               "opened-alpha": expected["alpha"]["query"],
               "cold-beta-result": expected["beta"]["query"],
               "cold-opened-beta": expected["beta"]["query"]}
    search_results = {"alpha-result": "alpha", "replacement-beta-result": "beta", "cold-beta-result": "beta"}
    opened = {"opened-alpha": "alpha", "cold-opened-beta": "beta"}
    common = {"schema", "phase", "ownedScope", "spaceName", "requestedAppLanguage", "queryExpected",
              "queryFieldExists", "queryObserved", "completedColdReopens", "nativeIdentityOrigin",
              "nativeReadExtraCallsByObserver", "testStorageOverrides", "identities", "visibleNativeBlocks"}
    for phase in PHASES:
        row = records[phase]
        c.require(isinstance(row, dict) and common <= set(row) <= common | {"visibleFixtureRows"}
                  and row["schema"] == "any-native-library-search-ui/v1" and row["phase"] == phase
                  and row["ownedScope"] == scope and row["spaceName"] == "Library search UI " + suffix[:8]
                  and row["requestedAppLanguage"] == "he" and row["queryExpected"] == queries[phase]
                  and row["identities"] == identities
                  and row["nativeIdentityOrigin"] == "actual-mounted-hierarchy-and-editor-accessibility"
                  and type(row["nativeReadExtraCallsByObserver"]) is int and row["nativeReadExtraCallsByObserver"] == 0
                  and row["testStorageOverrides"] is False
                  and type(row["completedColdReopens"]) is int
                  and row["completedColdReopens"] == (1 if phase.startswith("cold-") else 0)
                  and type(row["queryFieldExists"]) is bool,
                  "Original Library phase, scope, query, or cold-reopen observation differs")
        if row["queryFieldExists"]:
            c.require(isinstance(row["queryObserved"], str) and len(row["queryObserved"]) <= 1024,
                      "Bounded actual query-field observation required")
        else:
            c.require(row["queryObserved"] is None, "Absent search field must have null observed value")
        visible = row.get("visibleFixtureRows", [])
        c.require(isinstance(visible, list) and len(visible) <= 2
                  and all(isinstance(item, dict) and set(item) == {"label", "identifier", "hittable"}
                          and isinstance(item["label"], str) and len(item["label"]) <= 65536
                          and isinstance(item["identifier"], str) and len(item["identifier"]) <= 1024
                          and type(item["hittable"]) is bool for item in visible),
                  "Bounded actual Library fixture rows required")
        if phase in search_results:
            identity = expected[search_results[phase]]
            c.require(row["queryFieldExists"] and row["queryObserved"] == identity["query"]
                      and len(visible) == 1 and visible[0]["label"].startswith(identity["title"])
                      and visible[0]["hittable"] is True
                      and visible[0]["identifier"] not in {item["hierarchyRowIdentifier"] for item in identities.values()},
                      "Current real FTS result must replace previous results and hierarchy rows")
        elif phase == "no-match":
            c.require(row["queryFieldExists"] and row["queryObserved"] == queries[phase] and visible == [],
                      "Original no-match query must have no fixture result rows")
        elif phase == "cleared-hierarchy":
            c.require(len(visible) == 2
                      and {(item["label"], item["identifier"]) for item in visible}
                      == {(item["title"], item["hierarchyRowIdentifier"]) for item in identities.values()},
                      "Clear must restore both original hierarchy object identifiers")
        else:
            c.require(visible == [], "Opened-document observation cannot retain visible Library result rows")
        blocks = row["visibleNativeBlocks"]
        if phase in opened:
            identity = expected[opened[phase]]
            c.require(blocks == [{"identifier": identity["blockIdentifier"], "bodySHA256": identity["bodySHA256"]}],
                      "Opened current-query result must retain its actual original native block and body")
        else:
            c.require(blocks == [], "The Library observation must be outside the document editor")
    return {"ownedScope": scope, "identities": identities, "phaseOrder": list(PHASES),
            "completedColdReopens": 1, "extraObserverNativeCalls": 0,
            "visualReview": "PENDING", "physicalDevice": "NOT_RUN"}


def attachments(c, directory, udid):
    c.require(directory.is_absolute() and directory.resolve() == directory and not directory.is_symlink(),
              "Canonical private Library attachment directory required")
    manifest_raw = c.raw(directory / "manifest.json", 8 * 1024**2)
    manifest = c.decode(manifest_raw)
    c.require(isinstance(manifest, list), "Original Library attachment manifest required")
    # JSON and PNG intentionally share a human label. Type selects the pair.
    found, paths, records = {}, set(), {}
    for row in manifest:
        c.require(isinstance(row, dict) and isinstance(row.get("attachments", []), list),
                  "Original typed Library attachment rows required")
        for item in row.get("attachments", []):
            human = str(item.get("suggestedHumanReadableName", ""))
            if not human.startswith(PREFIX):
                continue
            name = item.get("exportedFileName")
            c.require(isinstance(name, str) and Path(name).name == name and name not in ("", ".", ".."),
                      "Original Library attachment path escaped")
            kind = Path(name).suffix
            c.require(kind in (".json", ".png", ".txt") and Path(human).suffix == kind,
                      "Original Library attachment type differs")
            options = {PREFIX + phase + ("-private-ax" if kind == ".txt" else ""): phase for phase in PHASES}
            matches = [phase for label, phase in options.items()
                       if re.fullmatch(re.escape(label) + r"(?:_[A-Za-z0-9-]+)*" + re.escape(kind), human)]
            test = str(row.get("testIdentifier", "")).removeprefix(TARGET + "/").removesuffix("()")
            c.require(len(matches) == 1 and test == SELECTOR
                      and str(item.get("deviceId", "")).lower() == udid.lower()
                      and item.get("isAssociatedWithFailure") is False,
                      "Library attachment belongs to another phase/test/device or failed observation")
            phase, path = matches[0], directory / name
            key = (phase, kind)
            c.require(path.resolve() == path and not path.is_symlink() and name not in paths and key not in found,
                      "Duplicate or aliased original Library attachment")
            maximum = {".json": 65536, ".png": 20 * 1024**2, ".txt": 131080}[kind]
            raw = c.raw(path, maximum)
            c.require(len(raw) > 0, "Empty original Library observation")
            record = {"path": str(path), "bytes": len(raw), "sha256": c.sha(raw)}
            if kind == ".json":
                records[phase] = c.decode(raw)
            elif kind == ".png":
                c.require(len(raw) >= 33 and raw[:8] == b"\x89PNG\r\n\x1a\n" and raw[8:16] == b"\x00\x00\x00\rIHDR"
                          and 0 < int.from_bytes(raw[16:20], "big") <= 16384
                          and 0 < int.from_bytes(raw[20:24], "big") <= 16384, "Actual bounded Library PNG required")
                record.update(width=int.from_bytes(raw[16:20], "big"), height=int.from_bytes(raw[20:24], "big"))
            else:
                raw.decode("utf-8")
            paths.add(name)
            found[key] = record
    c.require(set(found) == {(phase, kind) for phase in PHASES for kind in (".json", ".png", ".txt")},
              "Seven typed original JSON, screenshot, and accessibility observation groups required")
    proof = validate_metadata(c, records)
    return {"status": "PASS_ORIGINAL_LIBRARY_OBSERVATIONS_VISUAL_REVIEW_PENDING",
            "manifestSHA256": c.sha(manifest_raw), "metadata": proof,
            "phases": {phase: {kind: found[(phase, kind)] for kind in (".json", ".png", ".txt")} for phase in PHASES},
            "visualReview": "PENDING", "physicalDevice": "NOT_RUN"}
