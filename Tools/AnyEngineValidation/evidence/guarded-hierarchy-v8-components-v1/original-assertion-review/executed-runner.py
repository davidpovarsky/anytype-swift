#!/usr/bin/env python3
"""Archive the hierarchy probe delta and prove its original twenty assertions remain."""
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import subprocess


def expressions(source):
    output = []
    offset = 0
    while True:
        start = source.find("try check(", offset)
        if start < 0:
            return output
        index = start + len("try check(")
        depth, quoted, escaped = 1, False, False
        while index < len(source) and depth:
            character = source[index]
            if quoted:
                if escaped:
                    escaped = False
                elif character == chr(92):
                    escaped = True
                elif character == chr(34):
                    quoted = False
            elif character == chr(34):
                quoted = True
            elif character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
            index += 1
        if depth:
            raise RuntimeError("unbalanced_check_expression")
        output.append(source[start:index])
        offset = index


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    relative = "Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegrationProbe/GuardedHierarchyProbe.swift"
    raw = subprocess.check_output(["git", "-C", str(root), "show", args.baseline + ":" + relative], timeout=30)
    current = (root / relative).read_bytes()
    old = raw.decode("utf-8").replace("\r\n", "\n")
    new = current.decode("utf-8").replace("\r\n", "\n")
    before, after = expressions(old), expressions(new)
    if len(before) != 20 or before != after:
        raise RuntimeError("original_twenty_assertion_expressions_changed")
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / "original.swift").write_bytes(raw)
    (out / "current.swift").write_bytes(current)
    diff = "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                     fromfile="original/" + relative, tofile="v8/" + relative))
    (out / "probe.diff").write_text(diff, encoding="utf-8")
    result = {
        "status": "PASS_SOURCE_REVIEW_ONLY", "baselineCommit": args.baseline, "path": relative,
        "originalSHA256": hashlib.sha256(raw).hexdigest(),
        "currentSHA256": hashlib.sha256(current).hexdigest(),
        "diffSHA256": hashlib.sha256((out / "probe.diff").read_bytes()).hexdigest(),
        "assertionCount": 20, "allOriginalAssertionExpressionsUnchanged": True,
        "assertionSHA256": [hashlib.sha256(value.encode("utf-8")).hexdigest() for value in before],
        "executedRuntimeChecks": 0, "runnerSHA256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (out / "executed-runner.py").write_bytes(Path(__file__).read_bytes())
    print(json.dumps(result))
    print(diff.encode("ascii", errors="backslashreplace").decode("ascii"))


if __name__ == "__main__":
    main()
