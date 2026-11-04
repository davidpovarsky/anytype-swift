"""Build ONLY the real native Pinkha iPad app with its verified custom Heart.

No XCTest, no UI tests, no simulator. This produces an UNSIGNED IPA for later
signing/sideloading, not a TestFlight or physical-device validation pass.
"""
import argparse
import json
import platform
import plistlib
import shutil
import zipfile
from pathlib import Path

from build_custom_heart import command, contains, digest, git


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--app-source", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    if platform.system() != "Darwin":
        raise RuntimeError("macOS/Xcode is required to build an iOS IPA")

    app = args.app_source.resolve()
    evidence = args.evidence.resolve()
    if git(app, "branch", "--show-current") != "codex/torah-native-derived-properties-20261103":
        raise RuntimeError("Not on the authorized isolated Pinkha branch")

    receipt_path = app / "Dependencies/Middleware/PinkhaNativeHeartBuild.json"
    if not receipt_path.is_file():
        raise RuntimeError("Verified custom Heart receipt is missing; NEVER use stock middleware")
    heart = json.loads(receipt_path.read_text(encoding="utf-8"))
    if heart.get("status") != "PASS" or heart.get("target") != "ios":
        raise RuntimeError("Custom Heart iOS build has not succeeded")
    if not heart.get("marker") or not heart.get("patch_sha256") or not heart.get("artifacts"):
        raise RuntimeError("Custom Heart provenance is incomplete")

    framework = app / "Dependencies/Middleware/Lib.xcframework"
    for file in heart["artifacts"]:
        actual = framework / file["path"]
        if not actual.is_file() or digest(actual) != file["sha256"]:
            raise RuntimeError("Installed custom middleware differs: " + file["path"])
    marker = heart["marker"].encode("utf-8")
    binaries = [v for v in framework.rglob("Lib") if v.is_file()]
    if not binaries or not all(contains(v, marker) for v in binaries):
        raise RuntimeError("One or more embedded Heart slices lack the expected custom marker")

    evidence.mkdir(parents=True, exist_ok=True)
    command(["xcodebuild", "-version"], app, evidence)
    command(["xcrun", "--sdk", "iphoneos", "--show-sdk-version"], app, evidence)

    derived = evidence / "DerivedData-iPad"
    command([
        "xcodebuild", "build",
        "-project", "Anytype.xcodeproj",
        "-scheme", "Anytype",
        "-configuration", "Release-Anytype",
        "-destination", "generic/platform=iOS",
        "-sdk", "iphoneos",
        "-derivedDataPath", str(derived),
        "OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED",
        "CODE_SIGNING_ALLOWED=NO",
        "CODE_SIGNING_REQUIRED=NO",
        "CODE_SIGN_IDENTITY=",
        "CODE_SIGN_ENTITLEMENTS=",
        "PROVISIONING_PROFILE_SPECIFIER=",
        "AD_HOC_CODE_SIGNING_ALLOWED=YES",
    ], app, evidence)

    built = derived / "Build/Products/Release-Anytype-iphoneos/Anytype.app"
    if not built.is_dir():
        raise RuntimeError("Actual iPad device .app was not produced")
    with (built / "Info.plist").open("rb") as stream:
        info = plistlib.load(stream)
    if 2 not in info.get("UIDeviceFamily", []):
        raise RuntimeError("Built app does not support iPad")
    binary = built / info["CFBundleExecutable"]
    if not binary.is_file() or not contains(binary, marker):
        raise RuntimeError("Built app executable does NOT contain the custom Heart marker")
    if (built / "_CodeSignature").exists():
        raise RuntimeError("Unexpected signature on this explicitly unsigned trial app")

    payload_app = evidence / "ipa/Payload/Anytype.app"
    if payload_app.exists():
        raise RuntimeError("Refusing to repackage a stale IPA output")
    payload_app.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(built, payload_app, symlinks=True)
    info.update(
        CFBundleIdentifier="com.gloiiire.anytype.torahtrial",
        CFBundleDisplayName="Pinkha Torah Trial",
        PinkhaNativeHeartPatchSHA256=heart["patch_sha256"],
        PinkhaNativeHeartMarker=heart["marker"],
        PinkhaNativeAppCommit=git(app, "rev-parse", "HEAD"),
    )
    with (payload_app / "Info.plist").open("wb") as stream:
        plistlib.dump(info, stream, fmt=plistlib.FMT_BINARY)

    ipa = evidence / "Pinkha-Native-Derived-iPad-Unsigned.ipa"
    command(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent",
             str(payload_app.parent), str(ipa)], app, evidence)
    with zipfile.ZipFile(ipa) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("IPA ZIP integrity validation failed")
        required = "Payload/Anytype.app/Info.plist"
        if required not in archive.namelist():
            raise RuntimeError("Malformed IPA: missing app Info.plist")
        with archive.open(required) as stream:
            packaged = plistlib.load(stream)
        if (packaged["PinkhaNativeHeartMarker"] != heart["marker"]
                or packaged["PinkhaNativeAppCommit"] != git(app, "rev-parse", "HEAD")):
            raise RuntimeError("Packaged app provenance mismatch")

    result = {
        "status": "PASS",
        "scope": "Custom Heart + iPad device build + unsigned IPA only",
        "tests": "NOT_RUN_BY_REQUEST",
        "physical_ipad_verified": False,
        "signed": False,
        "heart_sha": heart["heart_sha"],
        "heart_marker": heart["marker"],
        "heart_patch_sha256": heart["patch_sha256"],
        "app_sha": git(app, "rev-parse", "HEAD"),
        "branch": git(app, "branch", "--show-current"),
        "ipa": str(ipa),
        "ipa_sha256": digest(ipa),
        "bundle_id": packaged["CFBundleIdentifier"],
        "extensions_retained": (payload_app / "PlugIns").is_dir(),
    }
    (evidence / "fast-ipa-receipt.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
