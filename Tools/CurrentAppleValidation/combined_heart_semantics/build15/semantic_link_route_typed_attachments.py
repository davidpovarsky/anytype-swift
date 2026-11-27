"""Read-only qualification of original menu and real existing-link navigation."""
from pathlib import Path
import math
import re


def validate(c, rows, phase, binding):
    c.require(phase in ("linked", "unlinked") and len(rows) == 2,
              "Exactly two actual later semantic-link openings are required")
    keys = {"protocol", "sourceSHA", "runID", "runAttempt", "nonce", "budgetSeconds",
            "realSemanticLinkTaps", "nativeMenuActionTaps", "selectionKeysSent", "status",
            "admittedElapsedSeconds", "elapsedSeconds"}
    for row in rows:
        c.require(set(row) == keys and row["protocol"] == "pinkha-semantic-existing-link-opening-v1"
                  and all(row[k] == binding[k] for k in binding)
                  and row["status"] == "OPENED_EXISTING_SEMANTIC_LINK"
                  and all(type(row[k]) is int for k in ("budgetSeconds", "realSemanticLinkTaps",
                                                       "nativeMenuActionTaps", "selectionKeysSent"))
                  and row["budgetSeconds"] == 20 and row["realSemanticLinkTaps"] == 1
                  and row["nativeMenuActionTaps"] == row["selectionKeysSent"] == 0,
                  "Actual existing semantic-link route identity or action differs")
        a, e = row["admittedElapsedSeconds"], row["elapsedSeconds"]
        c.require(all(type(x) in (int, float) and math.isfinite(x) for x in (a, e))
                  and 0 <= a <= 20 and e >= a,
                  "Actual existing-link admission exceeded its original deadline")
    return {"status": "PASS_TWO_ACTUAL_EXISTING_SEMANTIC_LINK_OPENINGS",
            "phase": phase, "realSemanticLinkTaps": 2, "nativeMenuActionTaps": 0,
            "selectionKeysSentBehindSheet": 0, "originalOutcomeAssertionsChanged": False}


def qualify_routes(c, policy, directory, selector, device, phase, binding):
    manifest = c.decode(c.raw(directory / "manifest.json", 8 * 1024**2))
    c.require(isinstance(manifest, list), "Original attachment manifest required")
    matched, screenshots, paths = [], [], set()
    for row in manifest:
        for item in row.get("attachments", []):
            human_name = str(item.get("suggestedHumanReadableName", ""))
            if not human_name.startswith("semantic-source-existing-link-opening_"):
                continue
            test = str(row.get("testIdentifier", "")).removeprefix(selector.split("/")[0] + "/").removesuffix("()")
            c.require(test == "/".join(selector.split("/")[1:])
                      and str(item.get("deviceId", "")).lower() == device.lower()
                      and item.get("isAssociatedWithFailure") is False,
                      "Existing-link evidence belongs to another test/device")
            name = item.get("exportedFileName")
            c.require(isinstance(name, str) and Path(name).name == name and name not in ("", ".", ".."),
                      "Existing-link attachment path escaped")
            kind = Path(name).suffix
            c.require(kind in (".json", ".png") and Path(human_name).suffix == kind
                      and re.fullmatch(r"semantic-source-existing-link-opening_[0-9]+_[0-9A-Fa-f-]{36}\.(json|png)",
                                       human_name) is not None,
                      "Existing-link attachment kind or exported name differs")
            path = directory / name
            c.require(path.resolve() == path and not path.is_symlink(), "Existing-link attachment is aliased")
            c.require(str(path) not in paths, "Duplicate attachment alias")
            paths.add(str(path))
            if kind == ".json":
                value = c.raw(path, 65536)
                matched.append((path, value, c.decode(value)))
            else:
                value = c.raw(path, 20 * 1024**2)
                c.require(len(value) >= 33 and value[:8] == b"\x89PNG\r\n\x1a\n"
                          and value[8:16] == b"\x00\x00\x00\rIHDR"
                          and 0 < int.from_bytes(value[16:20], "big") <= 16384
                          and 0 < int.from_bytes(value[20:24], "big") <= 16384,
                          "Original existing-link PNG screenshot required")
                screenshots.append((path, value))
    c.require(len(screenshots) == 2, "Exactly two original existing-link screenshots required")
    proof = validate(c, [x[2] for x in matched], phase, binding)
    proof["originalAttachmentSHA256"] = [c.sha(x[1]) for x in matched]
    proof["originalScreenshotSHA256"] = [c.sha(x[1]) for x in screenshots]
    proof["originalScreenshotCount"] = len(screenshots)
    if phase == "linked":
        raw, origin = policy.attachment(directory, "semantic-source-menu-navigation", selector, device, maximum=65536)
        menu = c.decode(raw)
        c.require(menu["protocol"] == "pinkha-semantic-source-menu-v1"
                  and all(menu[k] == binding[k] for k in binding)
                  and menu["status"] == "TAPPED_ORIGINAL_SOURCE_ACTION"
                  and type(menu["sourceActionTaps"]) is int and menu["sourceActionTaps"] == 1
                  and type(menu["nextPageTaps"]) is int and 0 <= menu["nextPageTaps"] <= 3
                  and menu["budgetSeconds"] == 20,
                  "The first original native Sources-menu action must remain actually exercised")
        proof["firstOriginalNativeMenuActionSHA256"] = c.sha(raw)
        proof["firstOriginalNativeMenuActionTaps"] = 1
    return proof
