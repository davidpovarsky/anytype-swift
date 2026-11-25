#!/usr/bin/env python3
"""Qualify post-Apply projection authority and affected client lifetime controls."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MODULE = REPO / "Modules/ProtobufMessages"
SWIFT = "/usr/local/bin/swift"
NATIVE_MANIFEST = "2f76212f9fcd749aeb9e806b941e0fd0b54eba17e5cc842adb81c7eb3bae0f38"
PINS = {
    "swift-protobuf": "c6fe6442e6a64250495669325044052e113e990c",
    "swift-crypto": "e8d6eba1fef23ae5b359c46b03f7d94be2f41fed",
    "swift-asn1": "917b472dbe53ba699cbb0495f9a95a084bc6364d",
}
SUPPORT = [
    "ResponceProtocols.swift",
    "PinkhaNativeReadLifetime.swift",
    "InvocationMesagesHandlerProtocol.swift",
    "InvocationSettings.swift",
    "Generated/CommandsInvocation/invocation-adoption.generated.swift",
]
NEW = ["PinkhaHeartSemanticAnchor" + name + ".swift" for name in ("Wire", "JSON", "Protobuf", "Client", "Native", "Publication", "ApplyObservation")]
TESTS = ["PinkhaHeartSemanticAnchor" + name + "Tests.swift" for name in ("Wire", "Client", "Observation")]

def require(value, label):
    if not value:
        raise ValueError(label)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def install(source, target):
    # Keep unchanged input paths and mtimes for the existing build cache.
    if target.is_file() and digest(source) == digest(target):
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)

def read(path):
    return json.loads(path.read_text())

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args], text=True).strip()

def source_guard(args):
    require(git("rev-parse", "HEAD") == args.expected_app_sha and not git("status", "--porcelain"),
        "Exact clean reviewed source commit required")

def prepare(args):
    source_guard(args)
    require(not (args.run / "evidence/source-manifest.json").exists(), "Fresh evidence attempt required")
    prior = None
    if args.reuse_manifest is None:
        require(not args.package.exists(), "Fresh package or explicit prior manifest required")
    else:
        prior = read(args.reuse_manifest)
        require(args.package.is_dir(), "Missing stable package to reuse")
        archive = args.run / "evidence/prior-package-sources"
        require(not archive.exists(), "Prior source snapshot already exists")
        for target, row in prior["files"].items():
            require(digest(args.package / target) == row["sha256"], "Prior package differs from original manifest")
            saved = archive / target
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(args.package / target, saved)
            require(digest(saved) == row["sha256"], "Original source snapshot changed")
        save(args.run / "evidence/prior-source.json", {
            "original_app_sha": prior["app_sha"], "manifest": str(args.reuse_manifest),
            "manifest_sha256": digest(args.reuse_manifest), "source_archive": str(archive),
            "files_preserved": len(prior["files"]), "status": "EXACT_ORIGINAL_INPUTS_RETAINED"
        })
    package = args.package
    sources = sorted((MODULE / "Sources/Protocol").rglob("*.swift"))
    require(len(sources) == 685, "Unexpected generated protocol inventory")
    sources += [MODULE / "Sources" / path for path in SUPPORT + NEW]
    require(len(sources) == 697, "Wrong copied product source count")
    files = {}
    for source in sources:
        target = package / "Sources/ProtobufMessages" / source.relative_to(MODULE / "Sources")
        target.parent.mkdir(parents=True, exist_ok=True)
        install(source, target)
        files[str(target.relative_to(package))] = {"repo_path": str(source.relative_to(REPO)), "sha256": digest(source)}
    selected = []
    for name in TESTS:
        source = MODULE / "Tests/ProtobufMessagesTests" / name
        target = package / "Tests/ProtobufMessagesTests" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        install(source, target)
        files[str(target.relative_to(package))] = {"repo_path": str(source.relative_to(REPO)), "sha256": digest(source)}
        cls = name[:-6]
        selected.extend(cls + "." + method for method in re.findall(r"func (test[A-Za-z0-9_]+)\(", source.read_text()))
    require(len(selected) == len(set(selected)) == 37, "Exact reviewed wire/client/observation method catalog required")
    catalog = sorted(selected)
    # Publication now follows authority readback, so every client lifetime
    # control and the phase observer are affected. Pure request/JSON/mark codec
    # controls are unchanged and retain their existing native fixture evidence.
    selected = [name for name in catalog if name.startswith((
        "PinkhaHeartSemanticAnchorClientTests.", "PinkhaHeartSemanticAnchorObservationTests."))]
    selected += [
        "PinkhaHeartSemanticAnchorWireTests.testActualNativePageRequestDigestsEventAndColdReadback",
        "PinkhaHeartSemanticAnchorWireTests.testCapturedProjectionAndMarksRequireExactPreflightAndReadback",
        "PinkhaHeartSemanticAnchorWireTests.testNewProjectionMaterializationRequiresIndependentPostApplyAuthority",
        "PinkhaHeartSemanticAnchorWireTests.testProjectionRejectsForeignAmbiguousStaleAndMalformedNativeEvents",
    ]
    require(len(set(selected)) == 27 and set(selected) <= set(catalog), "Exact 27 affected authority/lifetime controls required")
    classes = sorted({name.split(".", 1)[0] for name in selected})
    fixture = MODULE / "Tests/ProtobufMessagesTests/Fixtures/NativePage"
    for source in sorted(fixture.iterdir()):
        if not source.is_file() or source.name.startswith("."):
            continue
        target = package / "Tests/ProtobufMessagesTests/Fixtures/NativePage" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        install(source, target)
        files[str(target.relative_to(package))] = {"repo_path": str(source.relative_to(REPO)), "sha256": digest(source)}
    require(read(fixture / "SOURCE.json")["native_source_manifest_sha256"] == NATIVE_MANIFEST, "Wrong native fixtures")
    for name, row in read(fixture / "SOURCE.json")["files"].items():
        require(digest(fixture / name) == row["sha256"], "Native artifact bytes changed")
    install(HERE / "Package.template.swift", package / "Package.swift")
    files["Package.swift"] = {"repo_path": str((HERE / "Package.template.swift").relative_to(REPO)),
        "sha256": digest(HERE / "Package.template.swift")}
    actual = {str(p.relative_to(package)) for folder in ("Sources", "Tests")
        for p in (package / folder).rglob("*") if p.is_file()}
    require(actual == set(files) - {"Package.swift"}, "Unexpected source or resource in stable package")
    metadata = [
        "Modules/ProtobufMessages/Package.swift",
        "Tools/PinkhaSemanticAnchorSwiftControls/run_readback_projection_controls.py",
        "Tools/PinkhaSemanticAnchorWire/page-source.json",
    ]
    require(digest(REPO / metadata[-1]) == NATIVE_MANIFEST, "Qualified native154 source manifest changed")
    save(args.run / "evidence/source-manifest.json", {
        "status": "PREPARED_CONTROLS_NOT_RUN", "app_sha": args.expected_app_sha, "files": files,
        "package_root": str(package), "reuse_prior_manifest": str(args.reuse_manifest) if args.reuse_manifest else None,
        "product_source_count": len(sources), "selected_methods": sorted(selected),
        "catalog_methods": catalog, "selected_classes": sorted(classes), "dependency_revisions": PINS,
        "metadata_only_sources": {name: digest(REPO / name) for name in metadata},
        "native_manifest_sha256": NATIVE_MANIFEST,
        "native_sdk_body": "INACTIVE_NOT_TYPECHECKED_OR_LINKED",
        "app_wrapper": "NOT_COMPILED_IN_HOST_CONTROLS",
        "mounted_editor": "NOT_RUN", "app_capability": "OFF",
    })
    print(json.dumps({"status": "PREPARED_EXACT_SWIFT_CONTROL_COMPOSITION", "product_source_count": len(sources),
        "selected_methods": len(selected), "actual_methods_executed": 0}))

def verify(args):
    source_guard(args)
    manifest = read(args.run / "evidence/source-manifest.json")
    require(manifest["app_sha"] == args.expected_app_sha, "Wrong control source identity")
    require(manifest.get("package_root", str(args.run / "package")) == str(args.package), "Wrong stable package root")
    for target, row in manifest["files"].items():
        require(digest(REPO / row["repo_path"]) == row["sha256"]
            and digest(args.package / target) == row["sha256"], "Copied control source changed")
    for name, expected in manifest["metadata_only_sources"].items():
        require(digest(REPO / name) == expected, "Metadata source changed")
    return manifest

def toolchain():
    value = subprocess.check_output([SWIFT, "--version"], text=True).strip()
    require(value == "Swift version 6.4.3 (swift-6.4.3-RELEASE)\nTarget: aarch64-unknown-linux-gnu"
        and platform.machine() == "aarch64", "Explicit Oracle Swift profile required")
    executable = Path(SWIFT).resolve()
    return {"version": value, "executable": str(executable), "executable_sha256": digest(executable)}

def dependencies(args):
    package = read(args.package / "Package.resolved")
    pins = {row["identity"]: row["state"]["revision"] for row in package["pins"]}
    require(pins == PINS, "Unreviewed Swift dependency resolution")
    checkouts = {}
    for name, revision in PINS.items():
        path = args.build_root / "scratch/checkouts" / name
        head = subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
        status = subprocess.check_output(["git", "-C", str(path), "status", "--porcelain"], text=True).strip()
        require(head == revision and not status, "Dependency checkout differs from exact clean pin")
        checkouts[name] = {"head": head, "clean": True}
    return {"pins": pins, "resolved_sha256": digest(args.package / "Package.resolved"), "checkouts": checkouts}

def command(args, argv, log, timeout):
    require(not log.exists(), "Refusing to overwrite original command log")
    env = dict(os.environ, TMPDIR=str(args.build_root / "tmp"), TERM="dumb",
        XDG_CACHE_HOME=str(args.build_root / "local-cache"), GIT_OPTIONAL_LOCKS="0")
    for directory in (args.build_root / "tmp", args.build_root / "local-cache",
                      args.build_root / "config", args.build_root / "security"):
        directory.mkdir(parents=True, exist_ok=True)
    with log.open("xb") as output:
        process = subprocess.Popen(argv, stdout=output, stderr=subprocess.STDOUT, env=env,
            cwd=args.package, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=10)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                pass
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=10)
            raise
    return {"argv": argv, "pid": process.pid, "exit_code": code, "log_sha256": digest(log)}

def common(args):
    return ["--package-path", str(args.package), "--scratch-path", str(args.build_root / "scratch"),
        "--cache-path", str(args.shared_cache), "--config-path", str(args.build_root / "config"),
        "--security-path", str(args.build_root / "security")]

def compiled_products(args, manifest):
    # Swift 6.4's pinned Linux build system emits a runner plus test module.
    directory = (args.build_root / "scratch/out/Products/Debug-linux-aarch64").resolve()
    require(directory.is_relative_to(args.build_root), "Products escaped owned build root")
    products = {}
    for name in ("ProtobufMessagesTests-test-runner", "ProtobufMessagesTests.so"):
        path = directory / name
        require(path.is_file(), "Missing actual Swift 6.4 test runner/module")
        with path.open("rb") as source:
            require(source.read(4) == b"\x7fELF", "Expected ELF test product")
        products[name] = {"path": str(path), "sha256": digest(path), "bytes": path.stat().st_size}
    dynamic = subprocess.check_output(["readelf", "-d", products["ProtobufMessagesTests-test-runner"]["path"]], text=True)
    require("Shared library: [ProtobufMessagesTests.so]" in dynamic, "Wrong test module loaded by runner")
    for target, row in manifest["files"].items():
        if "/Fixtures/NativePage/" not in target:
            continue
        relative = "PinkhaHeartSemanticAnchorControls_ProtobufMessagesTests.bundle/NativePage/" + Path(target).name
        path = directory / relative
        require(path.is_file() and digest(path) == row["sha256"], "Compiled fixture resource differs from source")
        products[relative] = {"path": str(path), "sha256": row["sha256"], "bytes": path.stat().st_size}
    return products

def verify_products(products):
    for row in products.values():
        path = Path(row["path"])
        require(path.is_file() and digest(path) == row["sha256"], "Qualified compiled product changed")

def execute(args):
    manifest = verify(args)
    evidence = args.run / "evidence"
    target = evidence / (args.mode + ".json")
    require(not target.exists(), "Original receipt cannot be overwritten")
    receipt = {"status": "PROBE_UNKNOWN", "app_sha": args.expected_app_sha, "mode": args.mode,
        "started_at": datetime.now(timezone.utc).isoformat(), "actual_methods_executed": 0,
        "actual_methods_passed": 0, "native_sdk_call": "NOT_RUN", "mounted_editor": "NOT_RUN", "app_capability": "OFF"}
    result_code = 1
    try:
        receipt["toolchain"] = toolchain()
        if args.mode == "resolve":
            argv = [SWIFT, "package", *common(args), "resolve"]
            result = command(args, argv, evidence / "resolve.log", 600)
            receipt["command"] = result
            require(result["exit_code"] == 0, "Swift dependency resolution failed")
            receipt["dependencies"] = dependencies(args)
            receipt["status"] = "PASS_EXACT_DEPENDENCY_RESOLUTION"
        elif args.mode == "build":
            receipt["dependencies"] = dependencies(args)
            argv = [SWIFT, "build", *common(args), "--build-tests", "-j", "1"]
            result = command(args, argv, evidence / "build.log", 2400)
            receipt["command"] = result
            require(result["exit_code"] == 0, "Swift control composition did not compile")
            products = compiled_products(args, manifest)
            runner = products["ProtobufMessagesTests-test-runner"]
            receipt.update(status="PASS_SWIFT_CONTROLS_COMPILE_ONLY", compiled_products=products,
                test_binary=runner["path"], test_binary_sha256=runner["sha256"],
                test_binary_bytes=runner["bytes"])
        else:
            built = read(evidence / "build.json")
            require(built["status"] == "PASS_SWIFT_CONTROLS_COMPILE_ONLY"
                and built["app_sha"] == args.expected_app_sha, "Unqualified Swift build")
            receipt["dependencies"] = dependencies(args)
            products = built["compiled_products"]
            verify_products(products)
            receipt.update(compiled_products=products, test_binary=built["test_binary"],
                test_binary_sha256=built["test_binary_sha256"])
            argv = [SWIFT, "test", *common(args), "--skip-build", "-j", "1",
                "--filter", "(" + "|".join(re.escape(name.split(".", 1)[0]) + "[./]" + re.escape(name.split(".", 1)[1])
                    for name in manifest["selected_methods"]) + ")$"]
            result = command(args, argv, evidence / "tests.log", 180)
            receipt["command"] = result
            rows = []
            for line in (evidence / "tests.log").read_text(errors="replace").splitlines():
                match = re.search(r"Test Case '([^']+)' (started|passed|failed)", line)
                if not match:
                    continue
                name = re.search(r"(PinkhaHeartSemanticAnchor(?:Wire|Client|Observation)Tests)[. /]+(test[A-Za-z0-9_]+)", match.group(1))
                require(name is not None, "An unselected XCTest method executed")
                rows.append({"method": name.group(1) + "." + name.group(2), "action": match.group(2)})
            starts = [row["method"] for row in rows if row["action"] == "started"]
            passes = [row["method"] for row in rows if row["action"] == "passed"]
            receipt.update(actual_methods_executed=len(starts), actual_methods_passed=len(passes), named_events=rows)
            require(result["exit_code"] == 0, "A selected Swift control failed")
            require(sorted(starts) == manifest["selected_methods"] and sorted(passes) == manifest["selected_methods"]
                and len(rows) == 2 * len(manifest["selected_methods"]), "Incomplete, skipped, duplicate or unselected Swift controls")
            verify_products(products)
            receipt["status"] = "PASS_" + str(len(starts)) + "_SELECTED_SWIFT_CONTROLS"
        verify(args)
        result_code = 0
    except BaseException as error:
        receipt.update(status="FAIL_" + args.mode.upper(), error_type=type(error).__name__, error=str(error))
    finally:
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        save(target, receipt)
    print(json.dumps({key: receipt.get(key) for key in ("status", "actual_methods_executed", "actual_methods_passed", "error")}))
    return result_code

def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("mode", choices=("prepare", "verify", "resolve", "build", "test"))
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--build-root", type=Path, required=True)
    parser.add_argument("--shared-cache", type=Path, required=True)
    parser.add_argument("--expected-app-sha", required=True)
    parser.add_argument("--package-root", type=Path)
    parser.add_argument("--reuse-manifest", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    for name in ("run", "build_root", "shared_cache"):
        setattr(args, name, getattr(args, name).resolve())
    args.package = (args.package_root or args.run / "package").resolve()
    if args.reuse_manifest is not None:
        args.reuse_manifest = args.reuse_manifest.resolve()
    require(args.package != REPO and args.package != args.build_root and args.package != args.shared_cache,
        "Package root must be an isolated control input directory")
    require(len({REPO, args.run, args.build_root, args.shared_cache}) == 4, "Separate source/run/build/cache paths required")
    require(re.fullmatch("[0-9a-f]{40}", args.expected_app_sha) is not None, "Exact source SHA required")
    if args.mode == "prepare":
        prepare(args)
        return 0
    if args.mode == "verify":
        verify(args)
        print("PASS_EXACT_CURRENT_SWIFT_CONTROL_SOURCE")
        return 0
    return execute(args)

if __name__ == "__main__":
    raise SystemExit(main())
