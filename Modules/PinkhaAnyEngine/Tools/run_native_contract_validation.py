#!/usr/bin/env python3
"""Exact-suite Engine validation plus actual URLSession SSE boundary fixtures."""
import argparse, collections, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def stamp(): return datetime.now(timezone.utc).isoformat()
def manifest(module):
    values = [module / "Package.swift", module / "Package.resolved"]
    for folder in ("Sources", "Tests"):
        values.extend((module / folder).rglob("*.swift"))
        values.extend((module / folder).rglob("*.py"))
    return {p.relative_to(module).as_posix(): sha(p) for p in sorted(set(values)) if p.is_file()}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--swift", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    module = root / "Modules/PinkhaAnyEngine"
    before = manifest(module)
    env = dict(os.environ)
    env["PATH"] = str(args.swift.parent) + os.pathsep + env.get("PATH", "")
    receipt = {"startedAt": stamp(), "scope": "Swift contracts and actual loopback URLSession fixtures; native engine proof separate",
               "sourceManifest": before, "scriptSHA256": sha(Path(__file__))}
    log = module / "native-contract-tests.log"
    with log.open("w", encoding="utf-8") as output:
        run = subprocess.run([str(args.swift), "test", "--package-path", str(module),
            "--scratch-path", str(module / ".build"), "--jobs", "2", "--disable-automatic-resolution"],
            cwd=module, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=1800)
    text = log.read_text(encoding="utf-8", errors="replace")
    passed = sorted(set(re.findall(r"Test Case '([^']+)' passed", text)))
    skipped = sorted(set(re.findall(r"Test Case '([^']+)' skipped", text)))
    suites = dict(collections.Counter(name.rsplit(".", 1)[0] for name in passed))
    expected = {"AnyTorahOperationTests": 18, "AnyHTTPClientTests": 6,
                "AnyLiveQueryTests": 13, "AnyGuardedTorahTests": 16}
    summary = re.findall(r"Executed (\d+) tests?, with (\d+) failures", text)
    count, failures = tuple(map(int, summary[-1])) if summary else (0, 0)
    valid = run.returncode == 0 and count == 53 and failures == 0 and not skipped and suites == expected
    receipt["xctest"] = {"valid": valid, "exitCode": run.returncode, "count": count,
        "failures": failures, "skipped": skipped, "suites": suites, "expectedSuites": expected,
        "passed": passed, "logSHA256": sha(log)}
    print(json.dumps({"phase": "xctest", "valid": valid, "count": count, "suites": suites}), flush=True)
    if valid:
        source = module / ".build/x86_64-unknown-windows-msvc/debug/PinkhaAnyEngineProbe.exe"
        target = root / "build/any-engine-port/engine-probe-native-v1.exe"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        receipt["probe"] = {"path": target.relative_to(root).as_posix(), "sha256": sha(target)}
        check = subprocess.run([sys.executable, str(module / "Tests/Fixtures/check_sse_transport.py"),
            "--probe", str(target)], cwd=module, env=env, text=True, encoding="utf-8",
            capture_output=True, timeout=120)
        try: outcome = json.loads(check.stdout)
        except ValueError: outcome = {"status": "INVALID_OUTPUT"}
        receipt["sseTransport"] = {"exitCode": check.returncode, "result": outcome,
                                  "stderr": check.stderr[:1000] if check.returncode else ""}
        valid = check.returncode == 0 and outcome.get("status") == "PASS_REAL_HTTP_SSE_BOUNDARIES" and len(outcome.get("checks", [])) == 7
        print(json.dumps({"phase": "sseTransport", "valid": valid}), flush=True)
    else:
        print("\n".join(text.splitlines()[-90:]), flush=True)
    receipt["sourceStable"] = manifest(module) == before
    receipt["finishedAt"] = stamp()
    receipt["status"] = "PASS" if valid and receipt["sourceStable"] else "FAIL"
    output = module / "Evidence/native-contract-components-v1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "sourceStable": receipt["sourceStable"], "receipt": str(output)}), flush=True)
    return 0 if receipt["status"] == "PASS" else 1
if __name__ == "__main__": sys.exit(main())
