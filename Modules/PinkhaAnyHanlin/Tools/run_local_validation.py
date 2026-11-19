#!/usr/bin/env python3
"""Source-bound local Swift component validation; no UI or runtime parity claim."""
import argparse, hashlib, json, os, re, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def manifest(root):
    result = {}
    for name in ("PinkhaAnyHanlin", "PinkhaAnyHost", "PinkhaAnyEngine", "PinkhaAnyIntegration", "PinkhaKit"):
        module = root / "Modules" / name
        paths = [module / "Package.swift", module / "Package.resolved"]
        for folder in ("Sources", "Tests"):
            paths.extend((module / folder).rglob("*.swift"))
        for path in sorted(set(paths)):
            if path.is_file():
                result[path.relative_to(root).as_posix()] = digest(path)
    return result

def now():
    return datetime.now(timezone.utc).isoformat()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--swift", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--only", choices=("PinkhaAnyHanlin", "PinkhaAnyHost"))
    args = parser.parse_args()
    root = args.root.resolve()
    module = root / "Modules/PinkhaAnyHanlin"
    scratch = root / "Modules/PinkhaAnyEngine/.build"
    env = dict(os.environ)
    env["PATH"] = str(args.swift.parent) + os.pathsep + env.get("PATH", "")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    before = manifest(root)
    proof = {"scope": "Windows Swift XCTest components; not native iOS UI or protected-filesystem proof",
             "startedAt": now(), "baseCommit": head, "sourceManifest": before,
             "validationScriptSHA256": digest(Path(__file__)), "packages": []}
    failed = False
    for name in ((args.only,) if args.only else ("PinkhaAnyHanlin", "PinkhaAnyHost")):
        log = module / (name + "-validation.log")
        command = [str(args.swift), "test", "--package-path", str(root / "Modules" / name),
                   "--scratch-path", str(scratch), "--jobs", "2", "--disable-automatic-resolution"]
        with log.open("w", encoding="utf-8") as output:
            process = subprocess.run(command, cwd=root / "Modules" / name, env=env, stdout=output, stderr=subprocess.STDOUT)
        text = log.read_text(encoding="utf-8", errors="replace")
        passed = sorted(set(re.findall(r"Test Case '([^']+)' passed", text)))
        skipped = sorted(set(re.findall(r"Test Case '([^']+)' skipped", text)))
        summary = re.findall(r"Executed (\d+) tests?, with (\d+) failures", text)
        count, failures = tuple(map(int, summary[-1])) if summary else (0, 0)
        expected_suites = ({"AnyHanlinPlainTextTests": 8, "SharedHanlinCoreTests": 6,
                            "SharedHanlinAccountAndProjectionTests": 5}
                           if name == "PinkhaAnyHanlin" else
                           {"NativeCreationTests": 12 if os.name == "nt" else 15,
                            "NativeSessionTests": 4, "NativeSnapshotTests": 18})
        actual_suites = {}
        for method in passed:
            suite = method.rsplit(".", 1)[0]
            actual_suites[suite] = actual_suites.get(suite, 0) + 1
        valid = (process.returncode == 0 and count == sum(expected_suites.values())
                 and len(passed) == count and failures == 0 and not skipped
                 and actual_suites == expected_suites)
        proof["packages"].append({"name": name, "exitCode": process.returncode,
            "xctestCount": count, "failures": failures, "passed": passed,
            "skipped": skipped, "valid": valid, "expectedSuites": expected_suites,
            "actualSuites": actual_suites, "logSHA256": digest(log)})
        print(json.dumps({"package": name, "valid": valid, "xctestCount": count,
                          "failures": failures, "skipped": len(skipped)}), flush=True)
        if not valid:
            failed = True
            print("\n".join(text.splitlines()[-100:]), flush=True)
        if valid and name == "PinkhaAnyHost":
            binary = scratch / "x86_64-unknown-windows-msvc/debug/pinkha-any-host-probe.exe"
            if not binary.is_file():
                failed = True
                proof["hostProbeCopyError"] = "expected compiled probe missing"
            else:
                target = root / "build/any-engine-port/host-probe-v2.exe"
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(binary, target)
                proof["hostProbe"] = {"path": target.relative_to(root).as_posix(),
                                      "sha256": digest(target)}
        if valid and name == "PinkhaAnyHanlin":
            binary = scratch / "x86_64-unknown-windows-msvc/debug/PinkhaAnyHanlinProbe.exe"
            if binary.is_file():
                proof["hanlinProbe"] = {"path": binary.relative_to(root).as_posix(),
                                        "sha256": digest(binary)}
    proof["sourceStable"] = manifest(root) == before
    failed = failed or not proof["sourceStable"]
    proof["finishedAt"] = now()
    proof["status"] = "FAIL" if failed else "PASS"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": proof["status"], "sourceStable": proof["sourceStable"],
                      "receipt": str(args.output)}), flush=True)
    return int(failed)

if __name__ == "__main__":
    sys.exit(main())
