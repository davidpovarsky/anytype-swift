"""Restore only reviewed startup replacements, then compare exact donor bytes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("Expected exactly one reviewed startup replacement")
    return text.replace(old, new)


def restored(name, text):
    if name == "AnytypeComprehensiveAcceptanceUITests.swift":
        text = replace_once(text,
            "        if expectedPID == nil || Self.readyPID != expectedPID || app.alerts.count > 0 {",
            "        if expectedPID == nil || Self.readyPID != expectedPID {")
        text = replace_once(text, '''            // Preserve the runner's exact process; only continue the original
            // warning for its controller-bound, freshly prepared native fixture.
            try PinkhaDisposableStartupWarning.waitForNavigation(
                app, testCase: self, spaceID: fixture.spaceId,
                allowedLanes: ["inspector", "inspector-search"]
            )''', '''            if !more.exists {
                guard home.waitForExistence(timeout: 120) else {
                    // Throw so Swift unwinds both timing and final-evidence defers.
                    // XCTest still records the missing readiness as a failed test.
                    throw NSError(domain: "UI27Readiness", code: 1, userInfo: [
                        NSLocalizedDescriptionKey: "Restored home did not become ready before the deep link"
                    ])
                }
            }''')
    elif name == "PinkhaTorahQuoteAcceptanceUITests.swift":
        text = replace_once(text, '''        try PinkhaDisposableStartupWarning.waitForNavigation(
            app, testCase: self, spaceID: fixture.spaceId, allowedLanes: ["quote-drop"]
        )''', '''        let ready = app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier == %@ OR label == %@ OR identifier == %@ OR label == %@ OR (elementType == %d AND (label == %@ OR label == %@))",
            "SpaceHub", "SpaceHub", "NewSpaceButton", "NewSpaceButton",
            XCUIElement.ElementType.button.rawValue, "More", "x24/More"
        )).firstMatch
        try require(ready.waitForExistence(timeout: 120), "Native Home did not become ready before document routing")''')
    elif name == "PinkhaStage1AcceptanceUITests.swift":
        text = replace_once(text, "import CryptoKit\nimport XCTest\n", "import XCTest\n")
        for space, lanes in [("fixture.spaceId", '["properties", "properties-set"]'),
                             ("spaceID", '["canonical-properties"]')]:
            text = replace_once(text,
                "        try PinkhaDisposableStartupWarning.waitForNavigation(\n"
                + "            app, testCase: self, spaceID: " + space + ", allowedLanes: " + lanes + "\n        )",
                "        guard waitForPinkhaNativeNavigation(app) else { return }")
        marker = "\n\n/// Test-only continuation of the exact original middleware warning."
        if text.count(marker) != 1:
            raise ValueError("Exactly one embedded helper required")
        text = text.split(marker, 1)[0] + "\n"
    else:
        raise ValueError("Unreviewed source")
    return text.encode("utf-8")


def verify(root, originals):
    rows = []
    for name in ["AnytypeComprehensiveAcceptanceUITests.swift", "PinkhaTorahQuoteAcceptanceUITests.swift",
                 "PinkhaStage1AcceptanceUITests.swift"]:
        relative = "PinkhaStage1Acceptance/Tests/" + name
        actual = (root / relative).read_bytes()
        original = originals(relative)
        if restored(name, actual.decode("utf-8")) != original:
            raise ValueError("Inverse does not restore exact donor bytes: " + relative)
        rows.append(dict(path=relative, sourceSHA256=hashlib.sha256(actual).hexdigest(),
                         originalSHA256=hashlib.sha256(original).hexdigest(), exactInverse=True))
    return dict(status="PASS_EXACT_ORIGINAL_UI_SOURCE_INVERSE_NOT_EXECUTION", donor="2a95ad12d6e58c4895583a871f9a07f8902ce34e",
                files=rows, originalUIAssertionsRewritten=False, T5FilesEdited=False, testsExecuted=0)


if __name__ == "__main__":
    root = Path(sys.argv[1]).resolve()
    if len(sys.argv) == 3:
        original_root = Path(sys.argv[2]).resolve()
        original = lambda relative: (original_root / relative).read_bytes()
    else:
        original = lambda relative: subprocess.check_output(["git", "-C", str(root), "show",
                    "2a95ad12d6e58c4895583a871f9a07f8902ce34e:" + relative])
    print(json.dumps(verify(root, original), indent=2, sort_keys=True))
