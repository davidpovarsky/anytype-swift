"""Finite observations for the two published Styled NativeUI methods.

This module launches nothing and does not admit a product or an XCTest result.
The original runner must first qualify source/products, the selected descriptor,
the real process exit, and the exact one-case result/device. These checks bind
its retained attachments to that same invocation. Screenshots still need visual
review; assigned UIFont observations do not identify per-glyph fallback fonts.
"""
from __future__ import annotations

import math
from pathlib import Path
import re
import uuid


TARGET = "PinkhaAnyNativeUITests"
SOURCE_COMMIT = "7380a797d13b279b6d19e43ade7af1929089b8ef"
SOURCE_AFTER = "8d58c41e8907019bf67088900bb5c35843562edd669422573c1280f800500e86"
SOURCE_PROOF = "docs/validation/20261127-wave2-native-styled-ui/source-proof.json"
SOURCE_PROOF_SHA = "63cadf150de799d104d8fb769b08578b3ddad3bb05f21fba232617ef2e550cf1"
PREFIX21_BYTES = 237631
PREFIX21_SHA = "5d3462b25dd64423cf33fc1243b2d734acea55011a9e5da4c66004022685958a"
PREFIX19_BYTES = 214858
PREFIX19_SHA = "31c64474cebf4890050f9077d3c44fac63264d878a77bd6f55811cc407e02422"
ADDITION_SHA = "b97c6ad4910088bae310914010a494981569becac0cffb0cf3ccd9018690828a"
OWNED_OUTCOMES_SHA = "73bb6a4f6dde58faa723c38fddd322b6a6ff356fbbee44ecdeb949a77d358e1a"
CHOICES = ("paragraph", "heading-1", "heading-2", "heading-3", "bulleted-list",
           "numbered-list", "checklist", "quote", "code")
CATALOG_PHASES = tuple(phase for choice in CHOICES for phase in (
    "choice-" + choice + "-empty-rtl", "choice-" + choice + "-saved")) + (
    "before-menu-empty-rtl", "before-menu-saved") + tuple("cold-" + choice for choice in CHOICES)
LIVE_PHASES = ("live-heading-1-empty-rtl", "live-code-empty-rtl", "live-paragraph-empty-rtl",
               "live-large-before", "live-accessibility", "live-large-restored")
PLANS = {
    "styled-blocks": {"method": "testTypedBlockMenusPersistAllNineKindsAndColdReopen",
                      "allowance": 1800, "phases": CATALOG_PHASES},
    "styled-live-type": {"method": "testNativeStyledTypographyRefreshesLiveAtAccessibilitySize",
                         "allowance": 900, "phases": LIVE_PHASES},
}
PREFIX = "PRIVATE-native-styled-"
FINAL_PREFIX = "PRIVATE-native-accessibility-final-"
INVOCATION_KEYS = {"schema", "runID", "appSourceCommit", "uiSourceCommit", "simulatorUDID",
                   "ownedScope", "method", "appLanguage", "osLanguage", "contentSize", "appearance",
                   "deviceFamily", "settingsReadbackSHA256"}
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
FRAME = re.compile(r"\{\{\s*(" + NUMBER + r"),\s*(" + NUMBER + r")\s*\},\s*\{\s*("
                   + NUMBER + r"),\s*(" + NUMBER + r")\s*\}\}\Z")


def qualify_source(c, current, proof_raw):
    """Return exact original19 bytes for the existing Library/RTL/title inverse."""
    c.require(c.sha(current) == SOURCE_AFTER and len(current) == 271344
              and c.sha(proof_raw) == SOURCE_PROOF_SHA,
              "Exact published Styled23 source and original insertion proof required")
    proof = c.decode(proof_raw)
    prefix21, suffix = current[:PREFIX21_BYTES], current[PREFIX21_BYTES:]
    prefix19 = prefix21[:PREFIX19_BYTES]
    methods = lambda data: [s.decode() for s in re.findall(rb"^    (?:@objc )?func (test\w+)\(", data, re.M)]
    original19, original21, current23 = methods(prefix19), methods(prefix21), methods(current)
    added = [PLANS[stage]["method"] for stage in ("styled-blocks", "styled-live-type")]
    c.require(proof["schema"] == "native-styled-ui-source-proof/v1"
              and proof["exactPrefixBytes"] == PREFIX21_BYTES
              and proof["exactPrefixSHA256"] == c.sha(prefix21) == PREFIX21_SHA
              and proof["original19Bytes"] == PREFIX19_BYTES
              and proof["original19SHA256"] == c.sha(prefix19) == PREFIX19_SHA
              and proof["suffixSHA256"] == c.sha(suffix) == ADDITION_SHA
              and proof["allOriginal21MethodsBytePreserved"] is True
              and proof["candidateMethods"] == len(current23) == 23
              and len(original19) == 19 and len(original21) == 21
              and proof["originalMethods"] == original21 and proof["addedMethods"] == added
              and current23 == original21 + added and original21[:19] == original19
              and current == prefix21 + suffix,
              "Styled23 must exactly preserve the published21 and original19 prefixes")
    return prefix19


def _uuid(value):
    try:
        return uuid.UUID(value) if isinstance(value, str) else None
    except (ValueError, AttributeError):
        return None


def _hex(value):
    return isinstance(value, str) and HEX64.fullmatch(value) is not None


def _positive(value):
    return type(value) is int and value > 0


def _bounded_string(value, limit):
    return isinstance(value, str) and 0 < len(value.encode("utf-8")) <= limit


def _read(c, path, maximum, *, allow_empty=False):
    c.require(path.is_absolute() and path.resolve() == path and not path.is_symlink() and path.is_file(),
              "Canonical regular original observation file required: " + str(path))
    raw = c.raw(path, maximum)
    c.require((0 if allow_empty else 1) <= len(raw) <= maximum, "Empty or oversized original observation")
    return raw, {"path": str(path), "bytes": len(raw), "sha256": c.sha(raw)}


def _context(c, out, udid, context, stage):
    c.require(stage in PLANS and isinstance(context, dict) and set(context) == INVOCATION_KEYS
              and all(isinstance(v, str) for v in context.values()),
              "Exactly the original13 string invocation fields required")
    raw, ref = _read(c, out / "styled-invocation.json", 16384)
    c.require(c.decode(raw) == context and context["schema"] == "native-accessibility-invocation/v1"
              and context["method"] == PLANS[stage]["method"]
              and _uuid(context["runID"]) is not None and _uuid(context["ownedScope"]) is not None
              and _uuid(udid) is not None and _uuid(context["simulatorUDID"]) == _uuid(udid)
              and re.fullmatch(r"[0-9a-f]{40}", context["appSourceCommit"]) is not None
              and context["appSourceCommit"] == context["uiSourceCommit"]
              and _hex(context["settingsReadbackSHA256"])
              and context["appLanguage"] in ("he", "en") and context["osLanguage"] in ("he", "en")
              and context["contentSize"] == "large" and context["appearance"] in ("light", "dark")
              and context["deviceFamily"] in ("iphone", "ipad"),
              "Retained original Styled invocation/source/device/settings binding differs")
    settings_raw, settings_ref = _read(c, out / "rtl-before-environment.json", 16384)
    settings = c.decode(settings_raw)
    c.require(c.sha(settings_raw) == context["settingsReadbackSHA256"] and isinstance(settings, dict)
              and settings.get("ownedUDID") == context["simulatorUDID"]
              and settings.get("language", {}).get("app_language") == context["appLanguage"]
              and settings.get("language", {}).get("device_language") == context["osLanguage"]
              and context["appLanguage"] != context["osLanguage"]
              and settings.get("presentation", {}).get("appearance") == context["appearance"]
              and settings.get("presentation", {}).get("content_size") == "large",
              "The original13-field context must bind the actual retained opposite-language/appearance/size readback")
    return ref, settings_ref


def _attachments(c, directory, udid, stage):
    phases, method = PLANS[stage]["phases"], PLANS[stage]["method"]
    labels = {}
    for phase in phases:
        for kind, ext in (("native", ".json"), ("context", ".json"), ("ax", ".txt"), ("screen", ".png")):
            labels[PREFIX + phase + "-" + kind] = (phase, kind, ext)
    for kind, ext in (("context", ".json"), ("ax", ".txt"), ("screen", ".png")):
        labels[FINAL_PREFIX + method + "-" + kind] = ("final", kind, ext)
    manifest_raw, manifest_ref = _read(c, directory / "manifest.json", 8 * 1024**2)
    manifest = c.decode(manifest_raw)
    c.require(isinstance(manifest, list), "Original xcresult attachment manifest required")
    found, values, paths = {}, {}, set()
    for row in manifest:
        c.require(isinstance(row, dict) and isinstance(row.get("attachments", []), list),
                  "Original typed xcresult attachment rows required")
        for item in row.get("attachments", []):
            c.require(isinstance(item, dict), "Original attachment item required")
            human = str(item.get("suggestedHumanReadableName", ""))
            if not human.startswith((PREFIX, FINAL_PREFIX)):
                continue
            matches = [value for label, value in labels.items()
                       if re.fullmatch(re.escape(label) + r"(?:_[A-Za-z0-9-]+)*" + re.escape(value[2]), human)]
            name = item.get("exportedFileName")
            test = str(row.get("testIdentifier", "")).removeprefix(TARGET + "/").removesuffix("()")
            c.require(len(matches) == 1 and isinstance(name, str) and Path(name).name == name
                      and name not in ("", ".", "..") and test == "NativeLaunchTests/" + method
                      and _uuid(item.get("deviceId")) == _uuid(udid)
                      and item.get("isAssociatedWithFailure") is False,
                      "Styled attachment belongs to another phase/method/device or failed observation")
            phase, kind, ext = matches[0]
            key = (phase, kind)
            c.require(Path(name).suffix == ext and Path(human).suffix == ext
                      and key not in found and name not in paths,
                      "Duplicate, aliased or wrongly typed Styled attachment")
            maximum = {"native": 24576, "context": 65536, "ax": 131080, "screen": 20 * 1024**2}[kind]
            raw, ref = _read(c, directory / name, maximum)
            if ext == ".json":
                value = c.decode(raw)
                c.require(isinstance(value, dict), "Original named JSON object required")
                values[key] = {"value": value, "raw": raw}
            elif ext == ".txt":
                raw.decode("utf-8")
            else:
                c.require(len(raw) >= 33 and raw[:8] == b"\x89PNG\r\n\x1a\n"
                          and raw[8:16] == b"\x00\x00\x00\rIHDR"
                          and 0 < int.from_bytes(raw[16:20], "big") <= 16384
                          and 0 < int.from_bytes(raw[20:24], "big") <= 16384,
                          "Actual bounded original PNG required")
                ref.update(width=int.from_bytes(raw[16:20], "big"), height=int.from_bytes(raw[20:24], "big"))
            found[key] = ref
            paths.add(name)
    expected = {(phase, kind) for phase in phases for kind in ("native", "context", "ax", "screen")}
    expected |= {("final", kind) for kind in ("context", "ax", "screen")}
    c.require(set(found) == expected, "Every finite Styled native/context/AX/PNG group and original final trio required")
    return manifest_ref, found, values


def _observation(c, native, meta, raw, phase, context):
    native_keys = {"schema", "mode", "pid", "state", "nativeReadOrigin", "engineCalls", "mutations",
                   "selectionChanges", "spaceSHA256", "objectSHA256", "nativeVersionSHA256", "generation",
                   "semanticSources", "sourceReadOrigin", "nativeMarkCount", "renderedMarkCount", "blocks"}
    c.require(set(native) == native_keys and native["schema"] == "any-semantic-anchor-native-rendered/v1"
              and native["mode"] == "read-only" and native["state"] == "MATCHED"
              and native["nativeReadOrigin"] == "AnyDocumentPresentation.read"
              and native["sourceReadOrigin"] == "TorahEditorSession.associationRecords"
              and _positive(native["pid"]) and _uuid(native["generation"]) is not None
              and all(_hex(native[key]) for key in ("spaceSHA256", "objectSHA256", "nativeVersionSHA256"))
              and all(type(native[key]) is int and native[key] == 0 for key in
                      ("engineCalls", "mutations", "selectionChanges", "nativeMarkCount", "renderedMarkCount"))
              and native["semanticSources"] == [] and isinstance(native["blocks"], list)
              and 1 <= len(native["blocks"]) <= 3,
              "Complete original plain-block native/rendered observation required")
    extra = set()
    if phase.startswith("cold-"):
        extra = {"hierarchyRowIdentifier", "objectIDFromOriginalHierarchy"}
    elif phase == "live-accessibility":
        extra = {"controllerReadback"}
    elif phase == "live-large-restored":
        extra = {"controllerReadback", "baselineObservationSHA256", "baselineAppPID", "restoredAppPID"}
    common = {"schema", "phase", "invocation", "nativeObservationSHA256", "appPIDFromOriginalObserver",
              "appLaunchArguments", "runnerProcessID", "visualReview", "fontClaim", "visibleBlocks"}
    language = context["appLanguage"]
    expected_args = ["--native-ui-tests", "--native-ui-test-scope", str(_uuid(context["ownedScope"])).upper(),
                     "-AppleLanguages", "(he,en)" if language == "he" else "(en,he)",
                     "-AppleLocale", "he_IL" if language == "he" else "en_US"]
    c.require(set(meta) == common | extra and meta["schema"] == "native-styled-ui-observation/v1"
              and meta["phase"] == phase and meta["invocation"] == context
              and meta["nativeObservationSHA256"] == c.sha(raw)
              and type(meta["appPIDFromOriginalObserver"]) is int and meta["appPIDFromOriginalObserver"] == native["pid"]
              and _positive(meta["runnerProcessID"]) and meta["appLaunchArguments"] == expected_args
              and meta["visualReview"] == "PENDING"
              and meta["fontClaim"] == "Assigned UIFont, not per-glyph fallback face"
              and isinstance(meta["visibleBlocks"], list) and len(meta["visibleBlocks"]) == len(native["blocks"]),
              "Original phase/invocation/native-byte/UI context differs")
    visible = {}
    for row in meta["visibleBlocks"]:
        c.require(isinstance(row, dict) and set(row) == {"identifier", "value", "frame"}
                  and _bounded_string(row["identifier"], 4096) and row["identifier"].startswith("any-native-block-")
                  and len(row["identifier"]) > len("any-native-block-")
                  and isinstance(row["value"], str) and len(row["value"].encode("utf-8")) <= 65536
                  and isinstance(row["frame"], str), "Actual bounded visible block identity/value/frame required")
        frame = FRAME.fullmatch(row["frame"])
        c.require(frame is not None, "Original NSStringFromCGRect observation required")
        rectangle = tuple(float(x) for x in frame.groups())
        c.require(all(math.isfinite(x) for x in rectangle) and rectangle[2] > 0 and rectangle[3] > 0,
                  "Actual finite mounted block frame required")
        key = c.sha(row["identifier"].removeprefix("any-native-block-").encode())
        c.require(key not in visible, "Distinct mounted block identities required")
        visible[key] = {**row, "rectangle": rectangle}
    block_keys = {"blockSHA256", "textSHA256", "sourceSHA256", "utf16Length", "nativeMarks", "renderedMarks",
                  "selectionLocation", "selectionLength", "isFirstResponder", "textPresentation"}
    identities = []
    for block in native["blocks"]:
        c.require(isinstance(block, dict) and set(block) == block_keys
                  and all(_hex(block[k]) for k in ("blockSHA256", "textSHA256", "sourceSHA256"))
                  and block["blockSHA256"] in visible and block["nativeMarks"] == [] and block["renderedMarks"] == []
                  and type(block["isFirstResponder"]) is bool
                  and all(type(block[k]) is int and block[k] >= 0 for k in ("utf16Length", "selectionLocation", "selectionLength"))
                  and isinstance(block["textPresentation"], dict), "Original complete typed block observation required")
        body = visible[block["blockSHA256"]]["value"]
        c.require(block["sourceSHA256"] == block["textSHA256"] == c.sha(body.encode())
                  and block["utf16Length"] == len(body.encode("utf-16-le")) // 2,
                  "Actual mounted text must match the same complete native block")
        identities.append(block["blockSHA256"])
    c.require(len(set(identities)) == len(identities) and set(identities) == set(visible),
              "All original native blocks must be present exactly once in the mounted observation")
    return {"native": native, "context": meta, "visible": visible, "raw": raw}


def _font_shape(c, font):
    c.require(isinstance(font, dict) and set(font) == {"name", "family", "pointSize", "bold", "italic"}
              and _bounded_string(font["name"], 1024) and _bounded_string(font["family"], 1024)
              and type(font["pointSize"]) in (int, float) and math.isfinite(font["pointSize"]) and font["pointSize"] > 0
              and type(font["bold"]) is bool and type(font["italic"]) is bool,
              "Actual assigned UIFont name/family/size/traits required")


def _paragraph_shape(c, paragraph):
    c.require(isinstance(paragraph, dict) and set(paragraph) == {"baseWritingDirection", "alignment"}
              and type(paragraph["baseWritingDirection"]) is int and type(paragraph["alignment"]) is int,
              "Actual mounted paragraph writing direction/alignment required")


def _presentation(c, block, choice, body, language, category, nominal, exact_style=None):
    report = block["textPresentation"]
    keys = {"schema", "nativeType", "nativeStylePresent", "nativeStyleJSON", "contentSizeCategory",
            "fontReadOrigin", "nativeReadOrigin", "assignedUIFontOnly", "fontRuns"}
    level = int(choice[-1]) if choice.startswith("heading-") else None
    native_type = "heading" if level else "list_item" if choice in ("bulleted-list", "numbered-list") else (
        "check_list_item" if choice == "checklist" else choice)
    c.require(keys <= set(report) <= keys | {"typingFont", "typingParagraph"}
              and report["schema"] == "native-mounted-text-presentation/v1"
              and report["nativeType"] == native_type and report["nativeStylePresent"] is True
              and _bounded_string(report["nativeStyleJSON"], 8192)
              and report["contentSizeCategory"] == category and _bounded_string(category, 1024)
              and report["fontReadOrigin"] == "mounted-UITextView-attributedText-and-typingAttributes"
              and report["nativeReadOrigin"] == "AnyDocumentPresentation.read.snapshot.blocks"
              and report["assignedUIFontOnly"] is True and isinstance(report["fontRuns"], list)
              and len(report["fontRuns"]) <= 128,
              "Original full native style and actual mounted text presentation required")
    style = c.decode(report["nativeStyleJSON"].encode())
    c.require(isinstance(style, dict) and style.get("pinkhaWritingDirection") == "rightToLeft"
              and style.get("pinkhaTextAlignment") == "natural" and style.get("lang") is None,
              "Original explicit RTL/natural native style required")
    expected = {"level": level, "ordered": False if choice == "bulleted-list" else True if choice == "numbered-list" else None,
                "number": 1 if choice == "numbered-list" else None, "checked": False if choice == "checklist" else None}
    for key, value in expected.items():
        actual = style.get(key)
        c.require(actual == value and (value is None or type(actual) is type(value)),
                  "Typed native block style differs for " + choice + ": " + key)
    if exact_style is not None:
        c.require(report["nativeStyleJSON"] == exact_style,
                  "Every original native style byte, including unknown fields, must be retained")
    nominal_size = {"heading-1": 28, "heading-2": 22, "code": 15}.get(choice, 17)
    font_name = "IBMPlexMono" if choice == "code" else "Inter_Bold" if level else "Inter"

    def assigned(font, paragraph):
        _font_shape(c, font)
        _paragraph_shape(c, paragraph)
        c.require(font["name"] == font_name and font["bold"] is (level is not None) and font["italic"] is False
                  and (abs(font["pointSize"] - nominal_size) < 0.01 if nominal else font["pointSize"] > nominal_size)
                  and paragraph["baseWritingDirection"] == 1 and paragraph["alignment"] == (2 if language == "he" else 0),
                  "Each actual font run/empty typing font must retain the original face/traits/RTL and qualified size")

    if "typingFont" in report:
        _font_shape(c, report["typingFont"])
    if "typingParagraph" in report:
        _paragraph_shape(c, report["typingParagraph"])
    if not body:
        c.require(report["fontRuns"] == [], "Empty native text must have no attributed font runs")
        assigned(report.get("typingFont"), report.get("typingParagraph"))
    else:
        offset = 0
        for run in report["fontRuns"]:
            c.require(isinstance(run, dict) and set(run) == {"location", "length", "font", "paragraph"}
                      and type(run["location"]) is int and run["location"] == offset and _positive(run["length"]),
                      "Complete contiguous actual attributed font runs required")
            assigned(run["font"], run["paragraph"])
            offset += run["length"]
        c.require(offset == len(body.encode("utf-16-le")) // 2,
                  "Every UTF-16 unit must be covered by qualified actual font runs")


def _expected(choice, body, block=None):
    return {"choice": choice, "body": body, "id": block["blockSHA256"] if block else None,
            "style": block["textPresentation"]["nativeStyleJSON"] if block else None}


def _match(c, observed, expected, context, category, nominal=True):
    blocks = observed["native"]["blocks"]
    c.require(len(blocks) == len(expected), "Exact complete native block count/order required")
    for block, item in zip(blocks, expected):
        c.require((item["id"] is None or block["blockSHA256"] == item["id"])
                  and observed["visible"][block["blockSHA256"]]["value"] == item["body"],
                  "Actual native block identity/body/order differs")
        _presentation(c, block, item["choice"], item["body"], context["appLanguage"], category, nominal, item["style"])


def _same_document(c, left, right):
    c.require(all(left["native"][key] == right["native"][key] for key in ("pid", "spaceSHA256", "objectSHA256")),
              "Original mounted App/Space/document changed within a live phase")


def _catalog(c, observations, context):
    first = observations[CATALOG_PHASES[0]]
    category = first["native"]["blocks"][0]["textPresentation"].get("contentSizeCategory")
    documents, object_hashes = {}, set()
    for choice in CHOICES:
        empty, saved = observations["choice-" + choice + "-empty-rtl"], observations["choice-" + choice + "-saved"]
        _match(c, empty, [_expected(choice, "")], context, category)
        wanted = _expected(choice, "אב7")
        wanted["id"] = empty["native"]["blocks"][0]["blockSHA256"]
        _match(c, saved, [wanted], context, category)
        _same_document(c, empty, saved)
        c.require(saved["native"]["objectSHA256"] not in object_hashes, "Nine distinct original native documents required")
        object_hashes.add(saved["native"]["objectSHA256"])
        documents[choice] = {"objectSHA256": saved["native"]["objectSHA256"],
                             "blocks": [_expected(choice, "אב7", saved["native"]["blocks"][0])]}
    original = documents["paragraph"]["blocks"][0]
    empty, saved = observations["before-menu-empty-rtl"], observations["before-menu-saved"]
    _match(c, empty, [_expected("heading-3", ""), original], context, category)
    inserted = _expected("heading-3", "ת8")
    inserted["id"] = empty["native"]["blocks"][0]["blockSHA256"]
    _match(c, saved, [inserted, original], context, category)
    _same_document(c, empty, saved)
    c.require(saved["native"]["objectSHA256"] == documents["paragraph"]["objectSHA256"]
              and saved["visible"][inserted["id"]]["rectangle"][1] < saved["visible"][original["id"]]["rectangle"][1],
              "The actual UIKit before-menu insertion must precede and preserve the original paragraph")
    documents["paragraph"]["blocks"].insert(0, _expected("heading-3", "ת8", saved["native"]["blocks"][0]))
    first_pid, space = first["native"]["pid"], first["native"]["spaceSHA256"]
    for phase in CATALOG_PHASES:
        observed = observations[phase]
        c.require(observed["native"]["spaceSHA256"] == space, "One original owned Space must serve the complete catalog")
        if not phase.startswith("cold-"):
            c.require(observed["native"]["pid"] == first_pid, "No extra App launch is permitted before the catalog cold phase")
    cold_pid, rows = None, set()
    for choice in CHOICES:
        observed, document = observations["cold-" + choice], documents[choice]
        _match(c, observed, document["blocks"], context, category)
        native, meta = observed["native"], observed["context"]
        if cold_pid is None:
            cold_pid = native["pid"]
        row, object_id = meta["hierarchyRowIdentifier"], meta["objectIDFromOriginalHierarchy"]
        c.require(native["pid"] == cold_pid and cold_pid != first_pid
                  and native["objectSHA256"] == document["objectSHA256"]
                  and _bounded_string(object_id, 4096) and row == "any-native-hierarchy-row-" + object_id
                  and c.sha(object_id.encode()) == document["objectSHA256"] and row not in rows,
                  "Same native document/style/body must survive the single actual distinct-PID cold reopen")
        rows.add(row)
        document.update(hierarchyRowIdentifier=row, objectIDFromOriginalHierarchy=object_id)
    return {"documentCount": 9, "typedChoices": list(CHOICES), "documents": documents,
            "appPIDBeforeCold": first_pid, "appPIDAfterCold": cold_pid, "spaceSHA256": space,
            "observedContentSizeCategory": category,
            "categoryAuthority": "Original source-qualified XCTest asserts UIContentSizeCategory.large.rawValue",
            "coldReopenPhases": 1, "beforeMenuNativeOrderAndMountedVerticalOrderObserved": True}


def _same_native_selection(c, left, right):
    a, b = left["native"], right["native"]
    c.require(all(a[key] == b[key] for key in ("pid", "spaceSHA256", "objectSHA256", "nativeVersionSHA256", "generation"))
              and len(a["blocks"]) == len(b["blocks"])
              and all(all(x[key] == y[key] for key in ("blockSHA256", "sourceSHA256", "textSHA256",
                          "selectionLocation", "selectionLength", "isFirstResponder"))
                      for x, y in zip(a["blocks"], b["blocks"])),
              "Live typography must retain the actual App PID/native read/blocks/selection/responder state")


def _primary_font(block):
    p = block["textPresentation"]
    return p["fontRuns"][0]["font"] if p["fontRuns"] else p["typingFont"]


def _rendezvous(c, out, context, observations):
    records = []
    for phase, before_phase, after_phase, size in (
        ("expanded", "live-large-before", "live-accessibility", "accessibility-extra-extra-extra-large"),
        ("restored", "live-accessibility", "live-large-restored", "large"),
    ):
        request_raw, request_ref = _read(c, out / "private-styled-rendezvous" / (phase + "-request.json"), 65536)
        response_raw, response_ref = _read(c, out / "private-styled-rendezvous" / (phase + "-response.json"), 16384)
        request, response = c.decode(request_raw), c.decode(response_raw)
        before, after = observations[before_phase], observations[after_phase]
        request_keys = {"schema", "phase", "requestNonce", "invocation", "requestedContentSize", "runnerProcessID",
                        "runnerBundleID", "appPIDFromOriginalObserver", "nativeObservationJSON", "nativeObservationSHA256"}
        c.require(isinstance(request, dict) and set(request) == request_keys
                  and request["schema"] == "native-typography-live-request/v1" and request["phase"] == phase
                  and _uuid(request["requestNonce"]) is not None and request["invocation"] == context
                  and request["requestedContentSize"] == size
                  and type(request["runnerProcessID"]) is int and request["runnerProcessID"] == before["context"]["runnerProcessID"]
                  and _bounded_string(request["runnerBundleID"], 1024)
                  and type(request["appPIDFromOriginalObserver"]) is int and request["appPIDFromOriginalObserver"] == before["native"]["pid"]
                  and isinstance(request["nativeObservationJSON"], str)
                  and request["nativeObservationJSON"].encode() == before["raw"]
                  and request["nativeObservationSHA256"] == c.sha(before["raw"]),
                  "Exact retained private request must bind the actual preceding mounted native observation")
        response_keys = {"schema", "phase", "requestNonce", "requestSHA256", "simulatorUDID", "contentSize",
                         "readback", "readbackSHA256", "status"}
        c.require(isinstance(response, dict) and set(response) == response_keys and all(isinstance(v, str) for v in response.values())
                  and response["schema"] == "native-typography-live-response/v1" and response["phase"] == phase
                  and response["requestNonce"] == request["requestNonce"] and response["requestSHA256"] == c.sha(request_raw)
                  and response["simulatorUDID"] == context["simulatorUDID"] and response["contentSize"] == size
                  and response["readback"].strip() == size and response["readbackSHA256"] == c.sha(response["readback"].encode())
                  and response["status"] == "APPLIED_AND_READ_BACK"
                  and after["context"]["controllerReadback"] == {
                      "requestSHA256": c.sha(request_raw), "responseSHA256": c.sha(response_raw), "response": response},
                  "Actual retained controller response bytes must equal the Swift coordination receipt")
        records.append({"phase": phase, "request": request_ref, "response": response_ref,
                        "requestValue": request, "responseValue": response})
    c.require(records[0]["requestValue"]["requestNonce"] != records[1]["requestValue"]["requestNonce"]
              and records[0]["requestValue"]["runnerBundleID"] == records[1]["requestValue"]["runnerBundleID"],
              "Two fresh ordered requests from the same actual test runner required")
    return records


def _pinned(c, value, expected_path, maximum, *, allow_empty=False):
    c.require(isinstance(value, dict) and set(value) == {"path", "sha256", "bytes"}
              and value["path"] == str(expected_path) and _hex(value["sha256"])
              and type(value["bytes"]) is int,
              "Exact original retained file pin required")
    raw, actual = _read(c, expected_path, maximum, allow_empty=allow_empty)
    c.require(value == actual, "Pinned original coordination bytes changed")
    return raw


def _number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _command(c, out, label, pins, argv=None, *, with_log=True):
    """Check the unchanged run() ledger, without executing or replacing it."""
    keys = {"command", "result", "processExit"} | ({"log"} if with_log else set())
    c.require(isinstance(pins, dict) and set(pins) == keys, "Complete original owned-command ledger pins required")
    values = {}
    for key, suffix in (("command", ".command.json"), ("result", ".result.json"), ("processExit", ".process-exit.json")):
        values[key] = c.decode(_pinned(c, pins[key], out / (label + suffix), 2 * 1024**2))
    command, result, process = (values[key] for key in ("command", "result", "processExit"))
    c.require(all(isinstance(value, dict) for value in values.values())
              and isinstance(command.get("argv"), list) and all(isinstance(x, str) for x in command["argv"])
              and (argv is None or command["argv"] == argv)
              and _positive(command.get("pid")) and command.get("pgid") == command["pid"]
              and type(command.get("pgid")) is int and _number(command.get("started"))
              and command["started"] > 0 and command.get("lifecycleSHA256") == OWNED_OUTCOMES_SHA
              and command.get("cleanupErrors") == [] and command.get("termination") == [],
              "Original command argv/owned process/initial lifecycle record differs")
    for value in (result, process):
        c.require(all(value.get(key) == command[key] for key in command)
                  and type(value.get("exitCode")) is int and value["exitCode"] == 0
                  and value.get("stopped") is None and value.get("cleanupErrors") == []
                  and _hex(value.get("logSHA256")) and _number(value.get("elapsedSeconds")),
                  "Original owned command result must retain its actual initial identity and successful process exit")
    c.require(result.get("status") == "PASS" and result.get("ownedProcessGroup") == "ABSENT_ESRCH"
              and process.get("status") == "EXIT_RECORDED_PENDING_GROUP_OBSERVATION"
              and result.get("processExitReceiptSHA256") == pins["processExit"]["sha256"]
              and result["logSHA256"] == process["logSHA256"]
              and result["elapsedSeconds"] >= process["elapsedSeconds"],
              "Actual successful original command/group observation and process-exit receipt required")
    log = None
    if with_log:
        log = _pinned(c, pins["log"], out / (label + ".log"), 4096, allow_empty=True)
        c.require(c.sha(log) == result["logSHA256"], "Actual original simctl output differs from its command ledger")
    return {"pins": pins, "log": log, "start": command["started"],
            "end": command["started"] + result["elapsedSeconds"], "argv": command["argv"]}


def _existing_command(c, out, label, argv):
    pins = {}
    for key, suffix in (("command", ".command.json"), ("result", ".result.json"),
                        ("processExit", ".process-exit.json"), ("log", ".log")):
        _, pins[key] = _read(c, out / (label + suffix), 4096 if key == "log" else 2 * 1024**2,
                            allow_empty=key == "log")
    return _command(c, out, label, pins, argv)


def _live_control(c, out, context, invocation_ref, records):
    """Bind actual controller I/O; this remains distinct from XCTest authority."""
    raw, ref = _read(c, out / "styled-live-control.json", 512 * 1024)
    value = c.decode(raw)
    keys = {"schema", "stage", "status", "invocationSHA256", "ownedUDID", "sourceCommit", "initialContentSize",
            "runner", "execute", "requests", "finalRestore", "errors", "actualXCTestAcceptance",
            "visualReview", "nativeCalls", "mutationScope"}
    c.require(isinstance(value, dict) and set(value) == keys
              and value["schema"] == "native-styled-live-control/v1" and value["stage"] == "styled-live-type"
              and value["status"] == "PASS_REQUESTS_AND_RESTORED_NOT_UI_ACCEPTANCE"
              and value["invocationSHA256"] == invocation_ref["sha256"]
              and value["ownedUDID"] == context["simulatorUDID"] and value["sourceCommit"] == context["appSourceCommit"]
              and value["initialContentSize"] == "large" and value["errors"] == []
              and value["actualXCTestAcceptance"] is False and value["visualReview"] == "PENDING"
              and type(value["nativeCalls"]) is int and value["nativeCalls"] == 0
              and value["mutationScope"] == "owned simulator content_size only",
              "Exact successful original live coordination/restoration receipt required")
    runner = value["runner"]
    runner_keys = {"bundleIdentifier", "builtApplication", "builtExecutable", "builtCodeCarriersSHA256", "installedApplication",
                   "installedCodeCarriersSHA256", "dataContainer", "installedLookupCommand", "processIDFromRequest"}
    c.require(isinstance(runner, dict) and set(runner) == runner_keys
              and isinstance(runner["bundleIdentifier"], str)
              and re.fullmatch(r"[A-Za-z0-9.-]+", runner["bundleIdentifier"]) is not None
              and _bounded_string(runner["builtExecutable"], 1024)
              and Path(runner["builtExecutable"]).name == runner["builtExecutable"]
              and runner["builtExecutable"] not in (".", "..")
              and _hex(runner["builtCodeCarriersSHA256"])
              and runner["builtCodeCarriersSHA256"] == runner["installedCodeCarriersSHA256"]
              and _positive(runner["processIDFromRequest"])
              and isinstance(runner["installedLookupCommand"], str)
              and re.fullmatch(r"styled-runner-app-[0-9]{2}", runner["installedLookupCommand"]) is not None
              and all(_bounded_string(runner[key], 4096) and Path(runner[key]).is_absolute()
                      and ".." not in Path(runner[key]).parts for key in ("builtApplication", "installedApplication", "dataContainer"))
              and Path(runner["builtApplication"]).suffix == Path(runner["installedApplication"]).suffix == ".app",
              "Original admitted/installed XCTest runner code and actual container identity required")
    owned_component = "/Library/Developer/CoreSimulator/Devices/" + context["simulatorUDID"] + "/"
    c.require(owned_component in runner["installedApplication"] and owned_component in runner["dataContainer"]
              and runner["installedApplication"].split(owned_component)[0] == runner["dataContainer"].split(owned_component)[0],
              "Actual runner application/data paths must belong to the same owned simulator")
    app_lookup = _existing_command(c, out, runner["installedLookupCommand"],
                                  ["xcrun", "simctl", "get_app_container", context["simulatorUDID"], runner["bundleIdentifier"], "app"])
    data_lookup = _existing_command(c, out, "styled-runner-data",
                                   ["xcrun", "simctl", "get_app_container", context["simulatorUDID"], runner["bundleIdentifier"], "data"])
    c.require(app_lookup["log"].decode().strip() == runner["installedApplication"]
              and data_lookup["log"].decode().strip() == runner["dataContainer"],
              "Retained actual simctl runner-container output must match the coordination identity")
    execute = _command(c, out, "execute", value["execute"], with_log=False)
    requests = value["requests"]
    c.require(isinstance(requests, list) and len(requests) == 2, "Exactly two ordered original live requests required")
    previous_end = execute["start"]
    for row, observed in zip(requests, records):
        expected_keys = {"phase", "contentSize", "request", "requestNonce", "runnerProcessID", "appPIDFromOriginalObserver",
                         "nativeObservationSHA256", "set", "read", "readback", "readbackSHA256", "response", "responsePublished"}
        request, response, phase = observed["requestValue"], observed["responseValue"], observed["phase"]
        c.require(isinstance(row, dict) and set(row) == expected_keys and row["phase"] == phase
                  and row["contentSize"] == request["requestedContentSize"]
                  and row["request"] == observed["request"] and row["response"] == observed["response"]
                  and row["requestNonce"] == request["requestNonce"]
                  and type(row["runnerProcessID"]) is int and row["runnerProcessID"] == request["runnerProcessID"] == runner["processIDFromRequest"]
                  and request["runnerBundleID"] == runner["bundleIdentifier"]
                  and type(row["appPIDFromOriginalObserver"]) is int and row["appPIDFromOriginalObserver"] == request["appPIDFromOriginalObserver"]
                  and row["nativeObservationSHA256"] == request["nativeObservationSHA256"]
                  and row["readback"] == response["readback"] and row["readbackSHA256"] == response["readbackSHA256"]
                  and row["responsePublished"] is True,
                  "Original live-control row must bind the retained request/response and actual runner/native identities")
        setter = _command(c, out, "styled-" + phase + "-set", row["set"],
                          ["xcrun", "simctl", "ui", context["simulatorUDID"], "content_size", row["contentSize"]])
        reader = _command(c, out, "styled-" + phase + "-read", row["read"],
                          ["xcrun", "simctl", "ui", context["simulatorUDID"], "content_size"])
        c.require(reader["log"].decode() == row["readback"] and c.sha(reader["log"]) == row["readbackSHA256"]
                  and previous_end <= setter["start"] and setter["end"] <= reader["start"]
                  and reader["end"] <= execute["end"],
                  "Actual owned size setter/readback must occur in the original ordered live XCTest interval")
        previous_end = reader["end"]
    final = value["finalRestore"]
    c.require(isinstance(final, dict) and set(final) == {"attempted", "target", "set", "read", "actual", "readback", "readbackSHA256"}
              and final["attempted"] is True and final["target"] == final["actual"] == "large"
              and isinstance(final["readback"], str) and final["readback"].strip() == "large"
              and final["readbackSHA256"] == c.sha(final["readback"].encode()),
              "Actual final restoration/readback of the original large category required")
    setter = _command(c, out, "styled-final-restore-set", final["set"],
                      ["xcrun", "simctl", "ui", context["simulatorUDID"], "content_size", "large"])
    reader = _command(c, out, "styled-final-restore-read", final["read"],
                      ["xcrun", "simctl", "ui", context["simulatorUDID"], "content_size"])
    c.require(execute["end"] <= setter["start"] and setter["end"] <= reader["start"]
              and reader["log"].decode() == final["readback"] and c.sha(reader["log"]) == final["readbackSHA256"],
              "Original finally path must retain actual successful restoration after the XCTest process completed")
    return {"receipt": ref, "runner": runner, "execute": value["execute"],
            "runnerLookup": {"app": app_lookup["pins"], "data": data_lookup["pins"]},
            "finalRestore": final, "coordinationIsNotXCTestAcceptance": True}


def _live(c, out, observations, context, invocation_ref):
    baseline, expanded, restored = (observations[p] for p in ("live-large-before", "live-accessibility", "live-large-restored"))
    category = baseline["native"]["blocks"][0]["textPresentation"].get("contentSizeCategory")
    expanded_category = expanded["native"]["blocks"][0]["textPresentation"].get("contentSizeCategory")
    expected = [_expected("heading-1", "אב"), _expected("code", "A7"), _expected("paragraph", "")]
    _match(c, baseline, expected, context, category)
    expected = [_expected(x["choice"], x["body"], b) for x, b in zip(expected, baseline["native"]["blocks"])]
    c.require(all(b["isFirstResponder"] is False for b in baseline["native"]["blocks"])
              and _bounded_string(expanded_category, 1024) and expanded_category != category,
              "Actual unfocused baseline and changed mounted UIKit category required")
    for index, phase in enumerate(LIVE_PHASES[:3]):
        wanted = [dict(item) for item in expected[:index + 1]]
        wanted[-1].update(body="", style=None)
        _match(c, observations[phase], wanted, context, category)
        _same_document(c, observations[phase], baseline)
    _match(c, expanded, expected, context, expanded_category, nominal=False)
    _match(c, restored, expected, context, category)
    _same_native_selection(c, expanded, baseline)
    _same_native_selection(c, restored, baseline)
    for b, e, r in zip(baseline["native"]["blocks"], expanded["native"]["blocks"], restored["native"]["blocks"]):
        before, after, reset = _primary_font(b), _primary_font(e), _primary_font(r)
        c.require(after["name"] == before["name"] and after["pointSize"] > before["pointSize"] and reset == before,
                  "Actual primary assigned fonts must grow and return exactly to their original baseline")
    final = restored["context"]
    c.require(final["baselineObservationSHA256"] == c.sha(baseline["raw"])
              and type(final["baselineAppPID"]) is int and type(final["restoredAppPID"]) is int
              and final["baselineAppPID"] == final["restoredAppPID"] == baseline["native"]["pid"],
              "Restored phase must bind the same original baseline bytes and App PID")
    requests = _rendezvous(c, out, context, observations)
    controller = _live_control(c, out, context, invocation_ref, requests)
    return {"blocks": expected, "appPID": baseline["native"]["pid"],
            "spaceSHA256": baseline["native"]["spaceSHA256"], "objectSHA256": baseline["native"]["objectSHA256"],
            "observedBaselineCategory": category, "observedExpandedCategory": expanded_category,
            "observedRestoredCategory": category,
            "categoryAuthority": "Original source-qualified XCTest asserts both actual UIContentSizeCategory enum raw values",
            "allFontRunsAndEmptyTypingFontQualified": True, "nativeReadAndSelectionUnchanged": True,
            "controller": controller,
            "rendezvous": [{k: record[k] for k in ("phase", "request", "response")} for record in requests]}


def attachments(c, directory: Path, udid: str, context: dict, stage: str):
    """Observe one already-successful original result; never replace its authority."""
    c.require(directory.is_absolute() and directory.resolve() == directory and not directory.is_symlink() and directory.is_dir(),
              "Canonical original private exported attachment directory required")
    invocation_ref, settings_ref = _context(c, directory.parent, udid, context, stage)
    manifest_ref, found, values = _attachments(c, directory, udid, stage)
    observations = {}
    for phase in PLANS[stage]["phases"]:
        native, meta = values[(phase, "native")], values[(phase, "context")]
        observations[phase] = _observation(c, native["value"], meta["value"], native["raw"], phase, context)
    c.require(len({row["context"]["runnerProcessID"] for row in observations.values()}) == 1,
              "All actual phase captures must belong to the same original XCTest runner process")
    final = values[("final", "context")]["value"]
    c.require(set(final) == {"schema", "invocation", "caseReachedEnd", "appStateBeforeTermination", "runnerSimulatorUDID",
                             "captureRequiresCompletedOnboarding", "contentsPrivate", "captureBeforeTermination"}
              and final["schema"] == "native-accessibility-private-final/v1" and final["invocation"] == context
              and final["caseReachedEnd"] is True and _bounded_string(final["appStateBeforeTermination"], 1024)
              and _uuid(final["runnerSimulatorUDID"]) == _uuid(udid)
              and final["captureRequiresCompletedOnboarding"] is False and final["contentsPrivate"] is True
              and final["captureBeforeTermination"] is True,
              "Original successful end-of-method private context/AX/PNG capture required")
    metadata = _catalog(c, observations, context) if stage == "styled-blocks" else _live(
        c, directory.parent, observations, context, invocation_ref)
    return {"schema": "native-styled-observation-collection/v1", "status": "OBSERVATIONS_MATCH_SOURCE_VISUAL_REVIEW_PENDING",
            "stage": stage, "selector": TARGET + "/NativeLaunchTests/" + PLANS[stage]["method"],
            "executionTimeAllowanceSeconds": PLANS[stage]["allowance"], "invocation": invocation_ref,
            "beforeEnvironment": settings_ref,
            "manifest": manifest_ref, "phaseOrderFromOriginalSource": list(PLANS[stage]["phases"]),
            "metadata": metadata,
            "phases": {phase: {kind: found[(phase, kind)] for kind in ("native", "context", "ax", "screen")}
                       for phase in PLANS[stage]["phases"]},
            "final": {kind: found[("final", kind)] for kind in ("context", "ax", "screen")},
            "originalResultAuthority": "Unchanged sole NativeUI runner: exact one-case XCTest, descriptor, process exit and device",
            "standaloneProductOrXCTestAcceptance": False, "visualReview": "PENDING", "physicalDevice": "NOT_RUN",
            "fontClaim": "Assigned UIFont, not per-glyph fallback face", "extraObserverNativeCalls": 0}
