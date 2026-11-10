"""Build ONLY the real native Pinkha iPad app with its verified custom Heart.

No XCTest, no UI tests, no simulator. This produces an UNSIGNED IPA for later
signing/sideloading, not a TestFlight or physical-device validation pass.
"""
import argparse
import json
import platform
import plistlib
import re
import shutil
import zipfile
from pathlib import Path

from build_custom_heart import command, contains, digest, git


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--app-source", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--derived-data", type=Path)
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

    derived = args.derived_data.resolve() if args.derived_data else evidence / "DerivedData-iPad"
    if args.derived_data:
        from build_native_ipa import prepare_source_cache
        prepare_source_cache(app, derived)
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
    if not binary.is_file():
        raise RuntimeError("Built iPad app executable is missing")
    # Gomobile produces a static Lib.framework. Xcode embeds a generated
    # framework stub and links the library's code into the executable; linker
    # stripping can remove the Go ldflags marker string. Absence of that marker
    # in the final app executable is NOT evidence that stock Heart was linked.
    # Verify the exact custom input above and Xcode's actual source selection.
    device_log = evidence / "command-02.log"
    if not device_log.is_file():
        raise RuntimeError("The Xcode device-build provenance log is missing")
    build_log = device_log.read_text(encoding="utf-8", errors="replace")
    chosen_slice = str(framework / "ios-arm64" / "Lib.framework")
    if ("ProcessXCFramework " + str(framework)) not in build_log or chosen_slice not in build_log:
        raise RuntimeError("Xcode did not process the verified custom Heart iOS slice")
    embedded_lib = built / "Frameworks/Lib.framework/Lib"
    if not embedded_lib.is_file():
        raise RuntimeError("Built iPad app is missing the expected Lib.framework")
    if (built / "_CodeSignature").exists():
        raise RuntimeError("Unexpected signature on this explicitly unsigned trial app")

    payload_app = evidence / "ipa/Payload/Anytype.app"
    if payload_app.exists():
        raise RuntimeError("Refusing to repackage a stale IPA output")
    payload_app.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(built, payload_app, symlinks=True)
    parent_bundle_id = "com.gloiiire.anytype.torahtrial"
    info.update(
        CFBundleIdentifier=parent_bundle_id,
        CFBundleDisplayName="Pinkha Torah Trial",
        PinkhaNativeHeartPatchSHA256=heart["patch_sha256"],
        PinkhaNativeHeartMarker=heart["marker"],
        PinkhaNativeAppCommit=git(app, "rev-parse", "HEAD"),
    )
    with (payload_app / "Info.plist").open("wb") as stream:
        plistlib.dump(info, stream, fmt=plistlib.FMT_BINARY)

    # Automatically and permanently retarget all nested extension bundle identifiers
    # so every PlugIns/*.appex ID matches parent_bundle_id + '.' prefix.
    plugins_dir = payload_app / "PlugIns"
    extension_conversions = []
    if plugins_dir.is_dir():
        used_ids = {parent_bundle_id}
        for appex in sorted(plugins_dir.glob("*.appex")):
            ext_plist = appex / "Info.plist"
            if not ext_plist.is_file():
                continue
            with ext_plist.open("rb") as stream:
                ext_info = plistlib.load(stream)
            prev_id = ext_info.get("CFBundleIdentifier")
            if not isinstance(prev_id, str):
                raise RuntimeError(f"Extension missing bundle ID: {ext_plist}")
            if prev_id.startswith(parent_bundle_id + "."):
                suffix = prev_id[len(parent_bundle_id) + 1:]
            elif prev_id.startswith("io.anytype.app."):
                suffix = prev_id[len("io.anytype.app."):]
            elif prev_id == parent_bundle_id:
                suffix = appex.stem
            else:
                suffix = prev_id.split(".")[-1]
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", suffix) or ".." in suffix:
                suffix = appex.stem
            new_id = f"{parent_bundle_id}.{suffix}"
            if new_id in used_ids:
                raise RuntimeError(f"Duplicate extension bundle ID: {new_id}")
            used_ids.add(new_id)
            if new_id != prev_id:
                ext_info["CFBundleIdentifier"] = new_id
                with ext_plist.open("wb") as stream:
                    plistlib.dump(ext_info, stream, fmt=plistlib.FMT_BINARY)
            extension_conversions.append({"extension": appex.name, "from": prev_id, "to": new_id})
    if not extension_conversions:
        raise RuntimeError("No app extensions found in PlugIns to package")

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
        ext_found = []
        for name in archive.namelist():
            match = re.fullmatch(r"^Payload/[^/]+\.app/PlugIns/([^/]+)\.appex/Info\.plist$", name)
            if match:
                with archive.open(name) as stream:
                    ext_packaged = plistlib.load(stream)
                ext_id = ext_packaged.get("CFBundleIdentifier", "")
                if not ext_id.startswith(parent_bundle_id + "."):
                    raise RuntimeError(f"Invalid packaged extension ID: {ext_id}")
                ext_found.append({"path": name, "id": ext_id})
        if not ext_found:
            raise RuntimeError("Malformed IPA: missing PlugIns extensions in archive")

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
        "app_executable_sha256": digest(binary),
        "branch": git(app, "branch", "--show-current"),
        "ipa": str(ipa),
        "ipa_sha256": digest(ipa),
        "bundle_id": packaged["CFBundleIdentifier"],
        "extensions_retained": (payload_app / "PlugIns").is_dir(),
        "extensions": extension_conversions,
        "extension_ids": [c["to"] for c in extension_conversions],
    }
    (evidence / "fast-ipa-receipt.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
