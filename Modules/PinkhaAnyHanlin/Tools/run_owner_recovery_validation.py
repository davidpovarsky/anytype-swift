#!/usr/bin/env python3
"""Focused mounted-owner / recovery-metadata / creation-capability regressions."""
import argparse, collections, hashlib, json, os, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def manifest(root):
    result = {}
    for name in ("PinkhaAnyHanlin", "PinkhaAnyHost", "PinkhaAnyEngine", "PinkhaAnyIntegration", "PinkhaKit"):
        package = root / "Modules" / name
        paths = [package / "Package.swift", package / "Package.resolved"]
        paths += list((package / "Sources").rglob("*.swift"))
        if name == "PinkhaAnyHanlin":
            paths += list((package / "Tests").rglob("*.swift"))
            paths += list((package / "Sources").rglob("*.xcstrings"))
        for path in sorted(set(paths)):
            if path.is_file(): result[path.relative_to(root).as_posix()] = sha(path)
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--swift", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve(); package = root / "Modules/PinkhaAnyHanlin"
    before = manifest(root)
    receipt = {"startedAt": now(), "scope": "portable Swift focused regressions; UIKit and protected iOS journal tests separate",
               "sourceManifest": before, "scriptSHA256": sha(Path(__file__))}
    env = dict(os.environ); env["PATH"] = str(args.swift.parent) + os.pathsep + env.get("PATH", "")
    command = [str(args.swift), "test", "--package-path", str(package),
               "--scratch-path", str(root / "Modules/PinkhaAnyEngine/.build"), "--jobs", "2",
               "--filter", "NativeMountedOwnerTests|KnownCreationRecoveryTests|NativeCreationCapabilityTests",
               "--disable-automatic-resolution"]
    log = package / "owner-recovery-tests.log"
    with log.open("w", encoding="utf-8") as out:
        run = subprocess.run(command, cwd=package, env=env, stdout=out, stderr=subprocess.STDOUT, timeout=1800)
    text = log.read_text(encoding="utf-8", errors="replace")
    passed = sorted(set(re.findall(r"Test Case '([^']+)' passed", text)))
    skipped = sorted(set(re.findall(r"Test Case '([^']+)' skipped", text)))
    suites = dict(collections.Counter(name.rsplit(".", 1)[0] for name in passed))
    expected = {"NativeMountedOwnerTests": 4, "KnownCreationRecoveryTests": 4, "NativeCreationCapabilityTests": 1}
    summary = re.findall(r"Executed (\d+) tests?, with (\d+) failures", text)
    count, failures = tuple(map(int, summary[-1])) if summary else (0, 0)
    valid = run.returncode == 0 and count == 9 and failures == 0 and not skipped and suites == expected
    receipt.update({"exitCode": run.returncode, "count": count, "failures": failures, "skipped": skipped,
        "passed": passed, "suites": suites, "expectedSuites": expected, "logSHA256": sha(log),
        "sourceStable": manifest(root) == before, "finishedAt": now()})
    receipt["status"] = "PASS" if valid and receipt["sourceStable"] else "FAIL"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: receipt[key] for key in ("status", "count", "failures", "sourceStable", "suites")}), flush=True)
    if not valid: print("\n".join(text.splitlines()[-100:]), flush=True)
    return 0 if receipt["status"] == "PASS" else 1
if __name__ == "__main__": sys.exit(main())
