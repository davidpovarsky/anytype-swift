#!/usr/bin/env python3
"""Local original-authority successor. No compiler, runtime, host or publication.

Preserve proposal3 exactly; add the original outer Auth attempt composition and
clear the inherited temporary dispatch binding only inside the owned subscription.
"""
from pathlib import Path
import base64
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
BEFORE = HERE / "proposal3"
OUT = HERE / "proposal4"
ACTIVE = "Anytype/Sources/ServiceLayer/ActiveSpaceManager/ActiveSpaceManager.swift"
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
    rows = []
    for tag, i, j, x, y in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag != "equal":
            rows.append({"beforeOffset": sum(map(len, a[:i])), "afterOffset": sum(map(len, b[:x])),
                         "beforeBase64": base64.b64encode(b"".join(a[i:j])).decode(),
                         "afterBase64": base64.b64encode(b"".join(b[x:y])).decode()})
    forward, reverse = before, after
    for row in reversed(rows):
        old, new = base64.b64decode(row["beforeBase64"]), base64.b64decode(row["afterBase64"])
        i, j = row["beforeOffset"], row["afterOffset"]
        assert forward[i:i+len(old)] == old and reverse[j:j+len(new)] == new
        forward = forward[:i] + new + forward[i+len(old):]
        reverse = reverse[:j] + old + reverse[j+len(new):]
    assert forward == after and reverse == before
    return rows


def inverse(path, before, after):
    return {"path": path, "before": identity(before), "after": identity(after),
            "operations": operations(before, after), "wholeForwardAndInverseExact": True}


def main():
    assert not OUT.exists()
    manifest_path = BEFORE / "source-inputs.json"
    prior_raw = manifest_path.read_bytes()
    assert identity(prior_raw)["sha256"] == "6ac0f8dc8c812657e01b90eebce7e1a9bd45cc4951b0c03937ab6a85172f7156"
    prior = json.loads(prior_raw)
    assert prior["sourcePathCount"] == 15 and prior["modified"] == 9 and prior["added"] == 6
    rows, full, delta = [], [], []
    old_subscription = b'''        workspaceSubscription = Task { [weak self, workspaceStorage] in
            for await workspaces in workspaceStorage.allSpaceViewsPublisher.values {
                await self?.handleSpaces(workspaces: workspaces, subscription: attempt)
            }
        }
'''
    new_subscription = b'''        workspaceSubscription = Task { [weak self, workspaceStorage] in
            // Login starts this owned subscription inside its temporary startup
            // binding. Later stream events use their own exact subscription and
            // selection identities, not that inherited completed startup binding.
            await InvocationDispatchContext.$binding.withValue(nil) {
                for await workspaces in workspaceStorage.allSpaceViewsPublisher.values {
                    await self?.handleSpaces(workspaces: workspaces, subscription: attempt)
                }
            }
        }
'''
    for row in prior["sourceRows"]:
        path = row["path"]
        raw = (BEFORE / "after" / path).read_bytes()
        assert identity(raw) == row["after"]
        after = raw
        if path == ACTIVE:
            assert raw.count(old_subscription) == 1
            after = raw.replace(old_subscription, new_subscription, 1)
            delta.append(inverse(path, raw, after))
            row["origins"].append({"newIntegrationSource": True,
                "scope": "Owned original subscription task clears only inherited temporary startup Invocation binding; public setActiveSpace guard and all original subscription/selection/account checks remain exact."})
        row["after"] = identity(after)
        row["base64"] = base64.b64encode(after).decode()
        write(OUT / "after" / path, after)
        if row["before"] is not None:
            before = (BEFORE / "before" / path).read_bytes()
            assert identity(before) == row["before"]
            write(OUT / "before" / path, before)
            full.append(inverse(path, before, after))
        rows.append(row)

    original_path = HERE / "source/root275-hanlin-auth" / WRAPPER
    original = original_path.read_bytes()
    assert identity(original)["gitBlob"] == "10bfbd82afdd6986da3d1940915bc6c8995a8cdc"
    donor_path = HERE / "source/original-pre-e2-hanlin-auth" / WRAPPER
    donor = donor_path.read_bytes()
    assert identity(donor)["gitBlob"] == "d413baf9dcdb09f0db61f46eb37b1c795a0ed465"
    wrapper = (HERE / "drafts/auth-stop-v1.swift").read_bytes()
    write(OUT / "before" / WRAPPER, original)
    write(OUT / "after" / WRAPPER, wrapper)
    full.append(inverse(WRAPPER, original, wrapper))
    delta.append(inverse(WRAPPER, original, wrapper))
    rows.append({"path": WRAPPER, "status": "M", "before": identity(original), "after": identity(wrapper),
                 "baseCommit": prior["baseCommit"], "base64": base64.b64encode(wrapper).decode(),
                 "origins": [
                     {"commit": prior["baseCommit"], "path": WRAPPER, "identity": identity(original),
                      "localSource": str(original_path), "scope": "Current protected MiniApps, Sharing, engine, Hanlin, Bootstrap and T5 stages retained."},
                     {"commit": "d1ca51352734bd21a4943e7e094ac3ae95519c1e", "path": WRAPPER,
                      "identity": identity(donor), "localSource": str(donor_path),
                      "scope": "OriginalAuthAttempt, parent, stage, current/stop admission, owned native Stop-before-startup-drain and explicit failed-Stop retry behavior."},
                     {"newIntegrationSource": True,
                      "scope": "Compose original attempts with every protected current stage; retain actual independent MiniApps hold tokens until all wrapper work is idle and Stop succeeded. No new account generation, native writer, fabricated cancellation completion or engine authority."}]})
    rows.sort(key=lambda row: row["path"])
    assert len(rows) == 16 and sum(row["status"] == "M" for row in rows) == 10
    result = dict(prior)
    result.update({"sourceRows": rows, "sourcePathCount": 16, "modified": 10, "added": 6,
                   "state": "SOURCE_ONLY_UNPUBLISHED_REVIEW_REQUIRED_NOT_COMPILED_NOT_RUNTIME_ACCEPTED",
                   "previousProposal3": {"path": str(manifest_path), "identity": identity(prior_raw)},
                   "newIntegrationSeams": [
                       "Owned stream callback no longer inherits temporary Login Invocation binding; public selector still rejects bound callers.",
                       "Original non-destructive Stop is admitted through the current wrapper and synchronously retires the original startup parent before any await.",
                       "All actual MiniApps holds survive overlapping/failed Stop; current Sharing/Hanlin/engine/Bootstrap paths remain owned and drained."]})
    write(OUT / "source-inputs.json", encode(result))
    write(OUT / "full-source-inverses.json", encode({"rows": full}))
    write(OUT / "proposal3-to-proposal4-inverses.json", encode({"rows": delta}))
    write(OUT / "original-wrapper-composition-inverse.json", encode(inverse(WRAPPER, donor, wrapper)))
    for name in ["source-inputs.json", "full-source-inverses.json", "proposal3-to-proposal4-inverses.json", "original-wrapper-composition-inverse.json"]:
        print(name, identity((OUT / name).read_bytes()))


if __name__ == "__main__":
    main()
