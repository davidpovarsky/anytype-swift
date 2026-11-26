"""Read-only qualification of original menu and real existing-link navigation."""
from pathlib import Path
import math


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
    matched = []
    for row in manifest:
        for item in row.get("attachments", []):
            if not str(item.get("suggestedHumanReadableName", "")).startswith("semantic-source-existing-link-opening_"):
                continue
            test = str(row.get("testIdentifier", "")).removeprefix(selector.split("/")[0] + "/").removesuffix("()")
            c.require(test == "/".join(selector.split("/")[1:])
                      and str(item.get("deviceId", "")).lower() == device.lower()
                      and item.get("isAssociatedWithFailure") is False,
                      "Existing-link evidence belongs to another test/device")
            name = item.get("exportedFileName")
            c.require(isinstance(name, str) and Path(name).name == name and name not in ("", ".", ".."),
                      "Existing-link attachment path escaped")
            path = directory / name
            c.require(path.resolve() == path and not path.is_symlink(), "Existing-link attachment is aliased")
            value = c.raw(path, 65536)
            matched.append((path, value, c.decode(value)))
    c.require(len({str(x[0]) for x in matched}) == len(matched), "Duplicate attachment alias")
    proof = validate(c, [x[2] for x in matched], phase, binding)
    proof["originalAttachmentSHA256"] = [c.sha(x[1]) for x in matched]
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
