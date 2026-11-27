"""Narrow, invertible localization of the original T5 startup warning shape.

Source preparation only. No test, simulator, or native operation is performed.
"""
from pathlib import Path
import hashlib
import json
import difflib


ROOT = Path(__file__).resolve().parent
READBACK = ROOT.parent / "t5-page154-readiness-refresh"
NAME = "PinkhaT5NativeAcceptanceUITests.swift"
ORIGINAL_SHA = "698f4ed7f1f81fe567b94b531f43e14259d08e6acbf79d72e132a5b9b6b941a7"
AUTH_SHA = "8ee4b81dfe98236853f6ba3949148ca2c2c8ca78aefdaf676c40aa128aa33161"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    original = (READBACK / "source" / NAME).read_bytes()
    auth = (READBACK / "source" / "Auth.xcstrings").read_bytes()
    assert digest(original) == ORIGINAL_SHA and digest(auth) == AUTH_SHA
    values = json.loads(auth)["strings"]

    def literal(key, language):
        return json.dumps(values["Initial.UnstableMiddle." + key]["localizations"][language]["stringUnit"]["value"], ensure_ascii=False)

    old = original.decode("utf8")
    changes = [
        ("        let warningPredicate = NSPredicate(format: \"elementType == %d AND label == %@\",\n",
         "        let warningTitle = appLanguage == \"he\" ? " + literal("Title", "he") + " : " + literal("Title", "en") + "\n"
         "        let warningPredicate = NSPredicate(format: \"elementType == %d AND label == %@\",\n"),
        ("XCUIElement.ElementType.alert.rawValue, \"Warning\")", "XCUIElement.ElementType.alert.rawValue, warningTitle)"),
        ("let warnings = app.alerts.matching(NSPredicate(format: \"label == %@\", \"Warning\"))",
         "let warnings = app.alerts.matching(NSPredicate(format: \"label == %@\", warningTitle))"),
        ("try require(!warnings.firstMatch.exists, \"Native startup warning remained or returned\")",
         "try require(!warnings.firstMatch.exists && app.alerts.count == 0, \"Native startup warning remained or returned\")"),
        ("        let text = " + literal("Message", "en") + "\n",
         "        let text = appLanguage == \"he\"\n"
         "            ? " + literal("Message", "he") + "\n"
         "            : " + literal("Message", "en") + "\n"
         "        let continueTitle = appLanguage == \"he\" ? " + literal("Continue", "he") + " : " + literal("Continue", "en") + "\n"
         "        let logoutTitle = appLanguage == \"he\" ? " + literal("Logout", "he") + " : " + literal("Logout", "en") + "\n"),
        ("let proceed = warning.buttons.matching(NSPredicate(format: \"label == %@\", " + literal("Continue", "en") + "))",
         "let proceed = warning.buttons.matching(NSPredicate(format: \"label == %@\", continueTitle))"),
        ("let logout = warning.buttons.matching(NSPredicate(format: \"label == %@\", " + literal("Logout", "en") + "))",
         "let logout = warning.buttons.matching(NSPredicate(format: \"label == %@\", logoutTitle))"),
    ]
    candidate = old
    for before, after in changes:
        assert candidate.count(before) == 1
        candidate = candidate.replace(before, after, 1)
    inverse = candidate
    for before, after in reversed(changes):
        assert inverse.count(after) == 1
        inverse = inverse.replace(after, before, 1)
    assert inverse.encode("utf8") == original
    launch = "    private func launch() throws {"
    tail = "    private func enterObject(_ id: String) throws {"
    assert candidate.split(launch)[0] == old.split(launch)[0]
    assert candidate.split(tail)[1] == old.split(tail)[1]
    assert candidate.count("systemUptime + 120") == old.count("systemUptime + 120") == 1
    assert candidate.count("        button.tap()") == old.count("        button.tap()")
    for key in ("PINKHA_NATIVE_UI_DISPOSABLE", "PINKHA_T5_UI_TOKEN", "PINKHA_T5_UI_APP_SHA", "PINKHA_T5_UI_RUN_ID"):
        assert candidate.count(key) == old.count(key)
    proof = {
        "status": "PASS_EXACT_SOURCE_INVERSE_NOT_SWIFT_OR_UI_EXECUTION",
        "baseCommit": "cee06ac951f735514059e616fbea48f07d4e7c09",
        "path": "PinkhaStage1Acceptance/Tests/" + NAME,
        "originalSHA256": ORIGINAL_SHA, "originalBytes": len(original),
        "candidateSHA256": digest(candidate.encode("utf8")), "candidateBytes": len(candidate.encode("utf8")),
        "productionAuthSHA256": AUTH_SHA,
        "changes": [{"old": a, "new": b, "count": 1} for a, b in changes],
        "fullInverseRestoresEveryOriginalByte": True,
        "unchangedPrefixBeforeLaunch": True, "unchangedSuffixAfterWarningHelper": True,
        "originalTestMethodsUnchanged": [
            "testCurrentSpaceRowsAndExactBlockNavigation",
            "testAddNoteEditOpenUnlinkAndRetainAfterRelaunch",
            "testHebrewRelatedRowsLongTitlesAndReadOnlyNavigation"],
        "preparationFixtureAndEnvironmentContractChanged": False,
        "startupSeconds": 120, "onlyContinueCanBeTapped": True,
        "unknownDialogs": "Untouched; explicit final zero-alert requirement",
        "sourceReviewRequired": True, "swiftCompilation": "NOT_RUN", "XCTest": "NOT_RUN",
        "nativeCalls": 0, "productAdmission": False,
    }
    (ROOT / "source" / NAME).write_bytes(original)
    (ROOT / "candidate" / NAME).write_bytes(candidate.encode("utf8"))
    (ROOT / "source-inverse.json").write_text(json.dumps(proof, ensure_ascii=False, indent=2) + "\n")
    (ROOT / "changes.diff").write_text("".join(difflib.unified_diff(old.splitlines(True), candidate.splitlines(True), fromfile="original/" + NAME, tofile="candidate/" + NAME)))
    print(json.dumps({k: proof[k] for k in ["status", "originalSHA256", "candidateSHA256", "candidateBytes"]}))


if __name__ == "__main__":
    main()
