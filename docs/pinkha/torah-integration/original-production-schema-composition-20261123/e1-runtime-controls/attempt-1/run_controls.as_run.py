#!/usr/bin/env python3
"""Run bounded E1 portable source controls. No Apple runtime qualification."""
import argparse, hashlib, json, os, pathlib, subprocess, sys, time

BASE = "642a8b9cd9cd243e820db154ea2471b6882e2a94"
ROOT = "Modules/AnytypeCore/AnytypeCore/Utils/"
PRODUCT = [
    ROOT + "OriginalRuntimeEnvironment.swift",
    ROOT + "TargetsConstants.swift",
    ROOT + "UserDefaultWrapper/UserDefaultByAppGroupStorage.swift",
    ROOT + "UserDefaultWrapper/UserDefaultStorage.swift",
]
RETAINED = [
    "Modules/AppTarget/Sources/AppTarget/AppTargetType.swift",
    ROOT + "CoreEnvironment.swift",
]
CASES = [
    "standalone-debug-migration-roundtrip", "standalone-release-defaults",
    "embedded-namespace-isolation", "first-standard-consumer-seals",
    "first-group-consumer-seals", "first-target-consumer-seals",
    "same-install-before-use", "conflicting-install-before-use",
    "invalid-group-recovery", "invalid-bundle-condition-recovery",
    "declared-target-mismatch", "cached-target-mismatch",
    "matching-direct-read-limitation", "container-denial-recovery",
    "original-cache-and-decode", "concurrent-first-use",
]
TRANSFORMS = {
    ROOT + "OriginalRuntimeEnvironment.swift": [
        ("import AppTarget\n", "", 1),
        ("Bundle.main", "E1Platform.bundle", 1),
        ("FileManager.default.containerURL", "E1Platform.containerURL", 1),
    ],
    ROOT + "TargetsConstants.swift": [],
    ROOT + "UserDefaultWrapper/UserDefaultByAppGroupStorage.swift": [
        ("UserDefaults(suiteName: environment.appGroup)", "E1Platform.groupStore(suiteName: environment.appGroup)", 1),
        ("UserDefaults.standard", "E1Platform.standard", 2),
    ],
    ROOT + "UserDefaultWrapper/UserDefaultStorage.swift": [
        ("import os\n", "", 1),
        ("UserDefaults.standard", "E1Platform.standard", 3),
    ],
    ROOT + "CoreEnvironment.swift": [
        ("import AppTarget\n", "", 1),
        ("import os.lock\n", "", 1),
        ("Bundle.main", "E1Platform.bundle", 1),
    ],
    "Modules/AppTarget/Sources/AppTarget/AppTargetType.swift": [],
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    commands = []
    source_rows = []
    def git(*parts):
        return subprocess.run(["git", "-C", str(repo), *parts],
            check=True, capture_output=True).stdout
    if git("rev-parse", "HEAD").decode().strip() != BASE:
        raise RuntimeError("source base changed")
    combined = []
    for path in RETAINED + PRODUCT:
        data = (repo / path).read_bytes() if path in PRODUCT else git("show", BASE + ":" + path)
        original = data.decode()
        projected = original
        applied = []
        for before, after, expected_count in TRANSFORMS[path]:
            count = projected.count(before)
            if count != expected_count:
                raise RuntimeError(f"projection count mismatch {path}: {before!r} {count} != {expected_count}")
            projected = projected.replace(before, after)
            applied.append({"from": before, "to": after, "count": count})
        source_rows.append({
            "path": path, "role": "affected-product" if path in PRODUCT else "unchanged-original",
            "sha256": sha(data), "projected_sha256": sha(projected.encode()),
            "transforms": applied,
        })
        combined.append("// BEGIN SOURCE: " + path + "\n" + projected + "\n// END SOURCE\n")
    harness = pathlib.Path(__file__).with_name("RuntimeEnvironmentControls.swift").read_bytes()
    combined.append(harness.decode())
    source = output / "CombinedControls.swift"
    source.write_text("\n".join(combined))
    manifest = {
        "base_sha": BASE, "product_paths": PRODUCT, "sources": source_rows,
        "harness_sha256": sha(harness), "combined_sha256": sha(source.read_bytes()),
        "scope": "Portable original state/storage behavior; Apple metadata/container/lock calls substituted explicitly.",
        "not_qualified": ["Apple signed AppGroup container access", "Apple OSAllocatedUnfairLock implementation",
            "real main-bundle metadata", "UIKit", "native library", "account bootstrap", "SDK/runtime/device"],
    }
    (output / "SOURCE_ADMISSION.json").write_text(json.dumps(manifest, indent=2) + "\n")
    def run(name, argv, timeout):
        started = time.time()
        with (output / (name + ".stdout.txt")).open("wb") as stdout, (output / (name + ".stderr.txt")).open("wb") as stderr:
            completed = subprocess.run(argv, cwd=repo, stdout=stdout, stderr=stderr, timeout=timeout)
        item = {"name": name, "argv": [str(x) for x in argv], "exit_code": completed.returncode,
            "elapsed_seconds": time.time() - started,
            "stdout_sha256": sha((output / (name + ".stdout.txt")).read_bytes()),
            "stderr_sha256": sha((output / (name + ".stderr.txt")).read_bytes())}
        commands.append(item)
        (output / "COMMANDS.json").write_text(json.dumps(commands, indent=2) + "\n")
        return completed.returncode
    run("swift-version", ["swift", "--version"], 20)
    parse = run("unprojected-product-parse",
        ["swiftc", "-frontend", "-parse", *[str(repo / p) for p in PRODUCT]], 40)
    binary = output / "runtime-environment-controls"
    compile_result = run("portable-compile",
        ["swiftc", "-swift-version", "6", "-parse-as-library", str(source), "-o", str(binary)], 120)
    results = []
    if compile_result == 0:
        for index, name in enumerate(CASES):
            fixture = output / ("fixture-" + str(index))
            rc = run(name, [str(binary), name, str(fixture)], 25)
            observed = None
            if rc == 0:
                observed = json.loads((output / (name + ".stdout.txt")).read_text())
                if observed.get("case") != name or observed.get("status") != "PASS" or observed.get("owned_fixture_cleanup") != "PASS":
                    raise RuntimeError("invalid actual control receipt")
            results.append({"case": name, "exit_code": rc, "observed": observed,
                "fixture_absent_after_return": not fixture.exists()})
    passed = sum(r["exit_code"] == 0 and r["fixture_absent_after_return"] for r in results)
    report = {
        "base_sha": BASE, "status": "PASS" if parse == 0 and compile_result == 0 and passed == len(CASES) else "FAIL",
        "unprojected_syntax_exit": parse, "portable_compile_exit": compile_result,
        "required_controls": len(CASES), "actual_controls": len(results), "passed_controls": passed,
        "binary_sha256": sha(binary.read_bytes()) if binary.exists() else None,
        "results": results, "scope": manifest["scope"], "not_qualified": manifest["not_qualified"],
    }
    (output / "RESULT.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in [
        "base_sha", "status", "unprojected_syntax_exit", "portable_compile_exit",
        "required_controls", "actual_controls", "passed_controls", "binary_sha256"]}, indent=2))
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
