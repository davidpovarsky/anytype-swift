#!/usr/bin/env python3
"""Exact source/inverse/DI preservation checks, not Swift or behavior tests."""
from pathlib import Path
import base64
import hashlib
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
P = HERE / "proposal4"
PREVIOUS = HERE / "proposal3"
WRAPPER = "Anytype/Sources/Pinkha/AI/PinkhaHanlinAuthService.swift"
ACTIVE = "Anytype/Sources/ServiceLayer/ActiveSpaceManager/ActiveSpaceManager.swift"


def identity(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "gitBlob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
            "gitMode": "100644"}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write((json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode())


def check_inverse(row, before, after):
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
    start = start.encode()
    end = end.encode()
    assert raw.count(start) == 1 and raw.count(end) == 1
    a = raw.index(start)
    return raw[a:raw.index(end, a)]


def main():
    manifest = json.loads((P / "source-inputs.json").read_text())
    previous = json.loads((PREVIOUS / "source-inputs.json").read_text())
    rows = {row["path"]: row for row in manifest["sourceRows"]}
    assert len(rows) == manifest["sourcePathCount"] == 16
    assert manifest["modified"] == 10 and manifest["added"] == 6
    assert set(rows) == {row["path"] for row in previous["sourceRows"]} | {WRAPPER}
    for path, row in rows.items():
        after = (P / "after" / path).read_bytes()
        assert identity(after) == row["after"] and base64.b64decode(row["base64"]) == after
        if row["before"]:
            assert identity((P / "before" / path).read_bytes()) == row["before"]
    unchanged_previous = []
    for row in previous["sourceRows"]:
        path = row["path"]
        if path != ACTIVE:
            assert rows[path]["after"] == row["after"]
            unchanged_previous.append({"path": path, "identity": row["after"]})
    assert len(unchanged_previous) == 14
    full = json.loads((P / "full-source-inverses.json").read_text())["rows"]
    assert len(full) == 10
    for row in full:
        check_inverse(row, (P / "before" / row["path"]).read_bytes(), (P / "after" / row["path"]).read_bytes())
    delta = json.loads((P / "proposal3-to-proposal4-inverses.json").read_text())["rows"]
    assert {r["path"] for r in delta} == {ACTIVE, WRAPPER}
    for row in delta:
        old = (P / "before" / WRAPPER) if row["path"] == WRAPPER else PREVIOUS / "after" / ACTIVE
        check_inverse(row, old.read_bytes(), (P / "after" / row["path"]).read_bytes())

    active_before = (PREVIOUS / "after" / ACTIVE).read_bytes()
    active_after = (P / "after" / ACTIVE).read_bytes()
    start = "    func startSubscription() {"
    end = "    func stopSubscription() async {"
    old_loop = section(active_before, start, end)
    new_loop = section(active_after, start, end)
    assert active_before.replace(old_loop, new_loop, 1) == active_after
    assert b"await InvocationDispatchContext.$binding.withValue(nil)" in new_loop
    guard = b"guard stopOperation == nil, InvocationDispatchContext.binding == nil else {"
    assert active_before.count(guard) == active_after.count(guard) == 1
    assert section(active_before, "    func setActiveSpace(spaceId:", start) == section(active_after, "    func setActiveSpace(spaceId:", start)
    assert active_before[active_before.index(end.encode()):] == active_after[active_after.index(end.encode()):]
    assert b"Task.detached" not in new_loop
    for token in [b"workspaceSubscriptionAttempt = attempt", b"subscription: attempt", b"guard workspaceSubscription == nil, stopOperation == nil"]:
        assert token in old_loop and token in new_loop

    old = (P / "before" / WRAPPER).read_bytes()
    new = (P / "after" / WRAPPER).read_bytes()
    donor = (HERE / "source/original-pre-e2-hanlin-auth" / WRAPPER).read_bytes()
    donor_inverse = json.loads((P / "original-wrapper-composition-inverse.json").read_text())
    check_inverse(donor_inverse, donor, new)
    assert old[:old.index(b"///")] == new[:new.index(b"///")]
    for a, b in [("    private func stage<Value:", "    private func perform<Value:"),
                 ("    private func requireCurrent(", "\n}\n")]:
        assert section(donor, a, b) == section(new, a, b)
    original_perform = section(donor, "    private func perform<Value:", "    private func requireCurrent(")
    current_perform = section(new, "    private func perform<Value:", "    private func requireCurrent(")
    assert current_perform.count(b"                resumeMiniAppsIfIdle()\n") == 2
    assert current_perform.replace(b"                resumeMiniAppsIfIdle()\n", b"") == original_perform
    assert sorted(re.findall(rb"base\.([A-Za-z]+)\(", old)) == sorted(re.findall(rb"base\.([A-Za-z]+)\(", new))
    assert new.count(b"OriginalAuthRequestContext.$parent.withValue(attempt)") == 7
    assert new.count(b"OriginalAuthRequestContext.$parent.withValue(stop)") == 1
    assert new.count(b"prepareEngineAccountChange(attempt)") == 7
    assert new.count(b"prepareEngineAccountChange(stop)") == 1
    assert b"OriginalEditorAuthCaller" not in new and b"PinkhaOriginalEditorRuntimeEnvironment" not in new
    assert b"UUID()" not in new and b"Task.detached" not in new
    assert new.count(b"removeData: removeData") == old.count(b"removeData: removeData") == 2
    proof_call = b"try PinkhaTypePreservationLaunchProof.captureBeforeAccountSelect(accountID: id)"
    assert old.count(proof_call) == new.count(proof_call) == 1
    assert old.count(b"#if PINKHA_NATIVE_DERIVED && targetEnvironment(simulator)") == new.count(b"#if PINKHA_NATIVE_DERIVED && targetEnvironment(simulator)") == 1
    assert old.count(b"#if PINKHA_DUAL_ENGINE_RUNTIME") == new.count(b"#if PINKHA_DUAL_ENGINE_RUNTIME") == 1
    stop = section(new, "    func logout(removeData:", "    func deleteAccount()")
    assert stop.index(b"previous?.retire()") < stop.index(b"let cleanup = Task")
    assert stop.index(b"base.logout(removeData: removeData)") < stop.index(b"await previous?.waitForDrain()") < stop.index(b"await bootstrap.quiesceAccountOperations()")
    catch = stop[stop.index(b"            } catch {"):]
    assert b"await previous?.waitForDrain()" not in catch
    assert b"successfulStopRequired = true" in catch and b"resumeMiniAppsIfIdle()" not in catch
    assert stop.index(b"await PinkhaSharingAccountOwner.shared.closeAndDrain") < stop.index(b"base.logout(")
    assert stop.count(b"PinkhaSharingAccountOwner.shared.closeAndDrain(engine: .heart)") == 2
    assert b"finalAccount.utf8.elementsEqual(originalAccount.utf8)" in stop
    resume = section(new, "    private func resumeMiniAppsIfIdle()", "    private func stage<Value:")
    assert b"guard current == nil, stopping == nil, !successfulStopRequired," in resume
    assert b"for token in tokens { PinkhaMiniAppsCoordinator.shared.resumeAfterAccountChange(token) }" in resume
    prepare = section(new, "    private func prepareEngineAccountChange(", "    private func requirePreparationOwner(")
    assert prepare.index(b"miniAppsChangeTokens.insert(token)") < prepare.index(b"try requirePreparationOwner(attempt)", prepare.index(b"let token"))

    # Exactly authenticated current counterpart contracts, read-only witnesses.
    dependencies = [
        (HERE / "source/root275-hanlin-owner/Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinCore/PinkhaHanlinAccountOwner.swift", "bde96d286c6db0e2c9cde9582156984eea6fcfe2"),
        (HERE / "source/root275-sharing-owner/Modules/PinkhaSharing/Sources/PinkhaSharing/PinkhaSharingAccountOwner.swift", "4791c74b77bfb365c1f1f48a54203a2e80c47a41"),
        (HERE.parent / "miniapps-independent-handler-current-review/consumer-ba7d/PinkhaMiniAppsCoordinator.swift", "21f34173f16d957f4584f76970fd95af3bef7f9a"),
        (HERE.parent / "hanlin-future-build-680/original/Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinCore/PinkhaMiniAppsLifetime.swift", "3999b9edb63eef26264cc643f41686b8c76540c9"),
        (HERE.parent / "native23-current-source-closure/current275/Anytype/Sources/Pinkha/Bootstrap/PinkhaEngineSceneView.swift", "6636723aebf70fde2adce7d3b844b148ed338c92"),
        (HERE / "source/root275-login-view/Anytype/Sources/PresentationLayer/Auth/Login/LoginView/LoginViewModel.swift", "98658a311e242e82b18a980b8c470f8dd8a96433"),
        (HERE / "source/root275-primary-auth-view/Anytype/Sources/PresentationLayer/Auth/PrimaryAuthView/PrimaryAuthViewModel.swift", "58f4b0d1e4939686282b13f796753032bbe55b4c"),
    ]
    witnessed = []
    for path, blob in dependencies:
        raw = path.read_bytes()
        assert identity(raw)["gitBlob"] == blob
        witnessed.append({"path": str(path), "identity": identity(raw)})
    mini = dependencies[3][0].read_bytes()
    assert b"private var holds = Set<UUID>()" in mini
    assert b"holds.insert(token)" in mini and b"holds.remove(token)" in mini
    assert b"public var acceptsOperations: Bool { holds.isEmpty }" in mini
    assert b"try? await authService.logout(removeData: false)" in dependencies[5][0].read_bytes()
    di = (HERE / "blob-source/dfc2b87f5e688b6fb5b89e24d58799f65751ea67").read_bytes()
    assert b"self { PinkhaHanlinAuthService(base: AuthService()) }.shared" in di

    frozen = HERE.parent / "wave3-w2-sdk61-intake/payload-builder-sealed3/payload.json"
    frozen_raw = frozen.read_bytes()
    sealed = json.loads(frozen_raw)
    assert not set(rows).intersection(set(sealed["rootRows"]) | set(sealed["donorRows"]))
    source_map = json.loads(base64.b64decode(sealed["guardInputs"]["sourceMapAfterBase64"]))
    assert len(source_map["changes"]) == 133
    assert source_map["changes"][15]["from"] == WRAPPER
    assert source_map["changes"][15]["replacementBlob"] == identity(old)["gitBlob"]

    # One ordinary full source whitespace diagnostic in an owned partial tree.
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
    assert git(["add", "--", *[path for path, row in rows.items() if row["before"]]]).returncode == 0
    assert git(["-c", "user.name=Source Retention Review", "-c", "user.email=source-review@localhost", "commit", "--quiet", "-m", "Exact partial root275 source preimages"]).returncode == 0
    for path in rows:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((P / "after" / path).read_bytes())
    assert git(["add", "--", *rows]).returncode == 0
    check = git(["diff", "--cached", "--check"])
    write(P / "ordinary-source-diagnostics/result.json", {"scope": "Ordinary local partial-Git source diagnostic only; no Swift compiler or behavior test.", "commands": log, "check": log[-1]})
    assert check.returncode == 0
    for path, row in rows.items():
        assert identity((P / "after" / path).read_bytes()) == row["after"]
    assert frozen.read_bytes() == frozen_raw
    write(P / "successor-byte-proof.json", {
        "status": "PASS_EXACT_SOURCE_INVERSES_AND_ORIGINAL_DECLARATION_PRESERVATION_NOT_SWIFT_OR_RUNTIME",
        "sourceInputs": identity((P / "source-inputs.json").read_bytes()),
        "allTenRootInverses": True, "bothProposal3SuccessorInverses": True, "originalWrapperFullInverse": True,
        "unchangedProposal3Files": unchanged_previous,
        "originalWholeDeclarationsExact": ["stage<Value>", "requireCurrent"],
        "performInverse": "Removing only its two resumeMiniAppsIfIdle() lines restores the complete original donor perform declaration.",
        "activePublicSelectionAndStopTailExact": True,
        "originalNativeAPICallSetExact": True, "allEightMutatingEntriesRetainOriginalMiniAppsAndEnginePreflight": True,
        "originalT5ProofPreserved": True, "dependencies": witnessed,
        "root288": {"identity": identity(frozen_raw), "sourceCollisions": [], "unchanged": True},
        "existingMapRow15": source_map["changes"][15],
        "ordinarySourceDiffCheck": identity((P / "ordinary-source-diagnostics/result.json").read_bytes()),
        "compilerExecuted": False, "testsExecuted": 0, "nativeCalls": 0, "hostActions": 0, "sourcePublished": False})
    print(json.dumps({"state": "PASS_SOURCE_ONLY", "sourcePaths": 16, "fullRootInverses": 10,
                      "originalDeclarationsExact": 2, "unchangedPriorSources": 14,
                      "checkExit": check.returncode, "proof": identity((P / "successor-byte-proof.json").read_bytes())}))


if __name__ == "__main__":
    main()
