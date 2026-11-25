"""Inspect the actual consumer binary closure for standalone MiniApps engines.

Shared bridge/picker and existing Hanlin AI products are reported separately.
The check does not count an engine name in user text as an embedded runtime.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess

MACHO_MAGIC = {b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca", b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca",
               b"\xfe\xed\xfa\xcf", b"\xfe\xed\xfa\xce"}
ENGINE_FRAMEWORK = re.compile(r"^(?:Expo(?:ModulesCore)?|EXReact(?:RootView)?|React(?:[_-].*)?|RCT.*|NativeScript(?:Runtime)?|hermes|V8|v8)\.framework$", re.I)
ENGINE_SYMBOLS = (
    "_OBJC_CLASS_$_RCTBridge", "_OBJC_CLASS_$_RCTRootView",
    "_OBJC_CLASS_$_EXAppContext", "_OBJC_CLASS_$_EXModuleRegistry",
    "_ZN2v8", "_ZNK2v8", "_ZN8facebook5react", "_ZN8facebook6hermes",
)


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def inspect(app_source, built, evidence):
    app_source, built, evidence = map(lambda p: Path(p).resolve(), (app_source, built, evidence))
    target = evidence / "consumer-runtime-boundary"
    target.mkdir(parents=True, exist_ok=False)
    pin = json.loads((app_source / "Tools/Hanlin/source.json").read_bytes())
    expected_packages = {"Packages/HanlinAgentSDK", "Packages/HanlinPlatform",
                         "Packages/HanlinPresentationSDK", "Packages/HanlinMiniAppsBridge"}
    require(set(pin["packages"]) == expected_packages,
            "The consumer's explicit shared SDK products changed")
    matches = []
    framework_names = sorted(path.name for path in built.rglob("*.framework") if path.is_dir())
    for name in framework_names:
        if ENGINE_FRAMEWORK.fullmatch(name):
            matches.append({"kind": "embedded_framework", "name": name})
    binaries = []
    seen = set()
    for candidate in sorted(built.rglob("*")):
        if not candidate.is_file():
            continue
        path = candidate.resolve()
        require(path.is_relative_to(built), "Consumer product aliases escape the actual app")
        if path in seen:
            continue
        seen.add(path)
        with path.open("rb") as stream:
            if stream.read(4) not in MACHO_MAGIC:
                continue
        number = len(binaries)
        dependencies = subprocess.run(["otool", "-L", str(path)], capture_output=True, text=True, timeout=60)
        symbols = subprocess.run(["nm", "-gU", str(path)], capture_output=True, text=True, timeout=120)
        (target / (str(number) + "-dependencies.log")).write_text(dependencies.stdout + dependencies.stderr)
        (target / (str(number) + "-symbols.log")).write_text(symbols.stdout + symbols.stderr)
        dependencies.check_returncode()
        symbols.check_returncode()
        for line in dependencies.stdout.splitlines()[1:]:
            load = line.strip().split(" (", 1)[0]
            if any(ENGINE_FRAMEWORK.fullmatch(part) for part in Path(load).parts):
                matches.append({"kind": "linked_framework", "binary": str(path.relative_to(built)), "load": load})
        for marker in ENGINE_SYMBOLS:
            if marker in symbols.stdout:
                matches.append({"kind": "native_engine_symbol", "binary": str(path.relative_to(built)), "marker": marker})
        binaries.append({"path": str(path.relative_to(built)), "bytes": path.stat().st_size,
                         "sha256": digest(path), "dependencies_log": str(number) + "-dependencies.log",
                         "symbols_log": str(number) + "-symbols.log",
                         "dependencies_log_sha256": digest(target / (str(number) + "-dependencies.log")),
                         "symbols_log_sha256": digest(target / (str(number) + "-symbols.log"))})
    require(binaries, "The actual original consumer app contains no observable Mach-O binary")
    result = {"schema": "miniapps.original-consumer-runtime-boundary/1",
              "status": "PASS" if not matches else "FAIL",
              "hanlin_revision": pin["revision"],
              "shared_miniapps_packages": ["Packages/HanlinMiniAppsBridge"],
              "preserved_hanlin_ai_packages": sorted(expected_packages - {"Packages/HanlinMiniAppsBridge"}),
              "frameworks": framework_names, "binaries": binaries,
              "standalone_engine_identity_matches": matches,
              "scope": "ACTUAL_EMBEDDED_MACHO_DYNAMIC_LOADS_AND_EXPORTED_ENGINE_IDENTITIES"}
    (target / "result.json").write_text(json.dumps(result, indent=2) + chr(10))
    require(not matches, "A standalone MiniApps engine was found in the original consumer app")
    return result
