#!/usr/bin/env python3
"""Finite v5 source qualification; no candidate imports or Swift execution."""
from pathlib import Path
import base64
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
P = HERE / "proposal5"
PREVIOUS = HERE / "proposal4"
WRAPPER = "Anytype/Sources/Pinkha/AI/PinkhaHanlinAuthService.swift"


def identity(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "gitBlob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
            "gitMode": "100644"}


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as f:
        f.write((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


def inverse(row, before, after):
    assert identity(before) == row["before"] and identity(after) == row["after"]
    forward, reverse = before, after
    for op in reversed(row["operations"]):
        a, b = base64.b64decode(op["beforeBase64"]), base64.b64decode(op["afterBase64"])
        i, j = op["beforeOffset"], op["afterOffset"]
        assert forward[i:i+len(a)] == a and reverse[j:j+len(b)] == b
        forward = forward[:i] + b + forward[i+len(a):]
        reverse = reverse[:j] + a + reverse[j+len(b):]
    assert forward == after and reverse == before


def section(raw, start, end):
    a, b = start.encode(), end.encode()
    assert raw.count(a) == raw.count(b) == 1
    i = raw.index(a)
    return raw[i:raw.index(b, i)]


def main():
    old_proof = (PREVIOUS / "successor-byte-proof.json").read_bytes()
    assert identity(old_proof)["sha256"] == "bf03999a568f5a6910f6e8ea87040d3cf4d214db565c9735187f2cf45431eee5"
    previous = json.loads((PREVIOUS / "source-inputs.json").read_text())
    source_raw = (P / "source-inputs.json").read_bytes()
    assert identity(source_raw)["sha256"] == "8117deba71707607ca2971e3278ce675a8495ebb74cd9335c2532eb16ac6c875"
    manifest = json.loads(source_raw)
    rows = {row["path"]: row for row in manifest["sourceRows"]}
    assert len(rows) == 16 and manifest["modified"] == 10 and manifest["added"] == 6
    unchanged = []
    for row in previous["sourceRows"]:
        path = row["path"]
        after = (P / "after" / path).read_bytes()
        assert identity(after) == rows[path]["after"]
        assert base64.b64decode(rows[path]["base64"]) == after
        assert row["before"] == rows[path]["before"]
        if path != WRAPPER:
            assert identity(after) == row["after"]
            unchanged.append({"path": path, "identity": row["after"]})
    assert len(unchanged) == 15
    full = json.loads((P / "full-source-inverses.json").read_text())["rows"]
    assert len(full) == 10
    for row in full:
        inverse(row, (P / "before" / row["path"]).read_bytes(), (P / "after" / row["path"]).read_bytes())
    before, after = (PREVIOUS / "after" / WRAPPER).read_bytes(), (P / "after" / WRAPPER).read_bytes()
    inverse(json.loads((P / "proposal4-to-proposal5-inverse.json").read_text()), before, after)
    donor = (HERE / "source/original-pre-e2-hanlin-auth" / WRAPPER).read_bytes()
    inverse(json.loads((P / "original-wrapper-composition-inverse.json").read_text()), donor, after)
    same_tail = "    private func prepareEngineAccountChange(_ attempt: OriginalAuthAttempt) async throws {"
    assert before[before.index(same_tail.encode()):] == after[after.index(same_tail.encode()):]
    public = section(after, "    private func publishAccount(", same_tail)
    assert public.count(b"let task = Task<Void, Error>") == 1
    assert public.count(b"try await stage(attempt)") == 2
    assert public.count(b"PinkhaHanlinAccountOwner.shared.accountDidOpen(account)") == 1
    assert public.count(b"PinkhaSharingAccountOwner.shared.didOpen(engine: .heart, accountID: account)") == 1
    assert b"try await MainActor.run {\n                    try attempt.validate()\n                    try PinkhaHanlinAccountOwner.shared.accountDidOpen(account)\n                }" in public
    assert public.index(b"try requireCurrent(attempt)") < public.index(b"let task = Task<Void, Error>")
    assert b"guard accountPublication == nil" in public
    assert public.index(b"accountPublication = publication") < public.index(b"try await task.value")
    assert b"defer { if accountPublication === publication { accountPublication = nil } }" in public
    assert not any(token in public for token in [b"bootstrap", b"base.", b"waitForDrain", b"prepareEngineAccountChange", b"Task.detached", b"UUID()"])
    assert after.count(b"try await self.publishAccount(account.id, for: attempt)") == 2
    assert after.count(b"try await self.publishAccount(account, for: attempt)") == 1
    stop = section(after, "    func logout(removeData:", "    func deleteAccount()")
    assert stop.index(b"let pendingPublication = accountPublication") < stop.index(b"stopping = stop") < stop.index(b"previous?.retire()") < stop.index(b"let cleanup = Task")
    assert b"guard pendingPublication.attempt === previous" in stop
    sequence = [b"_ = await pendingPublication?.task.result", b"try await prepareEngineAccountChange(stop)", b"await PinkhaSharingAccountOwner.shared.closeAndDrain(engine: .heart)", b"try await PinkhaHanlinAccountOwner.shared.closeAccount(originalAccount, removeData: removeData)", b"try await base.logout(removeData: removeData)", b"await previous?.waitForDrain()", b"await bootstrap.quiesceAccountOperations()"]
    indexes = [stop.index(token) for token in sequence]
    assert indexes == sorted(indexes)
    assert b"await previous?.waitForDrain()" not in stop[stop.index(b"            } catch {"):]
    assert b"resumeMiniAppsIfIdle()" not in stop[stop.index(b"            } catch {"):]
    assert b"Task.detached" not in after and b"UUID()" not in after
    assert before.count(b"#if PINKHA_NATIVE_DERIVED && targetEnvironment(simulator)") == after.count(b"#if PINKHA_NATIVE_DERIVED && targetEnvironment(simulator)") == 1
    assert before.count(b"try PinkhaTypePreservationLaunchProof.captureBeforeAccountSelect(accountID: id)") == after.count(b"try PinkhaTypePreservationLaunchProof.captureBeforeAccountSelect(accountID: id)") == 1

    root = P / "ordinary-source-diagnostics/partial-git"
    root.mkdir(parents=True)
    log = []
    def git(argv):
        result = subprocess.run(["git", "--no-optional-locks", *argv], cwd=root, capture_output=True, timeout=30)
        log.append({"argv": ["git", "--no-optional-locks", *argv], "exit": result.returncode,
                    "stdout": result.stdout.decode(), "stderr": result.stderr.decode()})
        return result
    assert git(["init", "--quiet"]).returncode == 0
    for path, row in rows.items():
        if row["before"]:
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.open("xb").write((P / "before" / path).read_bytes())
    assert git(["add", "--", *[p for p, r in rows.items() if r["before"]]]).returncode == 0
    assert git(["-c", "user.name=Source Retention Review", "-c", "user.email=source-review@localhost", "commit", "--quiet", "-m", "Exact partial root275 source preimages"]).returncode == 0
    for path in rows:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((P / "after" / path).read_bytes())
    assert git(["add", "--", *rows]).returncode == 0
    check = git(["diff", "--cached", "--check"])
    dump(P / "ordinary-source-diagnostics/result.json", {"scope": "Ordinary local full16-source partial-Git whitespace check; no Swift/test/runtime", "commands": log, "check": log[-1]})
    assert check.returncode == 0
    assert (P / "source-inputs.json").read_bytes() == source_raw
    for path, row in rows.items():
        assert identity((P / "after" / path).read_bytes()) == row["after"]
    dump(P / "publication-join-byte-proof.json", {
        "state": "PASS_SOURCE_INVERSE_AND_BOUNDED_DECLARATION_PRESERVATION_NOT_RUNTIME",
        "sourceInputs": identity(source_raw), "priorStaticProof": identity(old_proof),
        "unchangedPriorSources": unchanged, "wholeRootInverses": 10,
        "wholePreviousWrapperInverse": True, "wholeOriginalDonorWrapperInverse": True,
        "v4PreparationTokenStagePerformAndRequireTailExact": True,
        "originalSameMainActorAttemptValidationRestored": True,
        "publicationOnlyActualTaskRegisteredBeforeOuterAwait": True,
        "publicationClearedByExactRecordIdentity": True,
        "stopJoinsOnlyPublicationBeforeFirstOwnerClose": True,
        "realStopStillPrecedesRetiredStartupAndBootstrapDrains": True,
        "nativeAndBootstrapWorkExcludedFromPublicationTask": True,
        "sourceDiffCheck": identity((P / "ordinary-source-diagnostics/result.json").read_bytes()),
        "compilerExecuted": False, "testsExecuted": 0, "hostActions": 0, "sourcePublished": False})
    print(json.dumps({"state": "PASS_SOURCE_ONLY", "paths": 16, "diffCheckExit": check.returncode,
                      "proof": identity((P / "publication-join-byte-proof.json").read_bytes())}))


if __name__ == "__main__":
    main()
