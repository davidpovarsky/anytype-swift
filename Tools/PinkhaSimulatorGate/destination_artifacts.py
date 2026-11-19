"""Properties-only proof for XCTest's documented already-installed-host mode."""
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import plistlib
import re
import subprocess
import time

HOST = "io.anytype.app"
BLUEPRINT = "AnytypeTests"
BUNDLE = "PlugIns/AnytypeTests.xctest"
EXECUTABLE = BUNDLE + "/AnytypeTests"
RELATIVE = "__TESTHOST__/" + BUNDLE
PROOF = "type-preservation-destination-artifacts.json"
ENV = "PINKHA_TYPE_PRESERVATION_DESTINATION_ARTIFACTS_"
LIMIT = 65_536
MANUAL_LIMIT = 262_144
COMMAND_SECONDS = 30
MANUALS = {"xcodebuild": ("man1", "xcodebuild.1"), "xctestrun": ("man5", "xcodebuild.xctestrun.5")}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(raw):
    require(0 < len(raw) <= LIMIT, "Destination-artifact proof exceeds its bound")
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, "Duplicate destination-artifact proof key")
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=pairs)


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


def manual_text(raw, compressed):
    if compressed:
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            raw = stream.read(MANUAL_LIMIT + 1)
    require(0 < len(raw) <= MANUAL_LIMIT, "Expanded Xcode manual exceeds its bound")
    text = raw.decode("utf-8")
    text = re.sub(r"\\f(?:\[[^\]]*\]|\(..|.)", "", text)
    text = text.replace(r"\-", "-").replace(r"\&", "")
    # mdoc's Fl macro renders its argument with a leading hyphen.
    text = re.sub(r"(?m)(?:^\.Fl|(?<=[ \t])Fl)[ \t]+([A-Za-z0-9][A-Za-z0-9_-]*)", r"-\1", text)
    text = re.sub(r"(?m)^\.[A-Za-z]+(?:[ \t]+|$)", "", text)
    return " ".join(text.split())


def require_manual_support(manuals):
    xcodebuild, xctestrun = manuals["xcodebuild"], manuals["xctestrun"]
    require("test-without-building" in xcodebuild and "-xctestrun" in xcodebuild,
            "Selected xcodebuild manual does not support the required invocation")
    start = xctestrun.find("UseDestinationArtifacts")
    section = xctestrun[start:start + 6000] if start >= 0 else ""
    require("will not install test artifacts to the destination during testing" in section
            and all(name in section for name in ("TestHostBundleIdentifier", "TestBundleDestinationRelativePath",
                "UITargetAppBundleIdentifier", "TestBundlePath", "TestHostPath", "UITargetAppPath"))
            and "excluded" in section and "__TESTHOST__" in section,
            "Selected xctestrun manual does not establish destination-artifact no-install support")


def developer_directory(path):
    require(isinstance(path, str), "Selected Xcode path is not a string")
    executable = Path(path)
    require(executable.is_absolute() and ".." not in executable.parts
            and executable.parts[-3:] == ("usr", "bin", "xcodebuild"), "Unexpected selected xcodebuild layout")
    developer = executable.parents[2]
    require(developer.name == "Developer" and developer.parent.name == "Contents"
            and developer.parent.parent.suffix == ".app", "Selected xcodebuild is not in a full Xcode app")
    return developer


def capture(evidence, binding, code_sha, bundle, deadline):
    """Bounded read-only capability capture inside the existing installation deadline."""
    require(not (evidence / PROOF).exists(), "Refuse stale destination-artifact proof")
    def command(args):
        available = deadline - time.monotonic()
        require(available > 0, "Controlled install phase budget exhausted")
        result = subprocess.run(args, capture_output=True, timeout=min(COMMAND_SECONDS, available))
        require(result.returncode == 0 and len(result.stdout) <= 4096 and len(result.stderr) <= 4096,
                "Selected Xcode capability command failed or exceeded its bound")
        return result.stdout
    raw_path = command(["xcrun", "--find", "xcodebuild"])
    executable = Path(raw_path.decode("utf-8").strip())
    require(executable.is_absolute() and executable.is_file(), "Selected xcodebuild path is unavailable")
    executable = executable.resolve(strict=True)
    developer = developer_directory(str(executable))
    version = command([str(executable), "-version"]).decode("utf-8").strip()
    require(re.fullmatch(r"Xcode [0-9]+(?:\.[0-9]+)*\nBuild version [A-Za-z0-9]+", version),
            "Selected xcodebuild version is not the expected bounded format")
    records, texts = {}, {}
    for name, (section, filename) in MANUALS.items():
        candidates = [developer / "usr/share/man" / section / (filename + suffix) for suffix in ("", ".gz")]
        candidates = [p for p in candidates if p.exists()]
        require(len(candidates) == 1, "Selected Xcode manual is missing or ambiguous")
        source = candidates[0].resolve(strict=True)
        require(source.is_relative_to(developer), "Selected Xcode manual escaped its toolchain")
        raw = bounded_file(source, MANUAL_LIMIT)
        compressed = candidates[0].suffix == ".gz"
        texts[name] = manual_text(raw, compressed)
        saved = "type-preservation-" + filename + (".gz" if compressed else "")
        with (evidence / saved).open("xb") as stream:
            stream.write(raw)
        records[name] = {"sourcePath": str(source), "file": saved, "sha256": sha256(raw),
                         "bytes": len(raw), "compressed": compressed}
    require_manual_support(texts)
    value = {"schemaVersion": 1, "status": "SUPPORTED_SELECTED_XCODE", "binding": binding,
             "codeCarriersSHA256": code_sha, "testBundle": bundle, "xcodebuildPath": str(executable),
             "xcodebuildVersion": version, "manuals": records}
    validate(value, binding, code_sha, evidence)
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    require(len(raw) <= LIMIT, "Destination-artifact proof exceeds its bound")
    with (evidence / PROOF).open("xb") as stream:
        stream.write(raw)
    require(deadline - time.monotonic() > 0, "Controlled install phase budget exhausted")
    return value


def validate(value, binding, code_sha, evidence=None):
    require(isinstance(value, dict) and set(value) == {"schemaVersion", "status", "binding", "codeCarriersSHA256",
        "testBundle", "xcodebuildPath", "xcodebuildVersion", "manuals"}, "Unknown destination-artifact proof schema")
    require(type(value["schemaVersion"]) is int and value["schemaVersion"] == 1
            and value["status"] == "SUPPORTED_SELECTED_XCODE" and value["binding"] == binding
            and value["codeCarriersSHA256"] == code_sha and re.fullmatch(r"[0-9a-f]{64}", code_sha or ""),
            "Destination-artifact source/build binding differs")
    developer = developer_directory(value["xcodebuildPath"])
    require(isinstance(value["xcodebuildVersion"], str)
            and re.fullmatch(r"Xcode [0-9]+(?:\.[0-9]+)*\nBuild version [A-Za-z0-9]+", value["xcodebuildVersion"]),
            "Destination-artifact selected Xcode identity is missing")
    bundle = value["testBundle"]
    require(isinstance(bundle, dict) and set(bundle) == {"hostBundleIdentifier", "testBundleIdentifier",
        "relativeBundlePath", "executableRelativePath", "sha256", "bytes"}
            and bundle["hostBundleIdentifier"] == HOST and bundle["relativeBundlePath"] == RELATIVE
            and bundle["executableRelativePath"] == EXECUTABLE
            and isinstance(bundle["testBundleIdentifier"], str)
            and re.fullmatch(r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", bundle["testBundleIdentifier"])
            and bundle["testBundleIdentifier"] != HOST
            and type(bundle["bytes"]) is int and bundle["bytes"] > 0
            and re.fullmatch(r"[0-9a-f]{64}", bundle["sha256"] or ""), "Destination-artifact native bundle binding differs")
    require(isinstance(value["manuals"], dict) and set(value["manuals"]) == set(MANUALS),
            "Both selected Xcode manuals are required")
    texts = {}
    for name, record in value["manuals"].items():
        require(isinstance(record, dict) and set(record) == {"sourcePath", "file", "sha256", "bytes", "compressed"}
                and type(record["compressed"]) is bool
                and record["file"] == "type-preservation-" + MANUALS[name][1] + (".gz" if record["compressed"] else "")
                and isinstance(record["sourcePath"], str) and Path(record["sourcePath"]).is_absolute()
                and ".." not in Path(record["sourcePath"]).parts
                and Path(record["sourcePath"]).is_relative_to(developer) and type(record["bytes"]) is int
                and 0 < record["bytes"] <= MANUAL_LIMIT and re.fullmatch(r"[0-9a-f]{64}", record["sha256"] or ""),
                "Invalid selected Xcode manual receipt")
        if evidence is not None:
            raw = bounded_file(evidence / record["file"], MANUAL_LIMIT)
            require(len(raw) == record["bytes"] and sha256(raw) == record["sha256"], "Saved Xcode manual bytes changed")
            texts[name] = manual_text(raw, record["compressed"])
    if evidence is not None:
        require_manual_support(texts)
    return value


def environment(evidence, binding, code_sha):
    raw = bounded_file(evidence / PROOF, LIMIT)
    validate(decode(raw), binding, code_sha, evidence)
    return {ENV + "BASE64": base64.b64encode(raw).decode("ascii"), ENV + "SHA256": sha256(raw)}


def configure(target, environment, binding, code_sha):
    encoded = environment.get(ENV + "BASE64")
    require(isinstance(encoded, str) and 0 < len(encoded) <= 87_384, "Missing destination-artifact capability proof")
    raw = base64.b64decode(encoded, validate=True)
    require(sha256(raw) == environment.get(ENV + "SHA256"), "Destination-artifact capability proof changed")
    validate(decode(raw), binding, code_sha)
    require(target.get("BlueprintName") == BLUEPRINT and target.get("IsAppHostedTestBundle") is True
            and target.get("IsUITestBundle", False) is False, "Destination-artifact mode requires the original native test target")
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
    require(target.get("UseDestinationArtifacts", False) is False, "Refuse an already changed destination-artifact target")
    target.update(UseDestinationArtifacts=True, TestHostBundleIdentifier=HOST,
                  TestBundleDestinationRelativePath=RELATIVE, UITargetAppBundleIdentifier=HOST)
    for name in ("TestBundlePath", "TestHostPath", "UITargetAppPath"):
        target.pop(name, None)
