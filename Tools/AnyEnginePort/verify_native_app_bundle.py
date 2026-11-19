#!/usr/bin/env python3
"""Verify the built app's declared single-scene ownership boundary."""
from pathlib import Path
import argparse, hashlib, json, plistlib

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    plist = args.bundle / "Info.plist"
    raw = plist.read_bytes()
    values = plistlib.loads(raw)
    manifest = values.get("UIApplicationSceneManifest", {})
    if manifest.get("UIApplicationSupportsMultipleScenes") is not False:
        raise SystemExit("The built native app must explicitly disable simultaneous scenes")
    if values.get("CFBundleIdentifier") != "io.pinkha.anynative.dev":
        raise SystemExit("Unexpected native app bundle")
    executable = values.get("CFBundleExecutable")
    if not isinstance(executable, str) or Path(executable).name != executable:
        raise SystemExit("Invalid executable entry")
    if not (args.bundle / executable).is_file():
        raise SystemExit("Built native executable is absent")
    minimum = tuple(int(part) for part in values.get("MinimumOSVersion", "0").split("."))
    if minimum < (27, 0):
        raise SystemExit("Unexpected deployment target")
    families = values.get("UIDeviceFamily", [])
    if 1 not in families or 2 not in families:
        raise SystemExit("The native app must declare iPhone and iPad support")
    receipt = {
        "status": "PASS_BUILT_SINGLE_SCENE_CONTRACT",
        "scope": "Actual built Info.plist and executable presence; not a second-window UI test",
        "bundleIdentifier": values["CFBundleIdentifier"],
        "infoPlistSHA256": hashlib.sha256(raw).hexdigest(),
        "multipleScenes": False,
        "minimumOSVersion": values["MinimumOSVersion"],
        "deviceFamilies": families,
        "executable": executable,
        "reference": "https://developer.apple.com/documentation/bundleresources/information-property-list/uiapplicationscenemanifest/uiapplicationsupportsmultiplescenes",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))

if __name__ == "__main__":
    main()
