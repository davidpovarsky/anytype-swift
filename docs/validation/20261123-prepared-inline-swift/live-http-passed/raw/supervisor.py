from pathlib import Path
import datetime, hashlib, json, os, re, subprocess, sys, time
root = Path("/mnt/development/projects/worktrees/anytype-wave15-inline-http-20261123")
handshake = Path(sys.argv[1])
result_file = Path(sys.argv[2])
out = root / "build/inline-swift/live-http-attempt2"
out.mkdir(parents=True, exist_ok=False)
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def sources():
    return {str(p.relative_to(root)): digest(p) for p in sorted((root / "Modules").rglob("*"))
            if p.is_file() and (p.suffix == ".swift" or p.name == "Package.resolved") and ".build" not in p.parts}
def save(name, value):
    (out / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
registration_dir = root / "build/inline-swift/live-fixture-repair"
registration = json.loads((registration_dir / "receipt.json").read_bytes())
receipt = {"status": "NOT_RUN", "startedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "sourceCommit": subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
           "registrationReceiptSHA256": digest(registration_dir / "receipt.json")}
primary = None
bound = None
before = None
try:
    assert handshake.is_absolute() and result_file.is_absolute()
    assert handshake.is_file() and not handshake.is_symlink() and handshake.stat().st_size <= 8192
    assert not result_file.exists() and handshake.parent == result_file.parent
    assert 0 <= time.time() - handshake.stat().st_mtime <= 120, "Native handshake is not fresh"
    bound = json.loads(handshake.read_bytes())
    assert bound["protocol"] == "pinkha-native-inline-file-http-v1" and re.fullmatch("[0-9a-f]{32}", bound["nonce"])
    assert registration["status"] == "PASS_REPAIRED_LIVE_FIXTURE_COMPILE_AND_REGISTRATION"
    before = sources()
    assert before == json.loads((registration_dir / "sources-after.json").read_bytes())
    for product in registration["binaries"]:
        assert digest(Path(product["path"])) == product["sha256"], "Compiled test product changed"
    save("sources-before.json", before)
    receipt.update(handshakeSHA256=digest(handshake), nonce=bound["nonce"], binariesBefore=registration["binaries"])
    environment = dict(os.environ, PINKHA_INLINE_FILE_HANDSHAKE=str(handshake), PINKHA_INLINE_FILE_RESULT=str(result_file))
    cmd = ["swift", "test", "--package-path", str(root / "Modules/PinkhaAnyHost"),
           "--scratch-path", "/mnt/development/build-cache/anytype-inline-swift-20261123",
           "--cache-path", "/mnt/development/build-cache/swift-package-cache",
           "--disable-automatic-resolution", "-j", "1", "-Xswiftc", "-DPINKHA_PREPARED_INLINE_HTTP_ACCEPTANCE",
           "--skip-build", "--filter", "NativePreparedInlineFileHTTPTests"]
    receipt["command"] = cmd
    save("receipt.json", receipt)
    started = time.monotonic()
    log = out / "swift-test.log"
    with log.open("wb") as stream:
        completed = subprocess.run(cmd, cwd=root, env=environment, stdout=stream, stderr=subprocess.STDOUT, timeout=240)
    receipt.update(exitCode=completed.returncode, elapsedSeconds=round(time.monotonic() - started, 3),
                   logSHA256=digest(log))
    raw = log.read_text(errors="replace")
    terminals = re.findall(r"^Test Case '([^']+)' (passed|failed) \(", raw, flags=re.M)
    receipt["actualTerminals"] = terminals
    expected = "NativePreparedInlineFileHTTPTests.testRealNativeInlineFilesRoundTripThroughThePublicSwiftClient"
    assert completed.returncode == 0, "Swift live HTTP XCTest failed"
    assert terminals == [(expected, "passed")], "Exactly one actual passing live HTTP XCTest required"
    assert "Executed 1 test, with 0 failures" in raw, "Actual XCTest count required"
    assert result_file.is_file() and not result_file.is_symlink() and result_file.stat().st_size <= 32768
    response = json.loads(result_file.read_bytes())
    assert response["completed"] is True and response["nonce"] == bound["nonce"] and response["handshakeSHA256"] == digest(handshake)
    assert len(response["observations"]) == 2
    receipt.update(status="PASS_ACTUAL_SWIFT_NATIVE_HTTP_XCTEST_PENDING_INDEPENDENT_NATIVE_RESULT",
                   actualXCTestMethods=1, nativeIndependentStatus="PENDING", resultSHA256=digest(result_file),
                   originalResult=response, fullMigrationAccepted=False, networkVerified=False, apple="NOT_RUN")
except BaseException as error:
    primary = error
    receipt.update(status="FAIL", errorType=type(error).__name__, error=str(error))
    if bound and not result_file.exists():
        failure = {"protocol": bound["protocol"], "nonce": bound["nonce"], "completed": False,
                   "error": "Root live XCTest supervisor failed; original receipt and log retained."}
        temporary = result_file.with_name(result_file.name + ".root.tmp")
        temporary.write_text(json.dumps(failure, sort_keys=True) + "\n")
        temporary.replace(result_file)
finally:
    try:
        if before is not None:
            after = sources()
            save("sources-after.json", after)
            assert before == after, "Sources changed during live XCTest"
            for product in registration["binaries"]:
                assert digest(Path(product["path"])) == product["sha256"], "Compiled test product changed during live XCTest"
            receipt["sourceAndBinaryUnchanged"] = True
    except BaseException as error:
        receipt["sourceVerificationFailure"] = {"errorType": type(error).__name__, "error": str(error)}
        if primary is None:
            primary = error
            receipt["status"] = "FAIL_SOURCE_OR_BINARY_CHANGED"
    receipt["finishedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save("receipt.json", receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k not in ("originalResult","command","binariesBefore")}), flush=True)
if primary:
    raise SystemExit(1)
