"""Build-only r15 Apple runtime using the unchanged, hash-bound r14 builder helpers."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import subprocess
import sys

import run_t5_coverage_ci as coverage
import run_t5_pairs_ci as pair_ci
import r15_runtime_go as launcher

HELPER_SHA = "0ebbe2f6227418eac2c532b0058290158319ba9f786baaf445de444887e8c669"
INVENTORY_SHA = "f0e4a4c2d1b4c1baa11347362cfd18368ad272a8902b2beaf8de52270f809ee7"
MOBILE_VERSION = "v0.0.0-20250218173827-cd096645fcd3"
MOBILE_MODULE_SUM = "h1:0V/7Y1FEaFdAzb9DkVDh4QFp4vL4yYCiJ5cjk80lZyA="
MOBILE_MOD_SUM = "h1:j5VYNgQ6lZYZlzHFjdgS2UeqRSZunDk+/zXVTAIA3z4="
MOBILE_SEED_HASHES = {
    "go.mod": "c66fe96bdc57fb4a025ac8dc2cc612d3a0dbd52cd81d4470251c08c103297672",
    "go.sum": "371be5a55bf2fe640a45030b4254022a30f1bac6b3d0428c6767a82dfafe32f9",
}
MOBILE_GRAPH_REQUIRED = {
    "golang.org/x/exp/shiny": {
        "Version": "v0.0.0-20230817173708-d852ddb80c63",
        "Sum": "h1:3AGKexOYqL+ztdWdkB1bDwXgPBuTS/S8A4WzuTvJ8Cg=",
        "GoModSum": "h1:UH99kUObWAZkDnWqppdQe5ZhPYESUw8I0zVV1uWBR+0=",
    },
    "dmitri.shuralyov.com/gpu/mtl": {
        "Version": "v0.0.0-20221208032759-85de2813cf6b",
        "Sum": "h1:a26Bdkl2B9PmYN6vGXnnfB2UGKjz0Moif1aEg+xTd7M=",
        "GoModSum": "h1:H6x//7gZCb22OMCxBHrMx7a5I7Hp++hsVxbQ4BYO7hU=",
    },
}

MOBILE_BIND_SOURCES = {
    "cmd/gomobile/main.go": "7e28b18d4d3791bf05fe11d6323777fe7ad344baa54f57894442afeccd7e6a5c",
    "cmd/gomobile/bind.go": "f9039cc240190ee7cabd2a89f3b7d479d51bd40a18e79f1a032177ce803b64b0",
    "cmd/gomobile/bind_iosapp.go": "17cb5ce95d4194126099c94613f4f2769a7ede696f0b36f062ed985d7245e977",
}
GENERATED_GRAPH_REQUIRED = {
    "git.sr.ht/~sbinet/gg": {
        "effective_path": "git.sr.ht/~sbinet/gg", "effective_version": "v0.6.0",
        "sum": "h1:RIzgkizAk+9r7uPzf/VfbJHBMKUr0F5hRFxTUGMnt38=",
        "go_mod_sum": "h1:uucygbfC9wVPQIfrmwM2et0imr8L7KQWywX0xpFMm94=",
    },
}

MARKER = "pinkha-native-derived-v1-" + coverage.PATCH
CAPABILITY_MARKER = "pinkha-native-t5-lookup-v1-" + coverage.PATCH
VERSION = "v0.51.7-nightly.20261014.1-" + MARKER + "-" + CAPABILITY_MARKER
EXPECTED_SLICES = {
    ("ios-arm64/Lib.framework/Lib", "arm64"),
    ("ios-arm64_x86_64-simulator/Lib.framework/Lib", "arm64"),
    ("ios-arm64_x86_64-simulator/Lib.framework/Lib", "x86_64"),
}


def digest(path, normalize=False):
    data = path.read_bytes()
    if normalize:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def verify_source(heart, inventory):
    if coverage.git(heart, "rev-parse", "HEAD") != coverage.HEART:
        raise RuntimeError("Wrong native Heart source")
    approved = {entry["path"]: entry["after_sha256"] for entry in inventory["files"]}
    for path, expected in approved.items():
        relative = Path(path)
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("Unsafe native inventory path")
        target = (heart / relative).resolve(strict=True)
        if not target.is_relative_to(heart) or digest(target, True) != expected:
            raise RuntimeError("Approved native source differs: " + path)
    changed = set(coverage.git(heart, "diff", "--name-only", "HEAD").splitlines())
    untracked = set(coverage.git(heart, "ls-files", "--others", "--exclude-standard").splitlines())
    if ((changed | untracked) - set(approved)
            or coverage.git(heart, "diff", "--cached", "--name-only")):
        raise RuntimeError("Native changes outside the exact r15 inventory")
    return approved


def validate_framework(plist, slices):
    libraries = plist.get("AvailableLibraries", [])
    expected_libraries = {
        "ios-arm64": ("", {"arm64"}),
        "ios-arm64_x86_64-simulator": ("simulator", {"arm64", "x86_64"}),
    }
    if len(libraries) != 2:
        raise RuntimeError("Device and universal simulator framework entries required")
    seen = set()
    for library in libraries:
        identifier = library.get("LibraryIdentifier")
        if identifier not in expected_libraries or identifier in seen:
            raise RuntimeError("Unexpected or duplicate framework library")
        seen.add(identifier)
        variant, architectures = expected_libraries[identifier]
        if (library.get("LibraryPath") != "Lib.framework"
                or library.get("SupportedPlatform") != "ios"
                or library.get("SupportedPlatformVariant", "") != variant
                or set(library.get("SupportedArchitectures", [])) != architectures):
            raise RuntimeError("Framework platform or advertised architectures differ")
    actual = {(item.get("path"), item.get("architecture")) for item in slices}
    if actual != EXPECTED_SLICES or len(slices) != 3:
        raise RuntimeError("All three original Apple binary architectures must be verified")
    for item in slices:
        value = item.get("sha256", "")
        if item.get("marker") != VERSION or len(value) != 64 or set(value) - set("0123456789abcdef"):
            raise RuntimeError("A slice lacks the exact full r15 runtime identity or binary hash")
    return dict(device_architectures=["arm64"], simulator_architectures=["arm64", "x86_64"],
                verified_architecture_count=3)


def prepare_apple_bind(work, module_cache, gobind, selected_gobind, expected_sha256, env):
    """Prepare only the Apple workspace; init would install an unpinned latest gobind."""
    if env.get("GOPROXY") != "off" or env.get("GOFLAGS") != "-mod=readonly":
        raise RuntimeError("Offline read-only module resolution must remain enabled")
    if not module_cache.is_absolute() or not module_cache.is_dir():
        raise RuntimeError("Original resolved Go module cache is required")
    if (not selected_gobind or Path(selected_gobind).resolve() != gobind.resolve()
            or not gobind.is_file() or digest(gobind) != expected_sha256):
        raise RuntimeError("PATH must select the exact already-built pinned gobind")
    gopath = work / "gomobile-gopath"
    gopath.mkdir(exist_ok=False)
    mobile_cache = gopath / "pkg/gomobile"
    mobile_cache.mkdir(parents=True)
    selected = dict(env, GOPATH=str(gopath), GOMODCACHE=str(module_cache))
    receipt = dict(strategy="PINNED_GOBIND_AND_OWNED_APPLE_WORKSPACE",
                   gomobile_init="NOT_INVOKED_UNPINNED_LATEST_INSTALL",
                   mobile_version=MOBILE_VERSION, gobind=str(gobind), gobind_sha256=expected_sha256,
                   gopath=str(gopath), gomobile_cache=str(mobile_cache),
                   preserved_gomodcache=str(module_cache), goproxy=selected["GOPROXY"])
    return selected, receipt


def prepare_mobile_dependency_seed(work, mobile):
    """Copy the exact tool's module declarations; never edit the native or cached source."""
    if (mobile.get("Path") != "golang.org/x/mobile" or mobile.get("Version") != MOBILE_VERSION
            or mobile.get("Sum") != MOBILE_MODULE_SUM or mobile.get("GoModSum") != MOBILE_MOD_SUM
            or "Replace" in mobile or not mobile.get("Dir")):
        raise RuntimeError("Exact pinned mobile source and both checksums required before cache hydration")
    source = Path(mobile["Dir"])
    if not source.is_absolute() or not source.is_dir():
        raise RuntimeError("Original cached pinned mobile source directory required")
    data = {}
    for name, expected in MOBILE_SEED_HASHES.items():
        path = source / name
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise RuntimeError("Pinned mobile dependency declaration bytes differ: " + name)
        data[name] = path.read_bytes()
    target = work / "mobile-dependency-seed"
    target.mkdir(exist_ok=False)
    for name, raw in data.items():
        (target / name).write_bytes(raw)
    return target, dict(strategy="PINNED_MOBILE_GRAPH_BEFORE_OFFLINE_NATIVE_BIND",
                        mobile_version=MOBILE_VERSION, mobile_module_sum=MOBILE_MODULE_SUM,
                        mobile_go_mod_sum=MOBILE_MOD_SUM, source_directory=str(source),
                        owned_seed_directory=str(target), seed_sha256=dict(MOBILE_SEED_HASHES))


def validate_mobile_dependency_download(text):
    decoder, position, modules = json.JSONDecoder(), 0, {}
    while position < len(text):
        while position < len(text) and text[position].isspace():
            position += 1
        if position == len(text):
            break
        value, position = decoder.raw_decode(text, position)
        if (not isinstance(value, dict) or value.get("Error") or value.get("Replace")
                or not isinstance(value.get("Path"), str) or not value["Path"]
                or not isinstance(value.get("Version"), str) or not value["Version"]
                or value["Path"] in modules
                or any(not isinstance(value.get(key), str) or not value[key].startswith("h1:")
                       for key in ["Sum", "GoModSum"])):
            raise RuntimeError("Pinned mobile dependency download has an invalid or duplicate module receipt")
        modules[value["Path"]] = {key: value[key] for key in ["Version", "Sum", "GoModSum"]}
    for path, expected in MOBILE_GRAPH_REQUIRED.items():
        if modules.get(path) != expected:
            raise RuntimeError("Pinned tool transitive dependency/checksums differ: " + path)
    return dict(downloaded_module_count=len(modules), modules=modules)


def generated_dependency_seed(work, text, heart, mobile):
    """Mirror pinned getModuleVersions in owned files; do not edit native declarations."""
    if (mobile.get("Path") != "golang.org/x/mobile" or mobile.get("Version") != MOBILE_VERSION
            or mobile.get("Sum") != MOBILE_MODULE_SUM or mobile.get("GoModSum") != MOBILE_MOD_SUM
            or mobile.get("Replace") or not mobile.get("Dir")):
        raise RuntimeError("Exact pinned mobile source required for generated-graph preparation")
    for path, expected in MOBILE_BIND_SOURCES.items():
        target = Path(mobile["Dir"]) / path
        if target.is_symlink() or not target.is_file() or digest(target) != expected:
            raise RuntimeError("Pinned gomobile graph-generation source changed: " + path)
    records = launcher.module_records(text)
    requires, replacements, seen, native_count = [], [], set(), 0

    def token(value, version=False):
        pattern = r"v[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.+-]+)?" if version else r"[A-Za-z0-9_~+./-]+"
        if not isinstance(value, str) or not re.fullmatch(pattern, value):
            raise RuntimeError("Unsafe or missing module path/version in original native graph")
        return value

    for item in records:
        path = token(item.get("Path"))
        if path in seen:
            raise RuntimeError("Duplicate original native module path")
        seen.add(path)
        if item.get("Main"):
            if (path != launcher.NATIVE_MODULE or item.get("Version") or item.get("Replace")
                    or item.get("GoVersion") != launcher.PREPARED_GO_DIRECTIVE
                    or not item.get("Dir") or Path(item["Dir"]).resolve() != heart.resolve()):
                raise RuntimeError("Original native main module is not the exact owned Heart checkout")
            native_count += 1
            replacements.append(path + " => " + json.dumps(str(heart.resolve())))
            continue
        version = token(item.get("Version"), version=True)
        if item.get("Replace"):
            replacement = item["Replace"]
            # The reviewed native graph has no local dependency replacement
            # except its main Heart module. Versioned remote forks remain exact.
            target = token(replacement.get("Path"))
            selected_version = token(replacement.get("Version"), version=True)
            replacements.append(path + " " + version + " => " + target + " " + selected_version)
        else:
            requires.append(path + " " + version)
    if native_count != 1 or not requires or not replacements:
        raise RuntimeError("One native main module and its complete module declarations required")
    selected = {item["Path"]: item for item in records}
    if selected.get("golang.org/x/mobile", {}).get("Version") != MOBILE_VERSION:
        raise RuntimeError("Native graph changed the pinned mobile module")
    pair_ci.validate_genproto_selection(selected.get(pair_ci.GENPROTO_PATH, {}))
    seed = work / "generated-dependency-seed"
    seed.mkdir(exist_ok=False)
    raw = ("module gobind\n\ngo " + launcher.GENERATED_GO_DIRECTIVE + "\n\nrequire (\n"
           + "".join("\t" + line + "\n" for line in requires) + ")\n\nreplace (\n"
           + "".join("\t" + line + "\n" for line in replacements) + ")\n")
    (seed / "go.mod").write_text(raw, encoding="utf8", newline="\n")
    return seed, dict(strategy="EXACT_PINNED_GOMOBILE_FLATTENED_MODULE_GRAPH",
                      graph_role="GENERATED_GRAPH_NOT_ORIGINAL_NATIVE_GRAPH",
                      native_go_directive=launcher.PREPARED_GO_DIRECTIVE,
                      original_generated_go_directive=launcher.GENERATED_GO_DIRECTIVE,
                      input_native_graph_sha256=hashlib.sha256(text.encode()).hexdigest(),
                      source_module_count=len(records), initial_go_mod_sha256=digest(seed / "go.mod"),
                      go_mod_text=raw, bind_source_sha256=dict(MOBILE_BIND_SOURCES),
                      original_versions={item["Path"]: item.get("Version") for item in records})


def prepare_generated_hydration(work, original, expected_sha):
    """Give go mod download its own mutable declaration without changing bind input."""
    source = original / "go.mod"
    if (original.is_symlink() or source.is_symlink() or not source.is_file()
            or original.resolve().parent != work.resolve() or digest(source) != expected_sha):
        raise RuntimeError("Original owned generated module input changed before hydration")
    hydration = work / "generated-dependency-hydration"
    hydration.mkdir(exist_ok=False)
    shutil.copyfile(source, hydration / "go.mod")
    if digest(hydration / "go.mod") != expected_sha:
        raise RuntimeError("Generated hydration did not start from identical original declarations")
    return hydration


def validate_generated_hydration_manifest(original, hydrated, graph):
    """Allow only selected MVS requirements; keep the original bind manifest separate."""
    before = launcher.canonical_manifest(original, prepared=True)
    after = launcher.canonical_manifest(hydrated, prepared=True)
    if {key: value for key, value in before.items() if key != "Require"} != {
            key: value for key, value in after.items() if key != "Require"}:
        raise RuntimeError("Hydration changed original module/go/replacement or other non-require declarations")

    def requirements(document):
        values = {}
        for item in document["Require"]:
            if (not isinstance(item, dict) or set(item) - {"Path", "Version", "Indirect"}
                    or not isinstance(item.get("Path"), str) or not item["Path"]
                    or not isinstance(item.get("Version"), str) or not item["Version"]
                    or type(item.get("Indirect", False)) is not bool or item["Path"] in values):
                raise RuntimeError("Malformed or duplicate generated requirement")
            values[item["Path"]] = dict(version=item["Version"], indirect=item.get("Indirect", False))
        return values

    initial, resolved = requirements(before), requirements(after)
    if not initial or not set(initial).issubset(resolved):
        raise RuntimeError("Hydration removed an original generated requirement")
    changes, additions = [], []
    for path, actual in resolved.items():
        if actual["version"] != graph.get(path, {}).get("version"):
            raise RuntimeError("Hydrated requirement is not the checksum-verified selected version: " + path)
        if path in initial:
            if actual["indirect"] != initial[path]["indirect"]:
                raise RuntimeError("Hydration changed an original direct/indirect requirement")
            if actual["version"] != initial[path]["version"]:
                changes.append(dict(path=path, original=initial[path]["version"], hydrated=actual["version"]))
        else:
            if not actual["indirect"]:
                raise RuntimeError("Hydration added a new direct requirement")
            additions.append(dict(path=path, hydrated=actual["version"]))
    return dict(status="VERIFIED_SELECTED_MVS_REQUIREMENTS_ONLY",
                original_requirements=len(initial), hydrated_requirements=len(resolved),
                selected_version_updates=sorted(changes, key=lambda item: item["path"]),
                selected_indirect_additions=sorted(additions, key=lambda item: item["path"]),
                original_non_require_declarations_preserved=True)


def validate_generated_seed_graph(graph, downloads):
    launcher.validate_downloaded_graph(graph, downloads)
    for path, fields in GENERATED_GRAPH_REQUIRED.items():
        if any(graph.get(path, {}).get(key) != value for key, value in fields.items()):
            raise RuntimeError("Authoritative pinned generated dependency/checksums differ: " + path)
    return dict(selected_module_count=len(graph), downloaded_module_count=len(downloads))



def execute(args, control, evidence):
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("Actual ARM64 macOS/Xcode environment required; no native source modified")
    identity = coverage.require_identity(control)
    source, heart = args.source.resolve(), args.heart_source.resolve()
    work, artifacts = args.work.resolve(), args.artifacts.resolve()
    if len({control, source, heart, work, artifacts, evidence}) != 6:
        raise RuntimeError("Distinct source/control/native/work/artifact/evidence directories required")
    for tree, pin in [(source, coverage.SOURCE), (heart, coverage.HEART)]:
        if coverage.git(tree, "rev-parse", "HEAD") != pin or coverage.git(tree, "status", "--porcelain"):
            raise RuntimeError("Fresh exact clean source checkout required: " + str(tree))
    helper_path = control / "Tools/PinkhaNativeDerived/build_custom_heart.py"
    if digest(helper_path, True) != HELPER_SHA:
        raise RuntimeError("The reviewed native builder helper changed")
    helper = pair_ci.load_module("unchanged_r14_builder_helpers", helper_path)
    approval = source / pair_ci.APPROVAL_ROOT / "revision-15"
    patch, inventory_path = approval / "native-heart-integration.patch", approval / "native-heart-integration.json"
    if digest(patch, True) != coverage.PATCH or digest(inventory_path, True) != INVENTORY_SHA:
        raise RuntimeError("Exact reviewed r15 patch and inventory required")
    inventory = json.loads(inventory_path.read_text(encoding="utf8"))
    if (inventory["heart_sha"] != coverage.HEART or inventory["patch_sha256"] != coverage.PATCH
            or inventory.get("features", {}).get("t5_related_lookup") != 1):
        raise RuntimeError("Unexpected native capability inventory")
    if digest(source / pair_ci.GENPROTO_DECLARATION, True) != pair_ci.GENPROTO_DECLARATION_SHA:
        raise RuntimeError("Reviewed existing genproto declaration changed")
    real_go = Path(shutil.which("go") or "").resolve(strict=True)
    version = subprocess.check_output([str(real_go), "version"], text=True).strip()
    if version != "go version go1.26.5 darwin/arm64":
        raise RuntimeError("Pinned native Go 1.26.5 for ARM64 macOS required")
    if shutil.disk_usage(work).free < 8 * 1024**3:
        raise RuntimeError("Free disk reserve below 8 GiB")
    work.mkdir(exist_ok=True)
    if any(work.iterdir()):
        raise RuntimeError("Fresh empty owned runtime work directory required")
    artifacts.mkdir(parents=True, exist_ok=True)
    if any(artifacts.iterdir()):
        raise RuntimeError("Fresh empty owned artifact directory required")
    commands = []

    def run(command, name, env=None, cwd=heart, timeout=900):
        commands.append(dict(name=name, argv=[str(item) for item in command], cwd=str(cwd),
                             environment={key: (env or os.environ).get(key) for key in
                                          ["GOWORK", "GOFLAGS", "GOPROXY", "GOTOOLCHAIN", "GOMAXPROCS", "GOPATH", "GOMODCACHE",
                                           "CGO_ENABLED", "TMPDIR", "DEVELOPER_DIR"]}))
        coverage.write_receipt(evidence / "commands.json", commands)
        log_path = evidence / (name + ".log")
        with log_path.open("x", encoding="utf8") as log:
            result = subprocess.run(command, cwd=cwd, env=env, stdout=log,
                                    stderr=subprocess.STDOUT, timeout=timeout)
        if result.returncode:
            raise RuntimeError(name + " failed; see original retained log")
        return log_path

    xcode_log = run(["xcodebuild", "-version"], "xcode-version")
    xcode = xcode_log.read_text(encoding="utf8").strip()
    sdk_versions = {}
    for sdk in ["iphoneos", "iphonesimulator"]:
        path = run(["xcrun", "--sdk", sdk, "--show-sdk-version"], sdk + "-version")
        sdk_versions[sdk] = path.read_text(encoding="utf8").strip()
    if not xcode.startswith("Xcode 27") or any(value.split(".")[0] != "27" for value in sdk_versions.values()):
        raise RuntimeError("The verified Xcode 27 SDK lane is required")
    run([sys.executable, "-B", str(helper_path), "--heart-source", str(heart),
         "--patch", str(patch), "--inventory", str(inventory_path),
         "--approved-patch-sha256", coverage.PATCH, "--apply-approved-patch",
         "--target", "verify", "--evidence", str(evidence / "source-preflight")],
        "source-preflight")
    source_hashes = verify_source(heart, inventory)
    dependencies = [helper.fetch_tantivy(heart, arch) for arch in
                    ["darwin-arm64", "darwin-amd64", "ios-arm64", "ios-arm64-sim", "ios-amd64"]]
    gowork = work / "go.work"
    gowork.write_text("go 1.26.5\n\nuse " + str(heart) + "\n\nreplace "
                      + pair_ci.GENPROTO_PATH + " => " + pair_ci.GENPROTO_PATH + " "
                      + pair_ci.GENPROTO_VERSION + "\n", encoding="utf8")
    env = dict(os.environ, CGO_ENABLED="1", GOMAXPROCS="2", GOTOOLCHAIN="local",
               GOWORK=str(gowork), GOFLAGS="-mod=readonly")
    run([str(real_go), "mod", "download"], "pinned-module-download", env)
    mobile_path = run([str(real_go), "list", "-m", "-json", "golang.org/x/mobile"], "mobile-selection", env)
    mobile = json.loads(mobile_path.read_text(encoding="utf8"))
    # The lazy native graph omits platform dependencies needed by gomobile's
    # generated-module tidy. Hydrate the pinned tool's own complete graph in an
    # owned copy while downloads are still allowed, then keep all bind work offline.
    seed, mobile_dependencies = prepare_mobile_dependency_seed(work, mobile)
    seed_env = dict(env, GOWORK="off")
    download_log = run([str(real_go), "mod", "download", "-json", "all"],
                       "pinned-mobile-dependency-download", seed_env, cwd=seed)
    mobile_dependencies.update(validate_mobile_dependency_download(download_log.read_text(encoding="utf8")))
    if digest(seed / "go.mod") != MOBILE_SEED_HASHES["go.mod"]:
        raise RuntimeError("Cache hydration changed the pinned tool's module declaration")
    mobile_dependencies.update(resolved_go_sum_sha256=digest(seed / "go.sum"),
                               download_receipt_sha256=digest(download_log))
    coverage.write_receipt(evidence / "mobile-dependency-preparation.json", mobile_dependencies)
    native_graph_log = run([str(real_go), "list", "-m", "-json", "all"],
                           "original-native-graph-for-gomobile", env)
    graph_seed, graph_preparation = generated_dependency_seed(
        work, native_graph_log.read_text(encoding="utf8"), heart, mobile)
    coverage.write_receipt(evidence / "generated-original-input.json", graph_preparation)
    shutil.copyfile(graph_seed / "go.mod", evidence / "generated-original.go.mod")
    hydration = prepare_generated_hydration(work, graph_seed, graph_preparation["initial_go_mod_sha256"])
    graph_env = dict(env, GOWORK="off")
    checksum_log = run([str(real_go), "env", "-json", "GOSUMDB", "GONOSUMDB", "GOPRIVATE"],
                       "generated-graph-checksum-authority", graph_env, cwd=graph_seed)
    checksum_authority = json.loads(checksum_log.read_text(encoding="utf8"))
    if (checksum_authority.get("GOSUMDB") != "sum.golang.org"
            or any(checksum_authority.get(key) for key in ["GONOSUMDB", "GOPRIVATE"])):
        raise RuntimeError("Public generated dependencies need the standard checksum database; no bypass is added")
    initial_mod = run([str(real_go), "mod", "edit", "-json"],
                      "generated-graph-original-manifest", graph_env, cwd=graph_seed)
    manifest = launcher.canonical_manifest(json.loads(initial_mod.read_text(encoding="utf8")))
    # gomobile drops the compiler patch version and narrows workspace replacements.
    # Verify the original first, then explicitly prepare only the pinned native Go
    # requirement and reviewed genproto override in this separate mutable copy.
    scope_override = launcher.prepare_generated_module(real_go, graph_env, hydration, manifest)
    coverage.write_receipt(evidence / "generated-genproto-override.json", scope_override)
    prepared_manifest = launcher.validate_generated_preparation_receipt(scope_override, manifest)
    # go mod download may write MVS requirements even with GOFLAGS=-mod=readonly.
    # Preserve the original gomobile declarations and hydrate only this owned copy.
    graph_download = run([str(real_go), "mod", "download", "-json", "all"],
                         "generated-graph-module-download", graph_env, cwd=hydration)
    graph_env["GOPROXY"] = "off"
    graph_selection = run([str(real_go), "list", "-m", "-json", "all"],
                          "generated-graph-effective-modules", graph_env, cwd=hydration)
    hydrated_mod = run([str(real_go), "mod", "edit", "-json"],
                      "generated-graph-hydrated-manifest", graph_env, cwd=hydration)
    shutil.copyfile(hydration / "go.mod", evidence / "generated-hydrated.go.mod")
    graph = launcher.selected_graph(launcher.module_records(graph_selection.read_text(encoding="utf8")), heart)
    graph_preparation.update(validate_generated_seed_graph(
        graph, launcher.downloaded_modules(graph_download.read_text(encoding="utf8"))))
    if digest(graph_seed / "go.mod") != graph_preparation["initial_go_mod_sha256"]:
        raise RuntimeError("Generated cache hydration changed its original module declarations")
    hydration_delta = validate_generated_hydration_manifest(
        prepared_manifest, json.loads(hydrated_mod.read_text(encoding="utf8")), graph)
    selected_seed_genproto = next(item for item in launcher.module_records(graph_selection.read_text(encoding="utf8"))
                                 if item["Path"] == pair_ci.GENPROTO_PATH)
    pair_ci.validate_genproto_selection(selected_seed_genproto)
    graph_contract = dict(schema="pinkha-generated-module-graph-v2",
                          native_directory=str(heart), before_tidy_manifest=manifest,
                          prepared_tidy_manifest=prepared_manifest,
                          input_native_graph_sha256=graph_preparation["input_native_graph_sha256"],
                          selected_dependencies=graph)
    graph_contract_path = graph_seed / "bind-contract.json"
    coverage.write_receipt(graph_contract_path, graph_contract)
    graph_contract_sha = digest(graph_contract_path)
    original_versions = graph_preparation.pop("original_versions")
    graph_preparation.update(
        checksum_authority=checksum_authority, contract_sha256=graph_contract_sha,
        original_manifest_sha256=digest(initial_mod), download_receipt_sha256=digest(graph_download),
        effective_graph_sha256=digest(graph_selection), resolved_go_sum_sha256=digest(hydration / "go.sum"),
        hydrated_go_mod_sha256=digest(hydration / "go.mod"), hydrated_manifest_sha256=digest(hydrated_mod),
        hydration_delta=hydration_delta, immutable_bind_input_preserved=True,
        generated_scope_override=scope_override,
        selected_dependencies=graph,
        selected_version_changes=[dict(path=path, original=original_versions.get(path), generated=value["version"])
                                  for path, value in graph.items() if original_versions.get(path) != value["version"]])
    coverage.write_receipt(evidence / "generated-dependency-preparation.json", graph_preparation)
    env["GOPROXY"] = "off"
    run([str(real_go), "list", "-m", "-json", "all"], "resolved-native-modules", env)
    selection_path = run([str(real_go), "list", "-m", "-json", pair_ci.GENPROTO_PATH], "genproto-selection", env)
    genproto = pair_ci.validate_genproto_selection(json.loads(selection_path.read_text(encoding="utf8")))
    tools = {}
    for tool in ["gomobile", "gobind"]:
        target = heart / "deps" / tool
        run([str(real_go), "build", "-o", str(target), "golang.org/x/mobile/cmd/" + tool],
            tool + "-compile", env)
        tool_info = run([str(real_go), "version", "-m", str(target)], tool + "-identity", env)
        tools[tool] = dict(sha256=helper.digest(target), build_info_sha256=helper.digest(tool_info))
    shim = work / "bin"
    shim.mkdir()
    shim_source = control / "Tools/PinkhaNativeDerived/r15_runtime_go.py"
    shutil.copyfile(shim_source, shim / "go")
    (shim / "go").chmod(0o755)
    temporary = work / "gomobile-tmp"
    temporary.mkdir()
    audit = evidence / "go-launcher"
    audit.mkdir()
    env.update(PATH=str(shim) + os.pathsep + str(heart / "deps") + os.pathsep + env["PATH"],
               TMPDIR=str(temporary), PINKHA_T5_REAL_GO=str(real_go), PINKHA_T5_HEART=str(heart),
               PINKHA_T5_GOWORK=str(gowork), PINKHA_T5_MOBILE_TMP=str(temporary),
               PINKHA_T5_GO_AUDIT=str(audit),
               PINKHA_T5_GENERATED_CONTRACT=str(graph_contract_path),
               PINKHA_T5_GENERATED_CONTRACT_SHA256=graph_contract_sha)
    cache_log = run([str(real_go), "env", "GOMODCACHE"], "original-module-cache", env)
    module_cache = Path(cache_log.read_text(encoding="utf8").strip())
    env, mobile_preparation = prepare_apple_bind(
        work, module_cache, heart / "deps/gobind", shutil.which("gobind", path=env["PATH"]),
        tools["gobind"]["sha256"], env)
    coverage.write_receipt(evidence / "gomobile-preparation.json", mobile_preparation)
    framework = heart / "dist/ios/Lib.xcframework"
    if framework.exists():
        raise RuntimeError("Stale framework output is forbidden")
    framework.parent.mkdir(parents=True, exist_ok=True)
    ldflags = ("-X github.com/anyproto/anytype-heart/util/vcs.GitSummary=" + VERSION
               + " -X github.com/anyproto/anytype-heart/util/vcs.GitCommit=" + coverage.HEART)
    run([str(heart / "deps/gomobile"), "bind", "-tags",
         "nogrpcserver gomobile nowatchdog nosigar nomutexdeadlockdetector timetzdata rasterizesvg",
         "-ldflags", ldflags, "-target=ios", "-o", str(framework),
         "github.com/anyproto/anytype-heart/clientlibrary/service", "github.com/anyproto/anytype-heart/core"],
        "gomobile-bind", env, timeout=5400)
    run([str(real_go), "run", "cmd/iosrepack/main.go"], "original-ios-repack", env)
    records = [json.loads(path.read_text(encoding="utf8")) for path in sorted(audit.glob("*.json"))]
    verified_generated, original_generated = {}, {}
    for record in records:
        if "before_tidy_seed" in record and record.get("return_code") == 0:
            if (record.get("generated_contract_sha256") != graph_contract_sha
                    or record["before_tidy_seed"].get("status") != "EXACT_GENERATED_INPUT"):
                raise RuntimeError("Original generated input was not bound to the hydrated graph")
            actual_override = record.get("prepared_tidy_override", {})
            if (launcher.validate_generated_preparation_receipt(actual_override, manifest) != prepared_manifest
                    or actual_override["original_go_mod_sha256"] != record["before_tidy_seed"]["go_mod_sha256"]):
                raise RuntimeError("Actual generated dependency override differs from the verified input")
            after_tidy = record["after_tidy_modules"]
            launcher.validate_seeded_graph(after_tidy["selected_dependency_graph"], graph)
            original_generated[record["cwd"]] = record["before_tidy_seed"]
        if "before_build_modules" in record and record.get("return_code") == 0:
            if record.get("scope") != "generated-gobind" or record.get("selected_gowork") != "off":
                raise RuntimeError("Generated module scope was not recorded explicitly")
            checked = record["before_build_modules"]
            launcher.validate_seeded_graph(checked["selected_dependency_graph"], graph)
            launcher.validate_modules(checked["native"], checked["genproto_selection"], checked["genproto_download"], heart)
            if hashlib.sha256(checked["go_mod_text"].encode()).hexdigest() != checked["go_mod_sha256"]:
                raise RuntimeError("Original generated go.mod receipt bytes differ")
            verified_generated[record["cwd"]] = checked
    if (len(verified_generated) != 3 or set(original_generated) != set(verified_generated)
            or digest(graph_contract_path) != graph_contract_sha):
        raise RuntimeError("All three original generated architecture modules need exact dependency proofs")
    slices = helper.verify_framework_slices(framework, VERSION)
    source_slices = helper.verify_framework_slices(framework, coverage.HEART)
    if {(item["path"], item["architecture"], item["sha256"]) for item in source_slices} != {
            (item["path"], item["architecture"], item["sha256"]) for item in slices}:
        raise RuntimeError("Native source and full runtime markers did not bind identical slices")
    info = plistlib.loads((framework / "Info.plist").read_bytes())
    architecture_proof = validate_framework(info, slices)
    if verify_source(heart, inventory) != source_hashes:
        raise RuntimeError("Native source changed during framework build")
    if (coverage.require_identity(control) != identity
            or coverage.git(source, "status", "--porcelain")
            or digest(helper_path, True) != HELPER_SHA
            or digest(patch, True) != coverage.PATCH
            or digest(inventory_path, True) != INVENTORY_SHA):
        raise RuntimeError("Reviewed control/source inputs changed during build")
    receipt = dict(status="PASS", build_status="APPLE_FRAMEWORK_BUILT_NOT_EXECUTED",
                   **identity, source_sha=coverage.SOURCE, heart_sha=coverage.HEART, heart_tag=helper.TAG,
                   target="ios", patch_sha256=coverage.PATCH, inventory_sha256=INVENTORY_SHA,
                   files=inventory["files"], marker=MARKER, capability_marker=CAPABILITY_MARKER,
                   expected_app_get_version=VERSION, app_get_version_status="NOT_RUN_BUILD_ONLY",
                   native_tests="NOT_RUN_BUILD_ONLY", native_test_invocations=0,
                   client_enablement=pair_ci.CLIENT_DISABLED, swift_pairing_status="NOT_RUN", full_F10="NOT_PROVEN",
                   app_compile_flag="NOT_SET_BY_RUNTIME_BUILD", helper_sha256=HELPER_SHA,
                   go_version=version, xcode=xcode, sdk_versions=sdk_versions, native_dependencies=dependencies,
                   genproto_resolution=genproto, mobile_selection=mobile, tool_binaries=tools,
                   mobile_preparation=mobile_preparation, mobile_dependency_preparation=mobile_dependencies,
                   generated_dependency_preparation=graph_preparation, generated_input_proofs=original_generated,
                   go_launcher_sha256=digest(shim_source, True), generated_module_proofs=verified_generated,
                   binary_slices=slices, architecture_proof=architecture_proof, framework=str(framework),
                   artifacts=[dict(path=str(path.relative_to(framework)), sha256=helper.digest(path))
                              for path in sorted(framework.rglob("*")) if path.is_file()])
    receipt_path = evidence / "custom-heart-build.json"
    coverage.write_receipt(receipt_path, receipt)
    packaged_receipt = framework.parent / "PinkhaNativeHeartBuild.json"
    shutil.copyfile(receipt_path, packaged_receipt)
    archive = artifacts / "Pinkha-Universal-Verified-Heart-r15.tar.gz"
    run(["tar", "-czf", str(archive), "-C", str(framework.parent),
         "Lib.xcframework", "PinkhaNativeHeartBuild.json"], "package-runtime")
    artifact = dict(status="APPLE_RUNTIME_ARTIFACT_BUILT_NOT_EXECUTED",
                    path=str(archive), sha256=helper.digest(archive),
                    receipt_sha256=helper.digest(receipt_path), expected_app_get_version=VERSION,
                    binary_slices=slices, **identity, source_sha=coverage.SOURCE,
                    heart_sha=coverage.HEART, patch_sha256=coverage.PATCH,
                    swift_pairing_status="NOT_RUN", client_enablement=pair_ci.CLIENT_DISABLED)
    coverage.write_receipt(evidence / "runtime-artifact.json", artifact)
    return artifact


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    for name in ["source", "heart-source", "work", "artifacts", "evidence"]:
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=False)
    receipt = dict(status="RUNNING", started_at=datetime.now(timezone.utc).isoformat(),
                   component="runtime-r15", native_test_invocations=0, app_get_version_status="NOT_RUN_BUILD_ONLY",
                   swift_pairing_status="NOT_RUN", client_enablement=pair_ci.CLIENT_DISABLED, full_F10="NOT_PROVEN")
    path = evidence / "runtime-build-result.json"
    coverage.write_receipt(path, receipt)
    try:
        receipt.update(execute(args, Path(__file__).resolve().parents[2], evidence))
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
    receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
    coverage.write_receipt(path, receipt)
    print(json.dumps(receipt))
    return 0 if receipt["status"] == "APPLE_RUNTIME_ARTIFACT_BUILT_NOT_EXECUTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
