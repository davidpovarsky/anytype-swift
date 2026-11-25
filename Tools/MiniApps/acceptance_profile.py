"""Explicit source profile for the owned external MiniApps selection feature.

The workflow keeps its existing Hanlin selection entry point. Only the exact
owned branch resolves this tracked profile; other branches retain their original
selection suite. No workflow permissions or test success criteria are changed.
"""
from pathlib import Path
import hashlib
import json

BRANCH = "codex/anytype-miniapps-bridge-20261123"
PREPARE = "PinkhaMiniAppsNativePreparationTests/prepareMiniAppsDocument"
VERIFY = "PinkhaMiniAppsNativePreparationTests/verifyReturnedNativeDocument"
ADAPTER = "PinkhaMiniAppsNativePreparationTests/applySelectedTextAndPreserveNewerNativeContent"
UI_RETURN = "MiniAppsNativeAcceptanceUITests/testNativeEditorPickerTextStudioReturnAndColdReopen"
UI_REPLAY = "MiniAppsNativeAcceptanceUITests/testDuplicateCallbackDoesNotInsertAgain"
METHODS = [PREPARE, UI_RETURN, UI_REPLAY, VERIFY, ADAPTER]

def resolve_profile(app, requested_lane, branch):
    if branch != BRANCH or requested_lane not in {"hanlin-selection", "miniapps-native"}:
        return None
    relative = "Tools/MiniApps/native-profile.json"
    raw = (Path(app) / relative).read_bytes()
    profile = json.loads(raw)
    expected = dict(schema_version=1, profile="external-miniapps-native-v1",
                    consumer_branch=BRANCH, requested_lane="hanlin-selection",
                    effective_lane="miniapps-native", selected_methods=METHODS,
                    expected_method_count=5, original_hanlin_selection_executed=False)
    if profile != expected:
        raise ValueError("Tracked MiniApps selection profile differs from the reviewed five methods")
    return dict(requested_lane=requested_lane, effective_lane=profile["effective_lane"],
                source_profile=relative, source_profile_sha256=hashlib.sha256(raw).hexdigest(),
                selected_methods=METHODS.copy(), original_hanlin_selection_executed=False)
