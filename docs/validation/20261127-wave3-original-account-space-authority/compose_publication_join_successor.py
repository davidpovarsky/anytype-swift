#!/usr/bin/env python3
"""Narrow local v5: retain original actor-turn publication fence and actual join.

Preserves v4 and both reviews of its queued-publication gap. No Swift execution.
"""
from pathlib import Path
import base64
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
BEFORE = HERE / "proposal4"
OUT = HERE / "proposal5"
WRAPPER = "Anytype/Sources/Pinkha/AI/PinkhaHanlinAuthService.swift"


def identity(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "gitBlob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
            "gitMode": "100644"}


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(raw)


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def operations(before, after):
    a, b = before.splitlines(keepends=True), after.splitlines(keepends=True)
    result = []
    for tag, i, j, x, y in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag != "equal":
            result.append({"beforeOffset": sum(map(len, a[:i])), "afterOffset": sum(map(len, b[:x])),
                           "beforeBase64": base64.b64encode(b"".join(a[i:j])).decode(),
                           "afterBase64": base64.b64encode(b"".join(b[x:y])).decode()})
    forward, reverse = before, after
    for row in reversed(result):
        a, b = base64.b64decode(row["beforeBase64"]), base64.b64decode(row["afterBase64"])
        i, j = row["beforeOffset"], row["afterOffset"]
        assert forward[i:i+len(a)] == a and reverse[j:j+len(b)] == b
        forward = forward[:i] + b + forward[i+len(a):]
        reverse = reverse[:j] + a + reverse[j+len(b):]
    assert forward == after and reverse == before
    return result


def inverse(path, before, after):
    return {"path": path, "before": identity(before), "after": identity(after),
            "operations": operations(before, after), "wholeForwardAndInverseExact": True}


def replace(raw, old, new, count=1):
    old, new = old.encode(), new.encode()
    assert raw.count(old) == count
    return raw.replace(old, new)


def main():
    assert not OUT.exists()
    prior_raw = (BEFORE / "source-inputs.json").read_bytes()
    assert identity(prior_raw)["sha256"] == "60079a4745d9c3b139158ad8331a2fb0cc73be92abd9682a9d484c4eb77e3bc7"
    manifest = json.loads(prior_raw)
    prior = (BEFORE / "after" / WRAPPER).read_bytes()
    assert identity(prior)["sha256"] == "1e15c9bf2e3e87ca2e88979ceecae6f9c1cc8444168514bc17056b9aa134eccc"
    new = replace(prior, "    private var miniAppsChangeTokens = Set<UUID>()\n", '''    private var miniAppsChangeTokens = Set<UUID>()
    private var accountPublication: AccountPublication?

    /// Ownership of the actual existing presentation-open calls, not an account
    /// capability. Stop may join this task without waiting for native startup.
    private final class AccountPublication: Sendable {
        let attempt: OriginalAuthAttempt
        let task: Task<Void, Error>

        init(attempt: OriginalAuthAttempt, task: Task<Void, Error>) {
            self.attempt = attempt
            self.task = task
        }
    }
''')
    new = replace(new, '''            try await self.stage(attempt) {
                try await PinkhaHanlinAccountOwner.shared.accountDidOpen(account.id)
            }
            try await self.stage(attempt) {
                try await PinkhaSharingAccountOwner.shared.didOpen(engine: .heart, accountID: account.id)
            }
''', '''            try await self.publishAccount(account.id, for: attempt)
''', 2)
    new = replace(new, '''            try await self.stage(attempt) {
                try await PinkhaHanlinAccountOwner.shared.accountDidOpen(account)
            }
            try await self.stage(attempt) {
                try await PinkhaSharingAccountOwner.shared.didOpen(engine: .heart, accountID: account)
            }
''', '''            try await self.publishAccount(account, for: attempt)
''')
    new = replace(new, '''        let stop = try OriginalAuthAttempt(kind: .stop)
''', '''        let pendingPublication = accountPublication
        if let pendingPublication {
            guard pendingPublication.attempt === previous else { throw HanlinHostError.staleContext }
        }
        let stop = try OriginalAuthAttempt(kind: .stop)
''')
    new = replace(new, '''        let cleanup = Task { [self] in
            do {
                try await prepareEngineAccountChange(stop)
''', '''        let cleanup = Task { [self] in
            do {
                // A queued owner-open call must finish before the first close.
                // This task contains only Hanlin/Sharing publication, never the
                // native startup or Bootstrap work that real Stop must release.
                _ = await pendingPublication?.task.result
                try await prepareEngineAccountChange(stop)
''')
    insertion = '''    private func publishAccount(_ account: String, for attempt: OriginalAuthAttempt) async throws {
        try requireCurrent(attempt)
        guard accountPublication == nil else { throw HanlinHostError.staleContext }
        let task = Task<Void, Error> { [self] in
            try await stage(attempt) {
                // Retain the original same-turn MainActor check: retirement can
                // happen after a caller queues this hop but before it executes.
                try await MainActor.run {
                    try attempt.validate()
                    try PinkhaHanlinAccountOwner.shared.accountDidOpen(account)
                }
            }
            try await stage(attempt) {
                try await PinkhaSharingAccountOwner.shared.didOpen(engine: .heart, accountID: account)
            }
        }
        let publication = AccountPublication(attempt: attempt, task: task)
        // No suspension precedes registration. A Stop sees this exact task or
        // sets stopping first, after which requireCurrent rejects registration.
        accountPublication = publication
        defer { if accountPublication === publication { accountPublication = nil } }
        try await task.value
        try requireCurrent(attempt)
    }

'''
    new = replace(new, "    private func prepareEngineAccountChange(_ attempt: OriginalAuthAttempt) async throws {\n", insertion + "    private func prepareEngineAccountChange(_ attempt: OriginalAuthAttempt) async throws {\n")
    full = []
    for row in manifest["sourceRows"]:
        path = row["path"]
        old = (BEFORE / "after" / path).read_bytes()
        assert identity(old) == row["after"]
        after = new if path == WRAPPER else old
        if path == WRAPPER:
            row["origins"].append({"newIntegrationSource": True,
                "scope": "Restore the original same-MainActor attempt check. Retain and identity-clear one actual Hanlin/Sharing publication task; Stop retires the original parent and joins only that task before its first owner close. No native-startup/Bootstrap wait is added before real Stop."})
        row["after"] = identity(after)
        row["base64"] = base64.b64encode(after).decode()
        write(OUT / "after" / path, after)
        if row["before"]:
            before = (BEFORE / "before" / path).read_bytes()
            assert identity(before) == row["before"]
            write(OUT / "before" / path, before)
            full.append(inverse(path, before, after))
    manifest["previousProposal4"] = {"path": str(BEFORE / "source-inputs.json"), "identity": identity(prior_raw)}
    manifest["correctedProposal4Finding"] = "Queued actor publication could reopen a metadata owner between Stop's first close and final drain. Same-turn Hanlin validation and an exact actual publication-only task join close that window without changing native/Bootstrap cancellation order. Proposal4 is retained, not accepted for this edge."
    write(OUT / "source-inputs.json", encode(manifest))
    write(OUT / "full-source-inverses.json", encode({"rows": full}))
    write(OUT / "proposal4-to-proposal5-inverse.json", encode(inverse(WRAPPER, prior, new)))
    donor = (HERE / "source/original-pre-e2-hanlin-auth" / WRAPPER).read_bytes()
    write(OUT / "original-wrapper-composition-inverse.json", encode(inverse(WRAPPER, donor, new)))
    write(OUT / "proposal4-finding.json", encode({
        "status": "SOURCE_REVIEW_FINDING_CORRECTED_IN_DISTINCT_PROPOSAL5_NOT_RUNTIME_PROOF",
        "priorWrapper": identity(prior), "newWrapper": identity(new),
        "reviewers": ["owner self-review", "root source review", "sdk_hanlin independent source review"],
        "finding": "A pre/post stage check cannot prevent a queued cross-actor didOpen from running after retirement. A final reclose alone leaves an intermediate reopening window.",
        "correction": "Original Hanlin validation occurs within its MainActor turn. An actually owned publication-only task is registered before suspension; Stop retires parent before awaiting only that task, then closes both owners before actual native Stop. Exact record identity clears the handle.",
        "testsExecuted": 0, "compilerExecuted": False, "hostActions": 0}))
    for name in ["source-inputs.json", "full-source-inverses.json", "proposal4-to-proposal5-inverse.json", "original-wrapper-composition-inverse.json"]:
        print(name, identity((OUT / name).read_bytes()))
    print("wrapper", identity(new))


if __name__ == "__main__":
    main()
