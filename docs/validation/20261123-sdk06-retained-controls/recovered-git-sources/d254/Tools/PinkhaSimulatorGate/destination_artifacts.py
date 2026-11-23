"""Native test bundle identity for ordinary simulator XCTest installation.

UseDestinationArtifacts is device-only. Simulator preservation observes the
original store before AccountSelect instead of changing XCTest installation.
"""
from pathlib import PurePosixPath
import plistlib
import re

HOST = "io.anytype.app"
BLUEPRINT = "AnytypeTests"
BUNDLE = "PlugIns/AnytypeTests.xctest"
EXECUTABLE = BUNDLE + "/AnytypeTests"
RELATIVE = "__TESTHOST__/" + BUNDLE
LIMIT = 65_536


def require(condition, message):
    if not condition:
        raise ValueError(message)


def bounded_file(path, limit):
    require(path.is_file() and not path.is_symlink(), "Destination-artifact input is missing or a symlink")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    require(0 < len(raw) <= limit, "Destination-artifact input exceeds its bound")
    return raw


def test_bundle(app, carriers):
    app = app.resolve(strict=True)
    host = plistlib.loads(bounded_file(app / "Info.plist", LIMIT))
    bundle = app / BUNDLE
    require(bundle.is_dir() and not bundle.is_symlink() and bundle.resolve(strict=True).is_relative_to(app),
            "Installed native test bundle escaped its app")
    info = plistlib.loads(bounded_file(bundle / "Info.plist", LIMIT))
    require(host.get("CFBundleIdentifier") == HOST and info.get("CFBundleExecutable") == BLUEPRINT,
            "Installed native host/test executable identity differs")
    identifier = info.get("CFBundleIdentifier")
    require(isinstance(identifier, str) and re.fullmatch(r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", identifier)
            and identifier != HOST, "Installed native test bundle identifier is missing or invalid")
    executable = app / EXECUTABLE
    require(executable.is_file() and not executable.is_symlink()
            and executable.resolve(strict=True).is_relative_to(bundle.resolve(strict=True)),
            "Installed native test executable is missing or escaped")
    expected = carriers.get("manifest", {}).get("carriers", {}).get(EXECUTABLE)
    require(isinstance(expected, dict) and set(expected) == {"sha256", "bytes"}
            and type(expected["bytes"]) is int and expected["bytes"] > 0
            and re.fullmatch(r"[0-9a-f]{64}", expected["sha256"] or ""),
            "Native test executable is absent from the exact code-carrier inventory")
    require(executable.stat().st_size == expected["bytes"], "Installed native test executable size differs")
    # code_carriers has already hashed every executable, including this one.
    return {"hostBundleIdentifier": HOST, "testBundleIdentifier": identifier,
            "relativeBundlePath": RELATIVE, "executableRelativePath": EXECUTABLE, **expected}



def validate_native_target(target):
    require(target.get("BlueprintName") == BLUEPRINT and target.get("IsAppHostedTestBundle") is True
            and target.get("IsUITestBundle", False) is False, "Simulator postflight requires the original native test target")
    require(target.get("TestHostBundleIdentifier") == HOST
            and target.get("UITargetAppBundleIdentifier", HOST) == HOST, "Native test host bundle identifier differs or is missing")
    require(target.get("TestBundlePath") == RELATIVE
            and target.get("TestBundleDestinationRelativePath", RELATIVE) == RELATIVE,
            "Native test bundle relative path differs or is missing")
    host = target.get("TestHostPath")
    require(isinstance(host, str) and host.startswith("__TESTROOT__/")
            and ".." not in PurePosixPath(host).parts
            and (host.endswith("/Anytype.app") or host.endswith("/Anytype.app/Anytype")),
            "Original native test host path is missing or invalid")
    require(isinstance(target.get("TestingEnvironmentVariables"), dict), "Native XCTest injection environment is missing")
    require(target.get("UseDestinationArtifacts", False) is False, "Simulator postflight cannot use device-only destination artifacts")
