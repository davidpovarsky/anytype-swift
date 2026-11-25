"""Closed UI-only Bin confirmation preparation on the original App13 products."""
import hashlib
import json
from pathlib import Path

MAIN = "e540cd7e01b497f1b3173ae2e68b43ade0b00b6f"
SOURCE = "aa26166f27773b9122c00c9716c0b57a5fe3408c"
REVIEW_PATH = "docs/validation/20261125-native-bin-confirmation-preparation/source-review.json"
EXPECTED = {
    "protocol": "native-bin-confirmation-ax-preparation-v1",
    "mainSourceCommit": MAIN, "sourceCommit": SOURCE,
    "originalSHA256": "6fbcd0173351597af99dd6d79e7869ac72077c0b9ad2ff464d9c02e60d096d02",
    "compiledSHA256": "62691fb184de1d8b572bd0c9561f4668a5f296e42e276e4fce68648cb41fe7b3",
    "helperSHA256": "d017e9fd5d1988af07b7274203e516fb085aa4e06e1f44e1bee18bad914e3543",
    "reviewSHA256": "1a07cbefddb9075219a6194cc31b1c6cc0de2bd8d8e2ba9a468d5314ae998b43",
    "inverseDeltaRestoresCompleteOriginalFile": True,
    "allOriginalIdentityBodyBinRestoreColdAssertionsUnchanged": True,
    "timeoutSeconds": 30, "productChanges": 0, "nativeCallsAdded": 0,
    "storageOverridesAdded": 0,
}
PINS = {
    "nativeSHA256": "48905b7312d7228fe88a60517ec90c1c23d73f2ada762877c05ace9752103342",
    "sdkReceiptSHA256": "bad0afa285da6bd023235b15f82329f9d7b32ec50bf9194d63b9ee96730324a5",
    "lockSHA256": "e22368e522ac795253935b0a31e39d1b36bd9043ef2ed1014845927914527ccd",
}

def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def qualify_source(original, candidate, review):
    require(sha(original) == EXPECTED["originalSHA256"] and
            sha(candidate) == EXPECTED["compiledSHA256"] and
            sha(review) == EXPECTED["reviewSHA256"], "exact_Bin_confirmation_source_bytes_required")
    begin = b"    // BEGIN_NATIVE_BIN_CONFIRMATION_AX_PREPARATION_V1\n"
    end = b"    // END_NATIVE_BIN_CONFIRMATION_AX_PREPARATION_V1\n\n"
    require(candidate.count(begin) == candidate.count(end) == 1,
            "one_closed_Bin_confirmation_helper_required")
    a = candidate.index(begin); z = candidate.index(end, a) + len(end)
    require(sha(candidate[a:z]) == EXPECTED["helperSHA256"], "Bin_confirmation_helper_changed")
    before = b'        tapWhenEnabled(app.buttons["any-native-bin-confirm-remove"])\n'
    after = b'        confirmNativeBinRemoval(app)\n'
    stripped = candidate[:a] + candidate[z:]
    require(original.count(before) == stripped.count(after) == 1 and
            stripped.replace(after, before) == original,
            "Bin_confirmation_inverse_must_restore_every_original_UI_byte")
    reviewed = json.loads(review)
    require(reviewed["inverseDeltaRestoresCompleteOriginalFile"] is True and
            reviewed["originalIdentityBodyBinRestoreColdAssertionsUnchanged"] is True and
            reviewed["originalTimeoutSeconds"] == reviewed["timeoutSeconds"] == 30 and
            reviewed["productChanges"] == reviewed["nativeCallsAdded"] == reviewed["storageOverridesAdded"] == 0,
            "Bin_confirmation_must_not_change_product_authority_or_outcomes")
    return dict(EXPECTED)

def admit(source, main_record, ui_build, ui_record):
    require(main_record["sourceCommit"] == MAIN and
            main_record["inputs"]["nativeSourceManifestSHA256"] == "410b441e5726b4a2ff7b259e296ad2ba819a5751cd46732945f62259ace42cc9" and
            main_record["assemblyReceiptSHA256"] == "8556b47a6a7e523bd5ad4c58ae292501acda1038b0d1f827e268cef15a542797" and
            ui_record["runnerSourceCommit"] == SOURCE,
            "exact_App13_and_Bin_UI_source_required")
    for key, value in PINS.items():
        require(main_record["inputs"].get(key) == value and
                ui_record.get("reviewedInputProfile", {}).get(key) == value,
                "exact_Bin_App13_dependency_required:" + key)
    projection = json.loads((ui_build / "projection.json").read_bytes())
    require(ui_record.get("current410bBinConfirmationFixture") ==
            projection.get("current410bBinConfirmationFixture") == EXPECTED and
            ui_record.get("current410bFixture") is None and projection.get("current410bFixture") is None and
            projection["mainSourceCommit"] == MAIN and projection["runnerSourceCommit"] == SOURCE and
            projection["changedOriginalMethodAssertions"] == 0 and
            projection["applicationBuildTargets"] == projection["nativeLibraryBuilds"] == 0,
            "exact_UI_derivative_must_not_claim_same_source_App_build")
    for name, row in projection["sourceFiles"].items():
        path = ui_build / name
        require(path.is_file() and not path.is_symlink() and ui_build in path.resolve().parents and
                path.stat().st_size == row["bytes"] and sha(path.read_bytes()) == row["sha256"],
                "compiled_Bin_confirmation_UI_source_changed:" + name)
    return qualify_source((source / "NativeApp/UITests/NativeLaunchTests.swift").read_bytes(),
                          (ui_build / "source/UITests/NativeLaunchTests.swift").read_bytes(),
                          (ui_build / "bin-confirmation-source-review.json").read_bytes())
