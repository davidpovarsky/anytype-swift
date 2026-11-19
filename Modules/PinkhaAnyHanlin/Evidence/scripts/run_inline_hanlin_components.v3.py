#!/usr/bin/env python3
"""Compile exact inline codec, exact Hanlin renderer, and all 13 exact XCTest methods.
This is a component proof with hashed cached dependency objects, not SwiftPM or UIKit.
The cached PinkhaAnyHanlin implementation objects are deliberately excluded.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os, re, subprocess, sys, time

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def now():
    return datetime.now(timezone.utc).isoformat()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--swiftc", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    debug = root / "Modules/PinkhaAnyEngine/.build/x86_64-unknown-windows-msvc/debug"
    work = root / "build/any-engine-port/inline-hanlin-components-v3"
    work.mkdir(parents=True, exist_ok=True)
    output = work / "receipt.json"
    originals = [
        "Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyInlineMarkdown.swift",
        "Modules/PinkhaAnyHanlin/Sources/PinkhaAnyHanlin/AnyHanlinPlainText.swift",
        "Modules/PinkhaAnyHanlin/Tests/PinkhaAnyHanlinTests/AnyHanlinPlainTextTests.swift",
    ]
    before = {p: sha(root / p) for p in originals}
    for p in originals:
        (work / Path(p).name).write_bytes((root / p).read_bytes())
    tests_source = (work / "AnyHanlinPlainTextTests.swift").read_text(encoding="utf-8")
    tests = re.findall(r"    func (test\w+)\(\)", tests_source)
    assert len(tests) == 13 and len(set(tests)) == 13
    main_source = "import XCTest\n@main struct InlineHanlinComponents {\n    static func main() {\n        XCTMain([testCase([\n"
    main_source += ",\n".join('            ("' + n + '", AnyHanlinPlainTextTests.' + n + ')' for n in tests)
    main_source += "\n        ])])\n    }\n}\n"
    (work / "Run.swift").write_text(main_source, encoding="utf-8")
    link_source = debug / "PinkhaAnyHanlinProbe.product/Objects.LinkFileList"
    objects = [Path(p.strip()) for p in link_source.read_text().splitlines() if p.strip()]
    excluded = [p for p in objects if "PinkhaAnyHanlinProbe.build" in str(p) or "PinkhaAnyHanlin.build" in str(p)]
    objects = [p for p in objects if p not in excluded]
    policy = debug / "PinkhaAnyIntegration.build/AnyNativeDocumentPolicy.swift.o"
    if policy not in objects:
        objects.append(policy)
    assert all(p.is_file() for p in objects)
    assert not any("PinkhaAnyHanlin.build" in str(p) for p in objects)
    deps = {p.relative_to(root).as_posix(): sha(p) for p in objects}
    for p in (debug / "Modules").glob("*.swiftmodule"):
        deps[p.relative_to(root).as_posix()] = sha(p)
    (work / "objects.rsp").write_text("\n".join('"' + str(p) + '"' for p in objects), encoding="utf-8")
    command = [
        str(args.swiftc), "-parse-as-library", "-swift-version", "6",
        "-module-name", "PinkhaInlineHanlinValidation", "-enable-testing",
        "-I", str(debug / "Modules"), "-module-cache-path", str(debug / "ModuleCache"),
        "-sdk", r"C:\Users\DAVID\AppData\Local\Programs\Swift\Platforms\6.3.3\Windows.platform\Developer\SDKs\Windows.sdk",
        "-use-ld=lld",
    ]
    for module in [
        "swift-crypto/Sources/CCryptoBoringSSLShims/include",
        "swift-crypto/Sources/CCryptoBoringSSL/include",
        "swift-cmark/src/include", "swift-cmark/extensions/include",
        "swift-markdown/Sources/CAtomic/include",
    ]:
        path = root / "Modules/PinkhaAnyEngine/.build/checkouts" / module
        command += ["-Xcc", "-fmodule-map-file=" + str(path / "module.modulemap"), "-Xcc", "-I" + str(path)]
    command += [str(work / "Run.swift")]
    command += [str(work / Path(p).name) for p in originals]
    command += ["@" + str(work / "objects.rsp"), "-o", str(work / "validation.exe")]
    receipt = {
        "status": "RUNNING", "startedAt": now(), "scope": "exact production inline codec and Hanlin renderer with exact 13 XCTest method source; cached dependency contracts; component namespace",
        "sourceManifest": before, "copiedSourceManifest": {p: sha(work / Path(p).name) for p in originals},
        "cachedDependencyManifest": deps, "excludedCachedHanlinImplementationObjects": [p.relative_to(root).as_posix() for p in excluded],
        "testNames": tests, "expectedTestCount": 13, "runnerSHA256": sha(Path(__file__)),
        "driverSHA256": sha(work / "Run.swift"), "command": command,
        "limitations": [
            "Does not claim a complete SwiftPM package build or UIKit/native engine execution.",
            "Fresh source is compiled in a component namespace. Original test imports remain unchanged; locally compiled declarations take precedence.",
            "Cached PinkhaAnyHanlin implementation objects are excluded, so the renderer under test is the freshly compiled source.",
            "Shared Host-to-AnyUI aliases are independently compiled and exercised by component33.",
        ],
    }
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    env = os.environ.copy()
    env["PATH"] = str(args.swiftc.parent) + os.pathsep + env.get("PATH", "")
    build_log = work / "build.log"; run_log = work / "test.log"
    build_code = None; run_code = None; harness_error = None
    started = time.monotonic()
    try:
        with build_log.open("wb") as stream:
            built = subprocess.run(command, cwd=work, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=180)
        build_code = built.returncode
        if build_code == 0:
            with run_log.open("wb") as stream:
                ran = subprocess.run([str(work / "validation.exe")], cwd=work, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=60)
            run_code = ran.returncode
    except Exception as error:
        harness_error = type(error).__name__
    text = run_log.read_text(encoding="utf-8", errors="replace") if run_log.is_file() else ""
    summaries = re.findall(r"Executed (\d+) tests?, with (\d+) failures", text)
    count, failures = tuple(map(int, summaries[-1])) if summaries else (0, 0)
    passed = re.findall(r"Test Case '[^']*\.(test\w+)' passed", text)
    source_stable = before == {p: sha(root / p) for p in originals}
    deps_stable = all((root / p).is_file() and sha(root / p) == digest for p, digest in deps.items())
    valid = build_code == 0 and run_code == 0 and count == 13 and failures == 0 and set(passed) == set(tests) and len(passed) == 13
    receipt.update({
        "status": "PASS" if valid and source_stable and deps_stable else "FAIL",
        "finishedAt": now(), "elapsedSeconds": round(time.monotonic() - started, 3),
        "buildExitCode": build_code, "testExitCode": run_code, "harnessError": harness_error,
        "sourceStable": source_stable, "cachedDependenciesStable": deps_stable,
        "executedTestCount": count, "failureCount": failures, "passed": passed,
        "buildLogSHA256": sha(build_log) if build_log.is_file() else None,
        "testLogSHA256": sha(run_log) if run_log.is_file() else None,
        "binarySHA256": sha(work / "validation.exe") if (work / "validation.exe").is_file() else None,
    })
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ("status", "executedTestCount", "failureCount", "sourceStable", "cachedDependenciesStable", "buildExitCode", "testExitCode", "harnessError")}), flush=True)
    if receipt["status"] != "PASS":
        print(build_log.read_text(encoding="utf-8", errors="replace")[-16000:] if build_log.is_file() else "")
        print(text[-16000:])
    return 0 if receipt["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
