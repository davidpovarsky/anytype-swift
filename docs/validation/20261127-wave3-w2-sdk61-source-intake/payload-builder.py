#!/usr/bin/env python3
"""Prepare and seal a local finite source payload; never operate a host/repository.

`prepare` retains the complete reviewed inputs and local partial-tree diff
observations. `seal` requires the actual successful SDK publisher receipt and
the unchanged prepared inputs. Neither mode imports an integration controller,
contacts a remote, invokes a compiler, materializes an SDK or opens a runtime.
"""
import argparse
import base64
import copy
import difflib
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess


SELF = Path(__file__).resolve()
HERE = SELF.parent
WORK = HERE.parent
PREVIOUS_PREPARED = HERE / "payload-builder-prepared"
PREPARED = HERE / "payload-builder-prepared3"
SEALED = HERE / "payload-builder-sealed3"
SDK_RECEIPT = WORK / "hanlin-sdk-native-follow-binding-publication/integration.original.json"
SDK_REMOTE_RECEIPT = "/tmp/pinkha-root-sdk-native-follow-binding-publication-20261127.json"
CONTROLLER = WORK / "wave3-w2-sdk61-source-integration-prepared/root-source-integration.unbound2.py"
START = "2752229aacf72f468f32a4bfe5fe0a91142f5dbe"
START_TREE = "2d8db7a1585d48b857578920fa19b3730dde488b"
MAP = "docs/any-engine-port/SOURCE_REFACTOR_MAP.json"
REGISTER = "docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md"
SDK = "Tools/Hanlin/source.json"
HOST = "Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinUI/PinkhaHanlinChatView.swift"
PASTEBOARD = "Anytype/Sources/ServiceLayer/Block/Pastboard/PasteboardHelper.swift"
LOCK = "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
PASTE_PREFIX = "docs/validation/20261127-wave3-pasteboard-options"
ROOT_PREFIX = "docs/validation/20261127-wave3-w2-sdk61-source-intake"
PINNED = {
    "wave3-w2-sdk61-intake/donor-source-inputs.json": "5955fb3c1b0f6a3a6d2a53f23b50eda0be21172c68c338394c5d44633076567d",
    "wave3-w2-sdk61-intake/component-source-inputs.json": "eb481563b244f2fd8fe9a3dc8a5d740a36b0cfc9b88bfbd86e6e930bb0c5dc0c",
    "wave3-w2-sdk61-intake/unchanged-protected-local-locators.json": "33b2c2d3c97ca2802bed94fee26b0237c925574c5b003f54d87a79ea4c17ff7f",
    "wave3-w2-sdk61-intake/protobuf275.primary.json": "a4fecf06228ac73d569fad666ac1283c2d47cc3c4205ee5e8e5df539c13e9466",
    "wave3-w2-sdk61-source-integration-prepared/root-source-integration.unbound2.py": "423e8ce021ef3198bf073d1b11e625156f77ec0ecd5dc6993da38551113be693",
    "wave3-e-properties-app10-t5-intake/accepted265/integration.original.json": "5fb21559add1833d5b964620534e0cf59bf781ad4d888bba13faf1b8b0d010c2",
    "hosted61-component-successor/component-lanes-independent-review.json": "2135f2f193bdd3d6c183b23a9692366fe15c20ee84c1504435a46e6f84631461",
    "hosted61-component-successor/native23-t5-independent-successor-review.json": "a2b8794b206fd28336e9b95d75d9d65b38e711df3a091e8ce970449bec2312e3",
    "otzaria-pasteboard-retention-proposal/artifact-index.json": "8f2edd80f5e0167adab3a5bcbd129fd66f2a338d0c72ba0ff97a513f5f159269",
}


EVIDENCE_INPUTS = [
        ("component-lanes-independent-review.json", WORK / "hosted61-component-successor/component-lanes-independent-review.json"),
        ("native23-t5-independent-successor-review.json", WORK / "hosted61-component-successor/native23-t5-independent-successor-review.json"),
        ("uikit23-source-projection-intake.json", WORK / "hanlin-uikit23-anytype-source-proposal/source-intake.json"),
        ("component-composition-manifest.json", WORK / "hosted61-component-successor/integration-manifest.json"),
        ("component-lane-literal-operations.json", WORK / "hosted61-component-successor/component-lane-literal-operations.json"),
        ("native23-profile-full-inverse.json", WORK / "hosted61-component-successor/native23-profile-full-inverse.json"),
        ("component-successor-literal-operations.json", WORK / "hosted61-component-successor/successor-literal-operations.json"),
        ("g27-original-source-review.json", WORK / "hanlin-g27-native-binding-review/review.json")] + [
    ("payload-builder-source-successor-inverse.json", HERE / "payload-builder-source-successor-inverse.json"),
    ("payload-builder-reader-source-inverse.json", HERE / "payload-builder-reader-source-inverse.json"),
    ("payload-builder-reader-preparation-failure.original.json", HERE / "payload-builder-reader-preparation-failure.original.json"),
    ("payload-builder-reader-before.py", HERE / "build_final_payload2.py")
]




def require(value, message):
    if not value:
        raise ValueError(message)


def identity(raw, mode="100644"):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "gitBlob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
            "gitMode": mode}


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def b64(raw):
    return None if raw is None else base64.b64encode(raw).decode()


def safe_path(value):
    p = PurePosixPath(value)
    require(isinstance(value, str) and not p.is_absolute() and str(p) == value
            and value and not set(p.parts).intersection({"..", ".git"}) and "\0" not in value,
            "Unsafe repository path")
    return value


def read(path):
    path = Path(path)
    require(path.is_absolute() and path.is_relative_to(WORK) and path.resolve() == path
            and path.is_file() and not path.is_symlink(), "Nonphysical local input: " + str(path))
    before = path.stat()
    fields = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_size", "st_mtime_ns", "st_ctime_ns")
    signature = tuple(getattr(before, field) for field in fields)
    require(stat.S_ISREG(before.st_mode) and before.st_size <= 32 * 1024**2, "Oversized or nonregular source input")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        require(tuple(getattr(os.fstat(stream.fileno()), field) for field in fields) == signature,
                "Input identity changed before reading: " + str(path))
        raw = stream.read(32 * 1024**2 + 1)
        require(tuple(getattr(os.fstat(stream.fileno()), field) for field in fields) == signature,
                "Opened input changed during read: " + str(path))
    require(tuple(getattr(path.stat(), field) for field in fields) == signature and len(raw) == before.st_size,
            "Input identity/contents changed during read: " + str(path))
    return raw


def check(raw, pin):
    got = identity(raw, pin.get("gitMode", pin.get("mode", "100644")))
    require(all(got[k] == pin[k] for k in ("bytes", "sha256", "gitBlob")), "Whole original identity differs")
    require(got["gitMode"] in ("100644", "100755"), "Unexpected Git mode")


def exclusive(path, raw):
    require(path.is_relative_to(HERE) and path.resolve() == path, "Only owned local output is permitted")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)


def row(before, after, *, staged=None, origin):
    if staged is None:
        staged = before
    return {"status": "A" if before is None else "M", "before": None if before is None else identity(before),
            "beforeBase64": b64(before), "stageBefore": None if staged is None else identity(staged),
            "stageBeforeBase64": b64(staged), "after": identity(after), "base64": b64(after), "origin": origin}


def validate_rows(rows, root=False):
    for path, value in rows.items():
        safe_path(path)
        require(value["status"] in ("A", "M") and (value["before"] is None) == (value["status"] == "A"),
                "Original status/preimage changed")
        check(base64.b64decode(value["base64"], validate=True), value["after"])
        if value["before"] is None:
            require(value["beforeBase64"] is None, "Addition has original bytes")
        else:
            check(base64.b64decode(value["beforeBase64"], validate=True), value["before"])
        if root:
            if value["stageBefore"] is None:
                require(value["stageBeforeBase64"] is None, "Addition has staged bytes")
            else:
                check(base64.b64decode(value["stageBeforeBase64"], validate=True), value["stageBefore"])


def load_inputs():
    tracked = {}
    def take(path):
        raw = read(path)
        tracked[str(path.relative_to(WORK))] = identity(raw)
        return raw
    for relative, digest in PINNED.items():
        require(identity(take(WORK / relative))["sha256"] == digest, "Reviewed input changed: " + relative)
    donor = json.loads(take(HERE / "donor-source-inputs.json"))
    component = json.loads(take(HERE / "component-source-inputs.json"))
    require(donor["start"] == component["start"] == START and donor["startTree"] == component["startTree"] == START_TREE,
            "Actual reviewed START differs")
    require(len(donor["donorRows"]) == 210 and len(donor["donorLinks"]) == 5
            and donor["donorTips"] == ["f2fad4d9b07d49406bb8c20c838817fd9bc5ae8a",
                "9986f60d8e56d3835d755f1ed07b7255766d3451", "1a890015578962bc6eab8c6e9bb70c51ce189cf3"]
            and len(component["rootRows"]) == 53 and len(component["unchangedWitnesses"]) == 19,
            "Finite reviewed source closure differs")
    validate_rows(donor["donorRows"])
    validate_rows(component["rootRows"], root=True)
    for path, value in component["rootRows"].items():
        stage = donor["donorRows"].get(path)
        expected = stage["after"] if stage else value["before"]
        require(value["stageBefore"] == expected, "Component stage preimage differs")
        if stage:
            require(all(value[k] == stage[k] for k in ("before", "beforeBase64", "status")), "Original START identity differs")
            require(value["stageBeforeBase64"] == stage["base64"], "Original donor bytes differ")
    roots = copy.deepcopy(component["rootRows"])
    protected = {}
    for path, value in component["unchangedWitnesses"].items():
        raw = take(WORK / "hosted61-component-successor/after" / safe_path(path))
        check(raw, value)
        protected[path] = (raw, value)
    locations = json.loads(take(HERE / "unchanged-protected-local-locators.json"))
    paths = {"materializer": "Tools/Hanlin/prepare_sdk.py", "stage": "PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift",
             "lock": LOCK, "kit": "Modules/PinkhaTorahPresentation/Package.swift"}
    for key, value in locations.items():
        raw = take(WORK / value["path"])
        check(raw, value)
        protected[paths[key]] = (raw, {k: value[k] for k in ("bytes", "sha256", "gitBlob", "gitMode")})
    protobuf = take(HERE / "protobuf275.original.swift")
    protobuf_primary = json.loads(take(HERE / "protobuf275.primary.json"))
    protobuf_path = "Modules/ProtobufMessages/Package.swift"
    require(protobuf_primary["display_url"] == "https://github.com/davidpovarsky/anytype-swift/blob/" + START + "/" + protobuf_path
            and protobuf_primary["sha"] == identity(protobuf)["gitBlob"] == "b688ee88408f58af27ca2183646ebd160384fe46"
            and len(protobuf) == 2513 and identity(protobuf)["sha256"] == "1cc18e497d8385c9f6a34c039aac3678b72963507f095567660a1fa51db64220",
            "Original protobuf package path/bytes differ")
    take(CONTROLLER)
    protected[protobuf_path] = (protobuf, identity(protobuf))
    previous = WORK / "hanlin-sdk4cb-host-integration-prepared/after"
    map_raw, register_raw, sdk_raw = (take(previous / p) for p in (MAP, REGISTER, SDK))
    source_map = json.loads(map_raw)
    require(len(source_map["changes"]) == 132 and source_map["baselineCommit"] == "586c98bcc17dee425664224e508fc0e8df277678",
            "Original retention map differs")
    require((json.dumps(source_map, ensure_ascii=False, indent=2) + "\n").encode() == map_raw,
            "Original map formatting did not roundtrip exactly")
    require(json.loads(sdk_raw)["revision"] == "4cb6454c1c6e110ead73179c06ada9e909bf250b", "Original SDK revision differs")
    prior = json.loads(take(WORK / "wave3-e-properties-app10-t5-intake/accepted265/integration.original.json"))
    require(prior["head"] == prior["normalPushReadback"] == START
            and json.loads(protected[LOCK][0])["pins"] == prior["inputPins"]["allPackagePins"]
            and len(prior["inputPins"]["allPackagePins"]) == 56, "Original56 package pins differ")
    paste = WORK / "otzaria-pasteboard-retention-proposal"
    paste_index = json.loads(take(paste / "artifact-index.json"))
    require(len(paste_index["files"]) == 21, "Pasteboard retained packet differs")
    for item in paste_index["files"]:
        relative = safe_path(item["path"])
        raw = take(paste / relative)
        check(raw, item)
        path = PASTE_PREFIX + "/" + relative
        require(path not in roots and path not in donor["donorRows"], "Pasteboard evidence collision")
        roots[path] = row(None, raw, origin="exact-original-pasteboard-proposal-evidence")
    roots[PASTE_PREFIX + "/artifact-index.json"] = row(None, take(paste / "artifact-index.json"), origin="original-pasteboard-proposal-index")
    paste_before, paste_after = take(paste / "before" / PASTEBOARD), take(paste / "after" / PASTEBOARD)
    require(paste_before.replace(b"propertyList(from: data, format: nil)", b"propertyList(from: data, options: [], format: nil)", 1) == paste_after
            and len(paste_after) == len(paste_before) + 13, "Exact original13-byte insertion differs")
    roots[PASTEBOARD] = row(paste_before, paste_after, origin="reviewed-original-pasteboard-empty-options")
    appended = json.loads(take(paste / "proposed-row133.json"))
    require(appended["baselineBlob"] == identity(paste_before)["gitBlob"]
            and appended["replacementBlob"] == identity(paste_after)["gitBlob"], "Pasteboard map binding differs")
    paste_exception = json.loads(take(paste / "exception-append-inverse.json"))["appendUTF8"].encode()
    require(roots[HOST]["after"]["gitBlob"] == "9ec594dc3021aeee39d49ba641f7be3919f475ad", "G27 host input differs")
    for _, path in EVIDENCE_INPUTS:
        take(path)
    tracked[str(SELF.relative_to(WORK))] = identity(read(SELF))
    return {"donor": donor, "component": component, "roots": roots, "protected": protected,
            "map": map_raw, "register": register_raw, "sdk": sdk_raw, "appended": appended,
            "pasteException": paste_exception, "tracked": dict(sorted(tracked.items()))}


def partial_git_diagnostics(output, rows, evidence=None):
    """Real ordinary Git checks over isolated partial trees with repository paths."""
    require(not output.exists(), "Preserve the existing diagnostic observation")
    output.mkdir(parents=True)
    repo, index = output / "partial.git", output / "partial.index"
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0",
                       GIT_OPTIONAL_LOCKS="0", GIT_DIR=str(repo), GIT_INDEX_FILE=str(index), LC_ALL="C")
    commands = []
    def git(args, data=None, allowed=(0,)):
        argv = ["git", "--no-optional-locks", *args]
        result = subprocess.run(argv, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=environment, cwd=output, timeout=30, check=False)
        observation = {"argv": argv, "exit": result.returncode,
                       "stdout": result.stdout.decode(), "stderr": result.stderr.decode()}
        require(result.returncode in allowed, "Local ordinary Git diagnostic failed: " + str(observation))
        commands.append(observation)
        return result.stdout
    git(["init", "--bare", "--template=", str(repo)])
    objects = set()
    def tree(files):
        git(["read-tree", "--empty"])
        entries = []
        for path, (raw, mode) in sorted(files.items()):
            oid = identity(raw)["gitBlob"]
            if oid not in objects:
                require(git(["hash-object", "-w", "--stdin"], raw).decode().strip() == oid, "Git object mismatch")
                objects.add(oid)
            entries.append((mode + " " + oid + "\t" + safe_path(path)).encode() + b"\0")
        git(["update-index", "-z", "--index-info"], b"".join(entries))
        return git(["write-tree"]).decode().strip()
    before = {p: (base64.b64decode(v["beforeBase64"], validate=True), v["before"]["gitMode"])
              for p, v in rows.items() if v["before"] is not None}
    after = {p: (base64.b64decode(v["base64"], validate=True), v["after"]["gitMode"]) for p, v in rows.items()}
    old_tree, source_tree = tree(before), tree(after)
    productive = sorted(p for p in rows if not p.startswith("docs/"))
    git(["diff", "--check", old_tree, source_tree, "--", *productive])
    production = commands[-1]
    git(["diff", "--check", old_tree, source_tree], allowed=(0, 2))
    source = commands[-1]
    complete_tree, complete = source_tree, source
    if evidence is not None:
        final = dict(after)
        for name, value in evidence.items():
            path = ROOT_PREFIX + "/" + safe_path(name)
            require(path not in final, "Intake evidence collision")
            final[path] = (base64.b64decode(value["base64"], validate=True), value["after"]["gitMode"])
        complete_tree = tree(final)
        git(["diff", "--check", old_tree, complete_tree], allowed=(0, 2))
        complete = commands[-1]
    result = {"schema": "pinkha-local-partial-tree-ordinary-diff-observation-v1", "partialTreeOnly": True,
              "actualRootTreeClaimed": False, "beforeTree": old_tree, "sourceTree": source_tree,
              "completeTree": complete_tree, "productivePaths": productive, "productive": production,
              "source": source, "complete": complete, "gitCommands": commands,
              "originalEvidenceWhitespaceModified": False, "compilerOrRuntimeRuns": 0}
    exclusive(output / "ordinary-diff-check.original.json", encoded(result))
    return result


def sdk_publication():
    require(SDK_RECEIPT.exists(), "Actual successful SDK publication receipt is absent; final sealing remains closed")
    raw = read(SDK_RECEIPT)
    value = json.loads(raw)
    require(value["schema"] == "pinkha-root-native-follow-binding-new-ref-publication/v1"
            and value["state"] == "PASS_SOURCE_ONLY_NEW_REF_PUBLISHED"
            and re.fullmatch("[a-f0-9]{40}", value["candidateCommit"])
            and value["candidateCommit"] == value["normalPushReadback"]
            and value["candidateTree"] == "a52fdb359190930d23a76877baf2fe8fa25101d6"
            and value["baseTree"] == "c381d5c97207b30dfd0494bd54b74919010c7b1e"
            and value["base"] == "8b548bbe5b1340a48e741191c41d6b30c73537df"
            and value["ref"] == "refs/heads/codex/pinkha-sdk-native-follow-binding-20261127"
            and value["controllerSHA256"] == "e03bf9046ed18e4a72958c7067666dc600534fd9c707ed909ef501b408408a13"
            and value["payloadSHA256"] == "bf3abf99798e11ed06d3189d5fda105839400d03b39fda5169e358a2cd4d9bd5"
            and value["positiveBasePublicationReceiptSHA256"] == "3afc5bbe91fee176fab2ba0323ad7be5381e1b3c068335716c95f1ab4a723c4f"
            and value["normalPushCompleted"] is True and value["originalSourceWorktreePreserved"] is True
            and value["commandCustodyBlocked"] is False and value["firstFailure"] is None,
            "Actual SDK publication/provenance/custody is not qualified")
    require(all(value[k] == 0 for k in ("compilerInvocations", "testsExecuted", "workflowDispatches", "materializations")),
            "Original SDK source-only evidence scope changed")
    return raw, value


def inverse(path, before, after):
    a, b = before.splitlines(keepends=True), after.splitlines(keepends=True)
    x, y = [0], [0]
    for line in a:
        x.append(x[-1] + len(line))
    for line in b:
        y.append(y[-1] + len(line))
    edits = []
    for op, i, j, k, l in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op != "equal":
            edits.append({"originalStart": x[i], "originalEnd": x[j], "candidateStart": y[k], "candidateEnd": y[l],
                          "originalBase64": b64(before[x[i]:x[j]]), "candidateBase64": b64(after[y[k]:y[l]])})
    restored = after
    for e in reversed(edits):
        start, end = e["candidateStart"], e["candidateEnd"]
        require(restored[start:end] == base64.b64decode(e["candidateBase64"]), "Literal inverse candidate span differs")
        restored = restored[:start] + base64.b64decode(e["originalBase64"]) + restored[end:]
    require(restored == before, "Full original was not restored")
    return {"path": path, "before": identity(before), "after": identity(after), "edits": edits, "fullOriginalRestored": True}


def preservation_note(revision):
    return ("\n\n## 2026-11-27 — Original SDK63 and G27 source preservation\n\n"
            "The reviewed four-package Hanlin source advances from `4cb6454c1c6e110ead73179c06ada9e909bf250b` "
            "to the actually published `" + revision + "`. The original source-only publisher has sole parent "
            "`8b548bbe5b1340a48e741191c41d6b30c73537df`, tree `a52fdb359190930d23a76877baf2fe8fa25101d6`, "
            "and the new non-force ref `codex/pinkha-sdk-native-follow-binding-20261127`. The actual successful "
            "receipt and exact remote readback are required; no planned commit or historical test result substitutes for them.\n\n"
            "Preserve the original SDK63 checkpoint, canonical cancellation and Composer behavior, Promise settlement "
            "correction, explicit-handler bridge and standalone companion boundary. Add only the reviewed original "
            "follow-overlay and G27 native-binding corrections. The shared mounted consumer uses the original binding "
            "generation without changing native account authority or the original SDK API. Three original G27 methods "
            "extend the existing20 selected UIKit methods to23; the two source projections change only their import. "
            "The original attachment metadata successor9986 retains3/13 and adds2/11, alongside original IntentStore3/4, "
            "for8 methods/28 cases. These are source selection requirements, not new runtime passes.\n\n"
            "The61 native source inputs,10 Stage1 UI inputs and separate2 Native23 UI inputs require their real common "
            "compiler receipts. Every existing false/null/empty activation remains closed. All56 original Package.resolved "
            "pins, Kit26 source, original ProtobufMessages package, original materializer, existing native8ac gate and protected T5 custody "
            "remain unchanged. No SDK materialization, native or Apple compile, fixture preparation, runtime, signing "
            "or delivery is authorized by this source record. Historical failures and receipts retain their original "
            "source and execution scope. Pending Inspector changes are outside this payload.\n\n"
            "Only existing retention-map row17's shared host blob and row102's SDK-manifest replacement blob change; "
            "all other132-row metadata and the complete original exception-register prefix remain exact. Pasteboard "
            "has the separate reviewed row133 and exception above. Full source inputs, literal inverses and original "
            "publication evidence are retained under `" + ROOT_PREFIX + "/`.\n").encode()


def guards(inputs, roots, revision, publication_raw):
    all_rows = {**inputs["donor"]["donorRows"], **roots}
    before, after = {}, {}
    for path, value in all_rows.items():
        if path.startswith("docs/") and path not in (MAP, REGISTER):
            continue
        if value["before"] is not None:
            before[path] = value["before"]
        after[path] = value["after"]
    unchanged = {}
    for path, (_, pin) in inputs["protected"].items():
        require(path not in all_rows, "Protected unchanged path is modified: " + path)
        before[path] = after[path] = unchanged[path] = pin
    closed = []
    values = {p: base64.b64decode(v["base64"], validate=True) for p, v in all_rows.items()}
    values.update({p: v[0] for p, v in inputs["protected"].items()})
    for path, raw in sorted(values.items()):
        if path not in after or not path.endswith(".json") or not path.startswith("Tools/PinkhaDualEngineRuntime/"):
            continue
        data = json.loads(raw)
        fields = {k: v for k, v in data.items() if v is None or v is False
                  or isinstance(v, (list, dict)) and len(v) == 0}
        if fields:
            closed.append({"path": path, "fields": fields})
    require(len([r for r in closed if r["path"].endswith("/activation.json")]) == 5,
            "All five original closed activations must be guarded")
    old_map = json.loads(inputs["map"])
    new_map = json.loads(base64.b64decode(roots[MAP]["base64"]))
    return {"originalRetentionRows": 132, "expectedRetentionRows": 133,
            "beforeFiles": dict(sorted(before.items())), "afterFiles": dict(sorted(after.items())),
            "unchangedFiles": dict(sorted(unchanged.items())),
            "sourceMapBeforeBase64": b64(inputs["map"]), "sourceMapAfterBase64": roots[MAP]["base64"],
            "sourceMapUpdates": [{"index": n, "before": old_map["changes"][n], "after": new_map["changes"][n]} for n in (17, 102)],
            "sourceMapAppendedRows": [inputs["appended"]], "sdkBeforeBase64": b64(inputs["sdk"]),
            "sdkAfterBase64": roots[SDK]["base64"], "sdkRevision": revision,
            "registerBeforeBase64": b64(inputs["register"]), "registerAfterBase64": roots[REGISTER]["base64"],
            "closedActivation": closed,
            "sdkPublication": {"path": SDK_REMOTE_RECEIPT, "bytes": len(publication_raw),
                               "sha256": identity(publication_raw)["sha256"]}}


def prepare():
    require(not PREPARED.exists(), "Prepared packet already exists; preserve it and inspect")
    inputs = load_inputs()
    PREPARED.mkdir()
    roots = inputs["roots"]
    merged = {**inputs["donor"]["donorRows"], **roots}
    # The first actual local diagnostic remains original evidence. Reuse it
    # only after exact whole-row and original-input identity comparisons.
    prior_raw = read(PREVIOUS_PREPARED / "ready-without-sdk.json")
    require(identity(prior_raw)["sha256"] == "297088885db2803e88c57a220843cff8700c3b2203fcaaf0da5f56159d01982b",
            "Original local preparation receipt differs")
    prior = json.loads(prior_raw)
    require(json.loads(read(PREVIOUS_PREPARED / "known-root-rows.json")) == roots,
            "Known source/evidence bytes differ from actual original Git check")
    for path, pin in prior["inputs"].items():
        if path == "wave3-w2-sdk61-intake/build_final_payload.py":
            check(read(WORK / path), pin)
        else:
            require(inputs["tracked"].get(path) == pin, "Original prepared source identity changed")
    diagnostic_path = PREVIOUS_PREPARED / "known-input-diagnostics/ordinary-diff-check.original.json"
    diagnostic_raw = read(diagnostic_path)
    diagnostic = json.loads(diagnostic_raw)
    require({k: diagnostic["productive"][k] for k in ("exit", "stdout", "stderr")} == prior["knownProductiveDiff"]
            and {k: diagnostic["source"][k] for k in ("exit", "stdout", "stderr")} == prior["knownFullDiff"]
            and diagnostic["productive"]["exit"] == 0,
            "Original ordinary diagnostic scope differs")
    manifest = {"schema": "pinkha-final-payload-prepared-inputs-v1", "status": "PREPARED_SOURCE_PARTS_FINAL_SDK_UNBOUND",
                "start": START, "startTree": START_TREE, "inputs": inputs["tracked"], "donorRows": 210,
                "componentRows": 53, "pasteboardEvidenceRows": 22, "knownRootRows": len(roots),
                "knownCombinedPaths": len(merged), "pendingFinalPaths": [MAP, REGISTER, SDK],
                "sdkReceiptPath": str(SDK_RECEIPT), "sdkReceiptObservedAtPreparation": SDK_RECEIPT.exists(),
                "sdkRevision": None, "finalPayload": None, "readyForHostExecution": False,
                "runtimeAcceptance": False, "closedActivationUnchanged": True,
                "knownProductiveDiff": {k: diagnostic["productive"][k] for k in ("exit", "stdout", "stderr")},
                "knownFullDiff": {k: diagnostic["source"][k] for k in ("exit", "stdout", "stderr")},
                "reusedOrdinaryDiagnostics": {"path": str(diagnostic_path), **identity(diagnostic_raw)},
                "knownSourceRowsIdenticalToOriginalGitCheck": True,
                "newGitDiagnosticRuns": 0}
    exclusive(PREPARED / "known-root-rows.json", encoded(roots))
    exclusive(PREPARED / "guard-input-shape.json", encoded({"exactController": identity(read(CONTROLLER)),
        "sourceMapExistingUpdates": [17, 102], "appendedRows": [inputs["appended"]],
        "expectedRetentionRows": 133, "sdkRevision": None, "sdkPublication": None,
        "finalSDKBytes": None, "finalMapBytes": None, "finalRegisterBytes": None}))
    exclusive(PREPARED / "sdk-register-append.unbound.txt", preservation_note("ACTUAL_PUBLICATION_COMMIT_REQUIRED_BEFORE_SEALING"))
    exclusive(PREPARED / "ready-without-sdk.json", encoded(manifest))
    print(json.dumps({"status": manifest["status"], "manifest": str(PREPARED / "ready-without-sdk.json"),
                      "identity": identity(encoded(manifest)), "finalPayloadWritten": False}, sort_keys=True))


def seal():
    # Refuse before creating any final output if the actual publication is absent.
    publication_raw, publication = sdk_publication()
    require(PREPARED.is_dir() and not SEALED.exists(), "Preserve existing prepared/sealed state")
    prepared = json.loads(read(PREPARED / "ready-without-sdk.json"))
    inputs = load_inputs()
    require(inputs["tracked"] == prepared["inputs"], "A frozen reviewed local input changed")
    require(json.loads(read(PREPARED / "known-root-rows.json")) == inputs["roots"], "Prepared exact source rows changed")
    revision = publication["candidateCommit"]
    old_revision = b"4cb6454c1c6e110ead73179c06ada9e909bf250b"
    require(inputs["sdk"].count(old_revision) == 1, "SDK manifest revision replacement is ambiguous")
    sdk_after = inputs["sdk"].replace(old_revision, revision.encode())
    old_map = json.loads(inputs["map"])
    new_map = copy.deepcopy(old_map)
    require(new_map["changes"][17]["sharedSources"] == [{"path": HOST, "gitBlob": "00108593ef058d881b522f606c8818bbaf974f0e"}],
            "Original mapped shared host differs")
    new_map["changes"][17]["sharedSources"][0]["gitBlob"] = inputs["roots"][HOST]["after"]["gitBlob"]
    require(new_map["changes"][102]["to"] == SDK and new_map["changes"][102]["replacementBlob"] == identity(inputs["sdk"])["gitBlob"],
            "Original mapped SDK pin differs")
    new_map["changes"][102]["replacementBlob"] = identity(sdk_after)["gitBlob"]
    new_map["changes"].append(inputs["appended"])
    map_after = (json.dumps(new_map, ensure_ascii=False, indent=2) + "\n").encode()
    register_after = inputs["register"] + inputs["pasteException"] + preservation_note(revision)
    roots = copy.deepcopy(inputs["roots"])
    for path, before, after in [(MAP, inputs["map"], map_after), (REGISTER, inputs["register"], register_after), (SDK, inputs["sdk"], sdk_after)]:
        require(path not in roots and path not in inputs["donor"]["donorRows"], "Final metadata path collision")
        roots[path] = row(before, after, origin="root-reviewed-exact-sdk-g27-pasteboard-composition")
    validate_rows(roots, root=True)
    payload = copy.deepcopy(inputs["donor"])
    payload.update(schema="pinkha-root-w2-sdk61-source-payload/v1", rootCompositionPending=False,
                   rootRows=dict(sorted(roots.items())), runtimeAcceptance=False,
                   finalSourcePathCount=len(set(payload["donorRows"]) | set(roots)),
                   commitMessage="Integrate reviewed native UI source, original Hanlin G27 and closed shared acceptance\n\n"
                     "Preserve the original source graph, accounts, evidence and all package locks. Merge the three exact W2 tips; "
                     "bind the actually published original Hanlin source, shared61 and finite closed acceptance, and the original Pasteboard compatibility call.\n\n"
                     "Source only: final Apple/native/runtime qualification remains closed and separate.\n")
    payload["guardInputs"] = guards(inputs, roots, revision, publication_raw)
    evidence = {}
    def evidence_add(name, raw):
        safe_path(name)
        require(name not in evidence and name not in {"root-source-intake.json", "root-integration-controller.py", "prior275-integration.original.json",
            "original-final-sdk-publication.json", "root-controller-full-original-inverse.json"}, "Reserved evidence path collision")
        evidence[name] = {"after": identity(raw), "base64": b64(raw)}
    evidence_add("payload-builder.py", read(SELF))
    evidence_add("prepared-inputs.original.json", read(PREPARED / "ready-without-sdk.json"))
    evidence_add("source-inputs-manifest.json", encoded({"schema": "pinkha-root-source-inputs-v1", "files": inputs["tracked"],
        "actualSDKPublication": {"localPath": str(SDK_RECEIPT), **identity(publication_raw)}}))
    evidence_add("combined-metadata-full-inverses.json", encoded({"schema": "pinkha-root-metadata-full-inverses-v1", "files": [
        inverse(path, inputs[key], base64.b64decode(roots[path]["base64"])) for path, key in [(MAP, "map"), (REGISTER, "register"), (SDK, "sdk")]]}))
    evidence_add("sdk-g27-preservation-source-only.md", preservation_note(revision))
    for name, path in EVIDENCE_INPUTS:
        evidence_add(name, read(path))
    SEALED.mkdir()
    all_rows = {**payload["donorRows"], **roots}
    diagnostics = partial_git_diagnostics(SEALED / "exact-final-diagnostics", all_rows, evidence)
    payload["diffCheck"] = {k: diagnostics["source"][k] for k in ("exit", "stdout", "stderr")}
    payload["completeDiffCheck"] = {k: diagnostics["complete"][k] for k in ("exit", "stdout", "stderr")}
    evidence_add("local-ordinary-diff-check.original.json", encoded(diagnostics))
    # The diagnostic is JSON-encoded original stdout; its addition has no raw
    # evidence whitespace. Verify its actual new path in one complete tree.
    final_diagnostics = partial_git_diagnostics(SEALED / "complete-final-diagnostics", all_rows, evidence)
    require({k: final_diagnostics["complete"][k] for k in ("exit", "stdout", "stderr")} == payload["completeDiffCheck"],
            "Retaining original diagnostics changed full ordinary Git output")
    payload["evidence"] = evidence
    raw = encoded(payload)
    packed = gzip.compress(raw, compresslevel=9, mtime=0)
    exclusive(SEALED / "payload.json", raw)
    exclusive(SEALED / "payload.json.gz", packed)
    summary = {"schema": "pinkha-local-final-source-payload-seal-v1", "status": "SEALED_SOURCE_ONLY_AWAITING_ROOT_REVIEW",
               "start": START, "sdkRevision": revision, "sdkPublication": payload["guardInputs"]["sdkPublication"],
               "payload": identity(raw), "compressed": identity(packed), "donorRows": len(payload["donorRows"]),
               "rootRows": len(roots), "finalSourcePathCount": payload["finalSourcePathCount"], "evidenceRows": len(evidence),
               "protectedUnchangedFiles": len(payload["guardInputs"]["unchangedFiles"]),
               "closedGuardFiles": len(payload["guardInputs"]["closedActivation"]), "sourceRetentionRows": 133,
               "productiveDiffExit": final_diagnostics["productive"]["exit"], "completeDiffCheck": payload["completeDiffCheck"],
               "runtimeAcceptance": False, "hostActions": 0, "compilerOrNativeTests": 0,
               "rootControllerUnbound": identity(read(CONTROLLER)), "rootControllerExecuted": False}
    exclusive(SEALED / "sealed-manifest.json", encoded(summary))
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "seal"))
    options = parser.parse_args()
    prepare() if options.mode == "prepare" else seal()
