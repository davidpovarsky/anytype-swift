#!/usr/bin/env python3
"""Qualify one fixed related-read Swift Testing profile from original events."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import platform
import re
import signal
import subprocess
import sys
from pathlib import Path

KIT = "511454e49450cb2581ddf77f644146ff3e30dbef"
CONTRACT = "docs/architecture/related-read-authority-20261121/test-profiles.json"
PROFILES = {
    "kit-related-current-access": (15, 17),
    "any-related-authority-mapping": (3, 4),
    "shared-related-session-lifetime": (1, 1),
}


def require(value, message):
    if not value:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def exact_source(root, expected):
    require(re.fullmatch("[0-9a-f]{40}", expected or ""), "one immutable source commit required")
    require(git(root, "rev-parse", "HEAD") == expected, "source checkout differs")
    require(not git(root, "diff", "--name-only", "HEAD"), "tracked source or lock changed")


def validate_host(system, architecture, xcode):
    require(system == "Darwin" and architecture == "arm64", "actual Apple ARM64 host required")
    require(re.fullmatch(r"Xcode 27(?:\.\d+)*\nBuild version [A-Za-z0-9]+", xcode),
            "actual Xcode27 compiler host required")


@dataclass(frozen=True)
class Method:
    target: str
    suite: str
    name: str
    arguments: tuple[tuple[str, tuple[str, ...]], ...] = ()

    @property
    def key(self):
        return self.target + "." + self.suite + "/" + self.name

    @property
    def file_id(self):
        return self.target + "/" + self.suite + ".swift"

    @property
    def argument_cases(self):
        require(len(self.arguments) <= 1, "this fixed profile supports one named argument only")
        return list(self.arguments[0][1]) if self.arguments else [None]


def spelling(value):
    if type(value) is bool:
        return str(value).lower()
    require(type(value) is str and value in {"denied", "invalidated"}, "unreviewed argument value")
    return value


def load_profile(root, profile_id, kit_root=None):
    require(profile_id in PROFILES, "unreviewed component profile")
    contract = read_json(root / CONTRACT)
    require(contract.get("schemaVersion") == 1 and contract.get("requiredKitCommit") == KIT,
            "reviewed common profile or Kit pin changed")
    rows = [p for p in contract["profiles"] if p["id"] == profile_id]
    require(len(rows) == 1, "one fixed profile required")
    profile = rows[0]
    require((profile["expectedMethods"], profile["expectedArgumentCases"]) == PROFILES[profile_id],
            "fixed method/argument counts changed")
    if profile_id == "kit-related-current-access":
        require(kit_root is not None, "exact separate Kit checkout required")
        selection = read_json(kit_root / profile["selectionSource"])
        require((selection["expectedMethods"], selection["expectedActualCases"]) == (15, 17),
                "Kit selection counts differ")
        suites = selection["suites"]
        package = kit_root
    else:
        package = root / profile["packagePath"]
        require(len(profile["suiteTypes"]) == 1, "one declared suite required")
        suites = [{"target": package.name + "Tests", "suite": profile["suiteTypes"][0],
                   "methods": profile["methods"]}]
    require({s["suite"] for s in suites} == set(profile["suiteTypes"]), "suite selection differs")
    methods = []
    for suite in suites:
        for row in suite["methods"]:
            args = tuple((label, tuple(spelling(value) for value in values))
                         for label, values in row.get("argumentValues", {}).items())
            methods.append(Method(suite["target"], suite["suite"], row["name"], args))
    require(len({m.key for m in methods}) == len(methods) == PROFILES[profile_id][0],
            "duplicate or missing selected method")
    require(sum(len(m.argument_cases) for m in methods) == PROFILES[profile_id][1],
            "argument-case selection changed")
    return package, methods


def inspect_sources(package, methods):
    result = {}
    for target, suite in sorted({(m.target, m.suite) for m in methods}):
        matches = list((package / "Tests" / target).rglob(suite + ".swift"))
        require(len(matches) == 1, "one actual selected test source required")
        path = matches[0]
        content = path.read_text(encoding="utf-8")
        declarations = re.findall(r"@Test\b((?:(?!\bfunc\b).)*?)\bfunc\s+(\w+)\s*\(([^)]*)\)",
                                  content, re.DOTALL)
        expected = {m.name: m for m in methods if (m.target, m.suite) == (target, suite)}
        require(len(declarations) == len(expected) and {name for _, name, _ in declarations} == set(expected),
                "selected source declarations changed")
        for attributes, name, parameters in declarations:
            method = expected[name]
            values = re.search(r"arguments\s*:\s*\[([^]]+)\]", attributes)
            if method.arguments:
                label, arguments = method.arguments[0]
                require(values is not None and re.search(r"\b" + re.escape(label) + r"\s*:", parameters),
                        "named parameter declaration differs")
                declared = [value.strip().split(".")[-1] for value in values[1].split(",") if value.strip()]
                require(declared == list(arguments), "literal argument declaration differs")
            else:
                require(values is None, "unexpected parameterization")
        result[str(path.relative_to(package))] = digest(path)
    return result


def argument_value(event, method):
    require(len(method.arguments) == 1, "nonparameterized method emitted argument events")
    label, values = method.arguments[0]
    text = "\n".join(message.get("text", "") for message in event.get("messages", []))
    # Swift Testing's version-0 event message includes the actual label/value.
    # The optional qualified type is presentation only; the value must match.
    pattern = r"\b" + re.escape(label) + r"\s*→\s*(?:[A-Za-z_]\w*\.)*\.?([A-Za-z_]\w*)\b"
    found = re.findall(pattern, text)
    require(len(found) == 1 and found[0] in values, "missing, duplicate or unexpected actual argument")
    return found[0]


def passed(event):
    symbols = [message.get("symbol") for message in event.get("messages", [])]
    require("pass" in symbols and not set(symbols) & {"fail", "skip", "passWithKnownIssue", "warning"},
            "original terminal event does not prove a clean pass")


def qualify_stream(path, methods):
    """Require original named start/end pairs, argument pairs and clean run end."""
    expected = {(m.file_id, m.name): m for m in methods}
    require(len(expected) == len(methods), "ambiguous source method identity")
    suites = {m.suite for m in methods}
    descriptors, mapped, states = {}, {}, {}
    suite_starts, suite_ends = Counter(), Counter()
    started = ended = False
    versions = set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        require(line.strip(), "blank or truncated event-stream record")
        record = json.loads(line, object_pairs_hook=unique_object)
        require(type(record.get("version")) is int and record["version"] == 0, "unreviewed event schema")
        versions.add(record["version"])
        payload = record.get("payload")
        require(isinstance(payload, dict), "missing original event payload")
        if record.get("kind") == "test":
            identity = payload.get("id")
            require(isinstance(identity, str) and identity and identity not in descriptors, "duplicate test descriptor")
            require(payload.get("kind") in {"suite", "function"}, "unreviewed test descriptor kind")
            descriptors[identity] = payload
            if payload["kind"] == "function":
                source = payload.get("sourceLocation", {}).get("fileID")
                name = payload.get("name", "").split("(", 1)[0]
                method = expected.get((source, name))
                if method:
                    require(payload.get("isParameterized") is bool(method.arguments), "actual parameterization differs")
                    require(method.key not in states, "same method discovered twice")
                    mapped[identity] = method
                    states[method.key] = {"started": False, "ended": False, "starts": [], "ends": []}
            continue
        require(record.get("kind") == "event", "unreviewed original record kind")
        event = payload
        kind = event.get("kind")
        require(kind not in {"issueRecorded", "testSkipped", "testCancelled", "testCaseCancelled"},
                "issue, skip or cancellation cannot qualify")
        require(not event.get("issue"), "hidden issue payload")
        require(not any(m.get("symbol") in {"fail", "skip", "passWithKnownIssue", "warning"}
                        for m in event.get("messages", [])), "nonpassing event")
        if kind == "runStarted":
            require(not started and not ended, "duplicate run start")
            started = True
            continue
        require(started and not ended, "execution outside one live run")
        if kind == "runEnded":
            passed(event)
            ended = True
            continue
        identity = event.get("testID")
        require(identity in descriptors, "event has no discovered identity")
        descriptor = descriptors[identity]
        if descriptor["kind"] == "suite":
            name = descriptor["name"]
            require(name in suites and kind in {"testStarted", "testEnded"}, "unselected suite execution")
            if kind == "testStarted":
                suite_starts[name] += 1
                require(suite_starts[name] == 1 and not suite_ends[name], "duplicate suite start")
            else:
                passed(event)
                suite_ends[name] += 1
                require(suite_starts[name] == suite_ends[name] == 1, "invalid suite terminal")
            continue
        require(identity in mapped, "an unselected method executed")
        method, state = mapped[identity], states[mapped[identity].key]
        require(suite_starts[method.suite] == 1 and not suite_ends[method.suite], "method outside its suite")
        if kind == "testStarted":
            require(not state["started"] and not state["ended"], "duplicate method start")
            state["started"] = True
        elif kind in {"testCaseStarted", "testCaseEnded"}:
            require(state["started"] and not state["ended"], "argument event outside its method")
            value = argument_value(event, method)
            if kind == "testCaseStarted":
                require(value not in state["starts"], "duplicate actual argument")
                state["starts"].append(value)
            else:
                passed(event)
                require(value in state["starts"] and value not in state["ends"], "missing or duplicate argument end")
                state["ends"].append(value)
        elif kind == "testEnded":
            require(state["started"] and not state["ended"], "missing or duplicate method terminal")
            passed(event)
            if method.arguments:
                require(set(state["starts"]) == set(state["ends"]) == set(method.argument_cases),
                        "missing actual named argument cases")
            else:
                require(not state["starts"] and not state["ends"], "unexpected repeated simple test")
            state["ended"] = True
        else:
            raise ValueError("unreviewed method event: " + str(kind))
    require(started and ended and versions == {0}, "incomplete original run")
    require(set(states) == {m.key for m in methods} and all(s["ended"] for s in states.values()),
            "selected method missing from actual execution")
    require(dict(suite_starts) == dict(suite_ends) == {s: 1 for s in suites}, "suite closure missing")
    return [{"method": m.key, "status": "passed", "actualArguments": states[m.key]["ends"],
             "actualCases": len(m.argument_cases)} for m in methods]


def actual_checkout(package, kit_root=None):
    if kit_root is not None and package == kit_root:
        require(git(kit_root, "rev-parse", "HEAD") == KIT, "Kit checkout is not the reviewed exact source")
        return {"path": str(kit_root), "commit": KIT}
    checkout = package / ".build/checkouts"
    matches = [p for p in checkout.iterdir() if p.name.lower() == "torahinspectorkit"]
    require(len(matches) == 1, "one actual Kit dependency checkout required")
    exact_source(matches[0], KIT)
    return {"path": str(matches[0]), "commit": KIT}


def run_command(root, argv, path, seconds):
    """Finish the existing owned-group cleanup before another profile can start."""
    gate = Path(__file__).resolve().parents[1] / "PinkhaSimulatorGate"
    sys.path.insert(0, str(gate))
    import wave15_batch as owned
    from run_owned_single_lane import verify_owned_group_stopped

    command_path = path.with_suffix(".command.json")
    boundary_path = path.with_suffix(".ownership.json")
    require(not path.exists() and not command_path.exists() and not boundary_path.exists(),
            "refuse stale command or ownership evidence")
    record = {"status": "FAIL", "command": argv, "testAcceptanceInferred": False}
    previous = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT)}
    cancelled = finalizing = False
    failure = outcome = None

    def cancel(signum, frame):
        nonlocal cancelled
        if cancelled:
            return
        cancelled = True
        if not finalizing:
            raise KeyboardInterrupt("Owned package command cancelled")

    for number in previous:
        signal.signal(number, cancel)
    try:
        outcome = owned.run_worker_command(argv, root, path, seconds)
        record.update(status="PROCESS_COMPLETE_TEST_ACCEPTANCE_PENDING" if outcome["return_code"] == 0
                      else "PROCESS_FAILED", returncode=outcome["return_code"])
    except BaseException as error:
        failure = error
        record.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else
                      "TIMED_OUT" if isinstance(error, subprocess.TimeoutExpired) else "FAIL",
                      errorType=type(error).__name__)
    finally:
        finalizing = True
        try:
            record["ownedGroupQuiescence"] = verify_owned_group_stopped(command_path)
        except BaseException as error:
            record.update(status="FAILED_PROCESS_CLEANUP", cleanupErrorType=type(error).__name__)
            failure = failure or error
        try:
            if command_path.exists():
                record["originalCommandSHA256"] = digest(command_path)
            if path.exists():
                record["logSHA256"] = digest(path)
            if cancelled:
                record["status"] = "CANCELLED"
                failure = failure or KeyboardInterrupt("Owned package command cancelled")
            boundary_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            # A first cancellation during receipt writing must not return success.
            if cancelled:
                record["status"] = "CANCELLED"
                failure = failure or KeyboardInterrupt("Owned package command cancelled")
                boundary_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        finally:
            for number, handler in previous.items():
                signal.signal(number, handler)
    if failure is not None:
        raise failure
    require(outcome is not None, "missing original worker outcome")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--kit-root", type=Path)
    parser.add_argument("--profile", choices=PROFILES, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    kit = args.kit_root.resolve() if args.kit_root else None
    output = root / "build/related-read-authority" / args.profile
    output.mkdir(parents=True, exist_ok=False)
    receipt = {"schemaVersion": 1, "status": "FAIL", "profile": args.profile,
               "appSourceCommit": args.source_sha, "kitCommit": KIT,
               "appBuilds": 0, "simulatorRuns": 0, "nativeACLProof": False,
               "otherProfilesAcceptedByThisReceipt": False, "buildReuseClaim": "NOT_INFERRED_FROM_SHARED_JOB"}
    package = lock = None
    try:
        require(platform.system() == "Darwin" and platform.machine() == "arm64", "actual Apple ARM64 host required")
        exact_source(root, args.source_sha)
        if kit:
            exact_source(kit, KIT)
        package, methods = load_profile(root, args.profile, kit)
        receipt["contractSHA256"] = digest(root / CONTRACT)
        receipt["sourceSHA256"] = inspect_sources(package, methods)
        receipt["swiftVersion"] = subprocess.check_output(["swift", "--version"], text=True).strip()
        receipt["xcodeVersion"] = subprocess.check_output(["xcodebuild", "-version"], text=True).strip()
        receipt["platform"] = {"system": platform.system(), "architecture": platform.machine()}
        validate_host(receipt["platform"]["system"], receipt["platform"]["architecture"], receipt["xcodeVersion"])
        lock = package / "Package.resolved"
        before = lock.read_bytes() if lock.is_file() else None
        if before is not None:
            (output / "Package.resolved.before").write_bytes(before)
        receipt["resolution"] = run_command(root, ["swift", "package", "--package-path", str(package), "resolve"],
                                             output / "resolve.log", 300)
        require(receipt["resolution"]["returncode"] == 0, "resolve-only preflight failed")
        after = lock.read_bytes() if lock.is_file() else None
        require(after == before, "resolution rewrote a reviewed package lock")
        if after is not None:
            pins = read_json(lock)["pins"]
            selected = [p for p in pins if p["identity"] == "torahinspectorkit"]
            if package != kit:
                require(len(selected) == 1 and selected[0]["state"] == {"revision": KIT}, "lock contains wrong Kit pin")
            receipt["packageLockSHA256"] = digest(lock)
        exact_source(root, args.source_sha)
        receipt["actualKitCheckout"] = actual_checkout(package, kit)
        selected = "|".join(re.escape(target + "." + suite) for target, suite in sorted({(m.target,m.suite) for m in methods}))
        # Both libraries may be compiled; execution is Swift Testing only.
        argv = ["swift", "test", "--verbose", "--package-path", str(package), "--jobs", "2",
                "--force-resolved-versions", "--disable-xctest", "--enable-swift-testing", "--no-parallel",
                "--filter", selected, "--event-stream-output-path", str(output / "original-events.jsonl"),
                "--event-stream-version", "0"]
        receipt["execution"] = run_command(root, argv, output / "original-test.log", 1500)
        require(receipt["execution"]["returncode"] == 0, "selected package build or tests failed")
        receipt["methods"] = qualify_stream(output / "original-events.jsonl", methods)
        receipt["eventsSHA256"] = digest(output / "original-events.jsonl")
        require(inspect_sources(package, methods) == receipt["sourceSHA256"], "selected source changed during execution")
        exact_source(root, args.source_sha)
        if kit:
            exact_source(kit, KIT)
        require((lock.read_bytes() if lock.is_file() else None) == before, "test build rewrote dependency lock")
        require(actual_checkout(package, kit) == receipt["actualKitCheckout"], "actual Kit checkout changed")
        receipt.update(status="PASS_EXACT_RELATED_READ_COMPONENT", actualMethods=len(methods),
                       actualArgumentCases=sum(len(m.argument_cases) for m in methods))
        print(json.dumps({k: receipt[k] for k in ("status", "profile", "actualMethods", "actualArgumentCases")}), flush=True)
    except BaseException as error:
        receipt["error"] = type(error).__name__ + ": " + str(error)
        raise
    finally:
        if lock and lock.is_file():
            (output / "Package.resolved.after").write_bytes(lock.read_bytes())
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
