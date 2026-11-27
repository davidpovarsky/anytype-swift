#!/usr/bin/env python3
"""Compose only reviewed local originals for the next source-only root merge.

This authoring program never imports a candidate controller, contacts a host,
resolves packages, compiles or executes a test. Its optional Git work is confined
to an exclusive local finite-file whitespace preview with no remote or hooks.
"""
import argparse
import base64
import copy
import difflib
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
START = "af63f6209c38bddf6ed851f0b894e2f627a671af"
START_TREE = "c3c3f46ec9241b6d446000bbdb3f5f89826b6a0c"
SDK = "c0b118f4de28e6ca1e71219237d1ae1c7fabefd8"
SDK_TREE = "89485be6fc9db276c4359726a33b51284835b23b"
KIT = "26beca175d64a4d34e3567f2bbb4bf308d714478"
DONORS = ["e330c0230f352cadff76b4fa0feafd1032fa142e",
          "6b91db33d325f22b62d829051db203121c6cdb8e",
          "78ccffbc711affe743a96edcb79455998f8b73a6"]
PREFIX = "docs/validation/20261127-wave3-kit-sdk-auth-warm-source-intake"
MAP = "docs/any-engine-port/SOURCE_REFACTOR_MAP.json"
REGISTER = "docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md"
SDK_PATH = "Tools/Hanlin/source.json"
MAX_LOG = 16 * 1024**2


def need(value, reason):
    if not value:
        raise ValueError(reason)


def raw(path):
    path = Path(path)
    need(path.is_file() and not path.is_symlink(), "Exact physical original required: " + str(path))
    return path.read_bytes()


def ident(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "gitBlob": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest(),
            "gitMode": "100644"}


def canonical(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()


def b64(data):
    return base64.b64encode(data).decode()


def check(data, identity):
    actual = ident(data)
    need(all(actual[key] == identity[key] for key in ("bytes", "sha256", "gitBlob")),
         "Immutable source identity differs")
    need(identity.get("gitMode", identity.get("mode", "100644")) == "100644", "Reviewed regular-file mode differs")


def pinned(path, digest):
    value = raw(ROOT / path)
    need(ident(value)["sha256"] == digest, "Frozen input changed: " + path)
    return json.loads(value)


def row(before, after):
    return {"status": "A" if before is None else "M", "before": None if before is None else ident(before),
            "beforeBase64": None if before is None else b64(before), "after": ident(after), "base64": b64(after)}


def exact_row(item):
    result = {key: copy.deepcopy(item[key]) for key in ("status", "before", "beforeBase64", "after", "base64")}
    check(base64.b64decode(result["base64"], validate=True), result["after"])
    if result["before"] is not None:
        check(base64.b64decode(result["beforeBase64"], validate=True), result["before"])
    else:
        need(result["beforeBase64"] is None and result["status"] == "A", "Unexpected added preimage")
    return result


def inverse(original, current):
    old_lines, new_lines = original.splitlines(keepends=True), current.splitlines(keepends=True)
    old_offsets, new_offsets = [0], [0]
    for line in old_lines:
        old_offsets.append(old_offsets[-1] + len(line))
    for line in new_lines:
        new_offsets.append(new_offsets[-1] + len(line))
    operations = []
    for tag, a, z, c, d in difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        operations.append({"originalStartByte": old_offsets[a], "originalEndByte": old_offsets[z],
                           "newStartByte": new_offsets[c], "newEndByte": new_offsets[d],
                           "originalBase64": b64(original[old_offsets[a]:old_offsets[z]]),
                           "newBase64": b64(current[new_offsets[c]:new_offsets[d]])})
    restored = current
    for op in reversed(operations):
        a, z = op["newStartByte"], op["newEndByte"]
        need(restored[a:z] == base64.b64decode(op["newBase64"]), "Inverse new span differs")
        restored = restored[:a] + base64.b64decode(op["originalBase64"]) + restored[z:]
    need(restored == original, "Whole original not restored")
    return {"original": ident(original), "candidate": ident(current), "operations": operations, "fullOriginalRestored": True}


def local_git_preview(before, stages):
    records = []
    with tempfile.TemporaryDirectory(prefix="pinkha-kit-sdk-auth-static-") as temporary:
        repo = Path(temporary) / "source.git"
        prefix = ["git", "--no-optional-locks", "-c", "core.hooksPath=/dev/null", "-c", "gc.auto=0"]
        def run(args, data=None, expected=(0,)):
            process = subprocess.run(prefix + args, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     timeout=30, check=False)
            records.append({"argv": prefix + args, "exit": process.returncode,
                            "stdout": process.stdout.decode(), "stderr": process.stderr.decode()})
            need(process.returncode in expected, "Local finite Git preview failed")
            return process.stdout, process.stderr, process.returncode
        run(["init", "--bare", str(repo)])
        stream = bytearray()
        for name, files in [("base", before), *stages.items()]:
            stream.extend(("commit refs/heads/" + name + "\ncommitter ChatGPT <chatgpt@openai.com> 0 +0000\ndata 1\nx\n").encode())
            for path, data in sorted(files.items()):
                need(not any(x in path for x in ('\n', '"', '\\')), "Non-finite Git path")
                stream.extend(("M 100644 inline " + path + "\ndata " + str(len(data)) + "\n").encode())
                stream.extend(data + b"\n")
            stream.extend(b"\n")
        run(["-C", str(repo), "fast-import", "--quiet"], bytes(stream))
        checks = {}
        for name in stages:
            stdout, stderr, code = run(["-C", str(repo), "diff", "--check", "--no-renames", "base", name], expected=(0, 2))
            checks[name] = {"exit": code, "stdout": stdout.decode(), "stderr": stderr.decode()}
        version, _, _ = run(["--version"])
    return checks, {"scope": "ACTUAL_LOCAL_FINITE_GIT_DIFF_ONLY_NOT_A_HOST_OR_RUNTIME_RUN",
                    "gitVersion": version.decode().strip(), "commands": records,
                    "candidateImports": 0, "hostActions": 0, "testsExecuted": 0, "compilerInvocations": 0}


def tree_from_leaves(leaves):
    tree = {}
    for path, leaf in leaves.items():
        node = tree
        parts = path.split("/")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
            need(isinstance(node, dict), "Tree path collision")
        need(parts[-1] not in node, "Duplicate tree path")
        node[parts[-1]] = (leaf["mode"], leaf["sha"])
    def encode(node):
        value = bytearray()
        for name, child in sorted(node.items(), key=lambda pair: (pair[0] + ("/" if isinstance(pair[1], dict) else "")).encode()):
            mode, oid = ("40000", encode(child)) if isinstance(child, dict) else child
            value.extend(mode.encode() + b" " + name.encode() + b"\0" + bytes.fromhex(oid))
        return hashlib.sha1(b"tree " + str(len(value)).encode() + b"\0" + value).hexdigest()
    return encode(tree)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--warm-manifest", required=True)
    parser.add_argument("--warm-sha256", required=True)
    parser.add_argument("--base-leaves", required=True)
    parser.add_argument("--base-leaves-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    out = HERE / args.output
    need(not out.exists(), "Exclusive source preparation namespace required")
    previous = pinned("wave3-inspector-native26-host-source-integration-prepared/prior-attempt2-successor/bound01bc/payload.json",
                      "817ae2747e3175e94a1f5d73fe5ae7b40ff38a32120d30384077e6081c4f3b4a")
    prior_path = ROOT / "wave3-inspector-native26-host-source-integration-prepared/actual1/integration.original.json"
    prior_raw = raw(prior_path)
    need(ident(prior_raw)["sha256"] == "8aafc88fa5b3f8b96ad1f0d8a261d945c32a7a5f2b8ba3275778dcc5d571306f", "Actual158 original receipt changed")
    prior = json.loads(prior_raw)
    need(prior["head"] == prior["normalPushReadback"] == START and prior["tree"] == START_TREE
         and prior["state"] == "SOURCE_TWO_NORMAL_MERGES_PUBLISHED_RUNTIME_CLOSED"
         and prior["sourceRetentionPassed"] is True and prior["reviewedRefactors"] == 133
         and prior["firstFailure"] is None and prior["commandCustodyBlocked"] is False, "Actual positive158 required")
    kit = pinned("kit26-renderer-post158-candidate/prepared2-mounted-core24/source-candidate.unbound.json",
                 "fb5ec0b16f5964edb4fba5ff2da855b672367d4ac721c024f3f3bfd1c6f86342")
    account = pinned("otzaria-selection-authority-review/proposal5/source-inputs.json",
                     "8117deba71707607ca2971e3278ce675a8495ebb74cd9335c2532eb16ac6c875")
    account_handoff = pinned("otzaria-selection-authority-review/proposal5/handoff.json",
                             "830f3ffe2d29005cccd2d84de3ab4604525211f3ebdbcd535bf3d625079932c3")
    bootstrap = pinned("otzaria-supplier273-current-reconciliation/bootstrap-proposal1/source-inputs.json",
                       "7e073a95cc0413ff2b87360dc0f509e4f191be4e00c65f2e01d02c6d6c0e5734")
    mapping = pinned("otzaria-selection-authority-review/proposal5/source-map-prerequisites.json",
                     "5cdcf23dce99c1987ba936277fdde94f4e85438fc53b2f4d581c76c132df4a7c")
    sdk_receipt_path = ROOT / "hanlin-sdk-mcp-title-window-publication/actual1/integration.original.json"
    sdk_receipt_raw = raw(sdk_receipt_path)
    need(ident(sdk_receipt_raw)["sha256"] == "c9ed7976a67792ec2d3ab3706eadd6a3071276d9f252b1c04f0e4cd01f34bdbd", "Actual c0b receipt changed")
    sdk_receipt = json.loads(sdk_receipt_raw)
    need(sdk_receipt["candidateCommit"] == sdk_receipt["normalPushReadback"] == SDK
         and sdk_receipt["candidateTree"] == SDK_TREE and sdk_receipt["firstFailure"] is None
         and sdk_receipt["normalPushCompleted"] is True, "Actual SDK publication was not positively qualified")

    donors, root_rows, origins = {}, {}, {}
    def add(target, path, item, origin):
        need(path not in target, "Duplicate proposed source target: " + path)
        target[path] = exact_row(item)
        origins[path] = origin
    for path, item in kit["sourceRows"].items():
        if path == MAP:
            continue
        target = donors if item["category"] in ("reviewedRendererDonor", "reviewedMountedRenderer78Donor") else root_rows
        add(target, path, item, "Kit99:" + item["category"])
    need(len(donors) == 42 and len(root_rows) == 56, "Exact original Kit99 partition differs")
    n_index = pinned("wave1-n53-c21-independent-intake/primary72-file-index.json",
                     hashlib.sha256(raw(ROOT / "wave1-n53-c21-independent-intake/primary72-file-index.json")).hexdigest())
    n_review = pinned("wave1-n53-c21-independent-intake/independent-review.json",
                      "52b402bd714fd886bb2e77865a766f77fb139b5ac34308167606761b884994ae")
    need(n_review["primaryFileIndex"]["sha256"] == ident(raw(ROOT / "wave1-n53-c21-independent-intake/primary72-file-index.json"))["sha256"], "Original72 index binding changed")
    for item in n_index["files"]:
        value = raw(ROOT / "wave1-n53-c21-independent-intake/source" / item["scope"] / item["path"])
        check(value, item)
        add(donors, item["path"], row(None, value), "N53/C21:" + item["commit"])
    need(len(donors) == 114, "Exactly72+42 original donor paths required")

    links, retained = [], {}
    specs = [
        ("wave1-n53-c21-independent-intake/primary/commit-n53.json", "wave1-n53-c21-independent-intake/source/n53"),
        ("wave1-n53-c21-independent-intake/primary/commit-c21-ffee.json", "wave1-n53-c21-independent-intake/source/c21-ffee"),
        ("wave1-n53-c21-independent-intake/primary/commit-c21-parent12.json", "wave1-n53-c21-independent-intake/source/c21-parent12"),
        ("wave1-n53-c21-independent-intake/primary/commit-c21.json", "wave1-n53-c21-independent-intake/source/c21"),
        ("w2-render-cache-6eec-review/primary-commit.json", "w2-render-cache-6eec-review/source"),
        ("w2-renderer-mounted-78cc-review/primary-commit.json", "w2-renderer-mounted-78cc-review/source"),
    ]
    for meta_path, source_dir in specs:
        meta = json.loads(raw(ROOT / meta_path))
        need(meta["url"].startswith("https://api.github.com/repos/davidpovarsky/anytype-swift/"), "Primary repository changed")
        files = {}
        for file in meta["files"]:
            path = file["filename"]
            value = raw(ROOT / source_dir / path)
            identity = ident(value)
            need(identity["gitBlob"] == file["sha"], "Whole original donor blob differs: " + path)
            need(file["status"] in ("added", "modified"), "Unreviewed donor deletion or rename")
            files[path] = {"status": "A" if file["status"] == "added" else "M", "after": identity}
            if meta["sha"] in ("ffee3b05db8765b718a5cf6dab32f04a1ac75741", "12e49ea69efdde499a6b5343cbe77139073dfbd8"):
                retained[path] = identity
        links.append({"commit": meta["sha"], "tree": meta["commit"]["tree"]["sha"],
                      "parents": [p["sha"] for p in meta["parents"]], "files": files,
                      "primaryMetadata": {"path": meta_path, **ident(raw(ROOT / meta_path))}})
    need(len(links) == 6 and len(retained) == 41 and not set(retained).intersection(donors), "Closed C predecessor closure differs")
    need(set.union(*(set(link["files"]) for link in links)) == set(donors) | set(retained), "Whole original donor union differs")

    for path, item in bootstrap["files"].items():
        add(root_rows, path, {**item, "status": "A" if item["before"] is None else "M"}, "Bootstrap5")
    for item in account["sourceRows"]:
        before = None if item["before"] is None else raw(ROOT / "otzaria-selection-authority-review/proposal5/before" / item["path"])
        candidate = base64.b64decode(item["base64"], validate=True)
        if before is not None:
            check(before, item["before"])
        check(candidate, item["after"])
        add(root_rows, item["path"], row(before, candidate), "Account16v5")

    warm_raw = raw(Path(args.warm_manifest))
    need(ident(warm_raw)["sha256"] == args.warm_sha256, "Final explicitly chosen warm manifest differs")
    warm = json.loads(warm_raw)
    need(warm["knownPublishedSDK"] == SDK and warm["knownRoot"] == START
         and all(warm[key] is False for key in ("buildAdmission", "stagingAdmission", "runtimeActivation"))
         and all(warm[key] is None for key in ("finalAppCommit", "finalSDKMaterializerMarker", "finalSourceSDKNativeProductTuple")),
         "Warm source must remain explicitly closed")
    for item in warm["rows"]:
        need(item["operation"] == "add-only-require-absent" and item["path"].startswith(("Tools/PinkhaDualEngineRuntime/warm_", "docs/validation/")), "Unexpected warm target operation")
        value = raw(Path(item["localPath"]))
        check(value, item)
        add(root_rows, item["path"], row(None, value), "ExactFinalWarmManifest")
    account_evidence = pinned("otzaria-selection-authority-review/proposal5/evidence-inputs.json",
                              "c268369e376453c8614e534711a7d77800f9e0ae1f551293bc449adaff59c2f6")
    for item in account_evidence["evidence"]:
        value = raw(Path(item["localPath"]))
        check(value, item["identity"])
        add(root_rows, item["path"], row(None, value), "OriginalAccountEvidence26")
    for item in account_handoff["bootstrap5"]["evidence"]:
        value = raw(Path(item["path"]))
        check(value, item["identity"])
        add(root_rows, PREFIX + "/bootstrap/" + Path(item["path"]).name, row(None, value), "OriginalBootstrapEvidence6")

    old_map_raw = base64.b64decode(previous["guardInputs"]["sourceMapAfterBase64"], validate=True)
    old_map = json.loads(old_map_raw)
    need(len(old_map["changes"]) == 133 and (json.dumps(old_map, indent=2, ensure_ascii=False) + "\n").encode() == old_map_raw,
         "Actual133 map envelope/encoding differs")
    new_map = copy.deepcopy(old_map)
    updates = []
    for spec in mapping["updates"]:
        index = spec["index"]
        need(old_map["changes"][index] == spec["beforeRow"] and spec["field"] == "replacementBlob", "Account map preimage changed")
        new_map["changes"][index]["replacementBlob"] = spec["after"]
    new_map["changes"][59]["replacementBlob"] = root_rows["Modules/PinkhaKit/Package.swift"]["after"]["gitBlob"]
    sdk_before = base64.b64decode(previous["guardInputs"]["sdkBase64"], validate=True)
    need(sdk_before.count(b"5fffe60fbcec8b12ae2cc14bcb092884677f19b0") == 1, "Exact old SDK revision required")
    sdk_after = sdk_before.replace(b"5fffe60fbcec8b12ae2cc14bcb092884677f19b0", SDK.encode())
    add(root_rows, SDK_PATH, row(sdk_before, sdk_after), "ActualSDKc0bRevisionOnly")
    new_map["changes"][102]["replacementBlob"] = ident(sdk_after)["gitBlob"]
    dependency = new_map["changes"][129]["sharedSources"][3]
    need(dependency == {"path": "Anytype/Sources/Pinkha/Bootstrap/PinkhaSpaceManifestStore.swift",
                        "gitBlob": "b712657e45feea1f05ca68a3aa2098fb9d053e5b"}, "Exact row129 shared dependency changed")
    dependency["gitBlob"] = root_rows[dependency["path"]]["after"]["gitBlob"]
    need(dependency["gitBlob"] == "74058e7b343365446b93db12395db7d2f948997a", "Bootstrap shared source is not reviewed74058")
    for index, (a, z) in enumerate(zip(old_map["changes"], new_map["changes"])):
        if a != z:
            updates.append({"index": index, "before": a, "after": z,
                            "field": "sharedSources[3].gitBlob" if index == 129 else "replacementBlob"})
    need([x["index"] for x in updates] == [15, 59, 63, 102, 115, 129], "Only six scoped original map rows may change")
    new_map["changes"].extend(copy.deepcopy(mapping["appendAfterCurrentRows"]))
    need(len(new_map["changes"]) == 140, "Exactly seven original-baseline rows must be appended")
    map_after = (json.dumps(new_map, indent=2, ensure_ascii=False) + "\n").encode()
    add(root_rows, MAP, row(old_map_raw, map_after), "MinimalOriginal133To140RetentionMap")
    register_before = base64.b64decode(previous["guardInputs"]["registerBase64"], validate=True)
    account_note = raw(ROOT / "otzaria-selection-authority-review/proposal5/append-only-upstream-exception.txt")
    appendix = ("\n\n## 2026-11-27 coherent SDK, Kit, renderer and account source integration\n\n"
        "Promote the four-package Hanlin source revision from 5fffe60fbcec8b12ae2cc14bcb092884677f19b0 "
        "to the actual published c0b118f4de28e6ca1e71219237d1ae1c7fabefd8. Its unchanged original materializer "
        "and all other manifest fields remain exact. The actual SDK source receipt qualifies 1011 files and "
        "39,812,364 source bytes; no installation, compiler or runtime result is supplied by this source merge.\n\n"
        "Align only the ten reviewed inner Kit revision literals with the already selected "
        "26beca175d64a4d34e3567f2bbb4bf308d714478. Preserve all 56 main lock records, other package pins, "
        "public APIs, Xcode target membership and existing module-lock originHash values. Those lock metadata "
        "fields have not been newly resolved and require the original selected-toolchain resolver.\n\n"
        "Retain the original N53/C21 evidence and failure boundaries through normal ancestry. Adopt the exact "
        "6eec renderer UTF8 comparison and 78cc mounted UIKit fixtures, preserving the three original methods. "
        "The distinct closed Core24 profile selects 24 methods / 28 cases with the original compiler, "
        "enumeration, result and custody validators; its two additional methods use controlled HTTP and "
        "mounted UIKit, not a real Native account. Existing Core22, Inspector14, Native26, UIKit23, "
        "attachment and priority focus selections remain separately scoped.\n\n"
        "Add only the reviewed warm-forward and current-product consumer controls and their original evidence. "
        "All build, staging and runtime admission flags remain false, all final product tuples remain null, "
        "and no old product is relabelled as a current build.\n\n").encode() + account_note
    add(root_rows, REGISTER, row(register_before, register_before + appendix), "AppendOnlyOriginalExceptionRegister")

    evidence_specs = {
        "kit/handoff.original.json": "kit26-renderer-post158-candidate/prepared2-mounted-core24/handoff.json",
        "kit/source-index.original.json": "kit26-renderer-post158-candidate/prepared2-mounted-core24/source-index.json",
        "kit/static-preservation-proof.original.json": "kit26-renderer-post158-candidate/prepared2-mounted-core24/evidence/static-preservation-proof.json",
        "kit/full-source-inverses.original.json": "kit26-renderer-post158-candidate/prepared2-mounted-core24/evidence/full-original-source-inverses.json",
        "kit/prior57-byte-proof.original.json": "kit26-renderer-post158-candidate/prepared1/evidence/static-preservation-proof.json",
        "kit/prior57-full-inverse.original.json": "kit26-renderer-post158-candidate/prepared1/evidence/full-literal-inverses.json",
        "kit/root-independent-review.original.json": "kit26-renderer-post158-candidate/prepared2-mounted-core24/root-independent-review.json",
        "native-evidence/independent-review.original.json": "wave1-n53-c21-independent-intake/independent-review.json",
        "native-evidence/independent-byte-proof.original.json": "wave1-n53-c21-independent-intake/independent-byte-proof.json",
        "native-evidence/primary72-file-index.original.json": "wave1-n53-c21-independent-intake/primary72-file-index.json",
        "account/handoff.original.json": "otzaria-selection-authority-review/proposal5/handoff.json",
        "account/evidence-manifest.original.json": "otzaria-selection-authority-review/proposal5/evidence-inputs.json",
        "prior158-root-readback.original.json": "wave3-inspector-native26-host-source-integration-prepared/actual1/root-independent-readback.json",
        "sdk-c0b-root-readback.original.json": "hanlin-sdk-mcp-title-window-publication/actual1/root-independent-readback.json",
    }
    evidence = {}
    for name, source in evidence_specs.items():
        data = raw(ROOT / source)
        evidence[name] = {"after": ident(data), "base64": b64(data)}
    evidence["warm-final-mapping.original.json"] = {"after": ident(warm_raw), "base64": b64(warm_raw)}

    final_rows = {**donors, **root_rows}
    need(len(final_rows) == len(donors) + len(root_rows), "No root override of original donor source was approved")
    before_guards = copy.deepcopy(previous["guardInputs"]["afterFiles"])
    for path, item in final_rows.items():
        if item["before"] is not None:
            if path in before_guards:
                need(before_guards[path] == item["before"], "Actual158 known source preimage differs: " + path)
            before_guards[path] = item["before"]
    before_guards.update(retained)
    after_guards = {**before_guards, **{path: item["after"] for path, item in final_rows.items()}}
    unchanged = {path: value for path, value in before_guards.items() if path not in final_rows}
    for path in ("Tools/Hanlin/prepare_sdk.py", "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved",
                 "Modules/PinkhaTorahPresentation/Package.swift", "Modules/ProtobufMessages/Package.swift",
                 "PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift"):
        need(path in unchanged, "Original materializer/main56/Stage/Protobuf/selectedKit witness changed")
    closed_before = copy.deepcopy(prior["outputPins"]["closedActivation"])
    need(closed_before == previous["guardInputs"]["closedActivationAfter"], "Actual158 activation custody differs")
    closed_after = copy.deepcopy(closed_before)
    for path, item in root_rows.items():
        if not path.startswith("Tools/PinkhaDualEngineRuntime/") or not path.endswith(".json") or item["status"] != "A":
            continue
        value = json.loads(base64.b64decode(item["base64"]))
        fields = {key: val for key, val in value.items() if val is False or val is None or val == []}
        if fields:
            need(not any(old["path"] == path for old in closed_after), "Duplicate new closed activation witness")
            closed_after.append({"path": path, "fields": fields})
    kit_pins = {path: {"before": item["before"], "after": item["after"]}
                for path, item in kit["sourceRows"].items() if item["category"] == "kitExactRevisionOnly"}
    guarded = {"originalRetentionRows": 133, "expectedRetentionRows": 140,
               "beforeFiles": before_guards, "afterFiles": after_guards, "unchangedFiles": unchanged,
               "sourceMapBeforeBase64": b64(old_map_raw), "sourceMapAfterBase64": b64(map_after),
               "sourceMapUpdates": updates, "sourceMapAppendedRows": mapping["appendAfterCurrentRows"],
               "registerBeforeBase64": b64(register_before), "registerAfterBase64": b64(register_before + appendix),
               "sdkBeforeBase64": b64(sdk_before), "sdkAfterBase64": b64(sdk_after), "sdkRevision": SDK,
               "sdkPublication": {"path": "/tmp/pinkha-root-sdk-mcp-title-window-publication-20261127.json", **{key: ident(sdk_receipt_raw)[key] for key in ("bytes", "sha256")}},
               "selectedKitRevision": KIT, "kitRevisionOnlyRows": kit_pins,
               "closedActivationBefore": closed_before, "closedActivationAfter": closed_after,
               "newBaselineRows": [{"path": r["from"], "baselineBlob": r["baselineBlob"], "replacementBlob": r["replacementBlob"]}
                                   for r in mapping["appendAfterCurrentRows"]]}

    leaf_raw = raw(Path(args.base_leaves))
    need(ident(leaf_raw)["sha256"] == args.base_leaves_sha256, "Original complete af63 tree bytes changed")
    leaves = {}
    for line in leaf_raw.split(b"\0"):
        if not line:
            continue
        header, path = line.split(b"\t", 1)
        mode, kind, oid = header.decode().split()
        need(path.decode() not in leaves, "Duplicate base tree leaf")
        leaves[path.decode()] = {"mode": mode, "type": kind, "sha": oid}
    need(tree_from_leaves(leaves) == START_TREE, "Complete original leaf inventory does not reproduce actual af63 tree")
    for path, item in final_rows.items():
        expected = None if item["before"] is None else {"mode": "100644", "type": "blob", "sha": item["before"]["gitBlob"]}
        need(leaves.get(path) == expected, "Actual complete af63 preimage/absence differs: " + path)
    for path, identity in before_guards.items():
        need(leaves.get(path) == {"mode": "100644", "type": "blob", "sha": identity["gitBlob"]}, "Actual full af63 guarded source differs: " + path)
    def projected(rows):
        return {**leaves, **{p: {"mode": "100644", "type": "blob", "sha": r["after"]["gitBlob"]} for p, r in rows.items()}}
    donor_tree = tree_from_leaves(projected(donors))
    source_tree = tree_from_leaves(projected(final_rows))
    base_values = {p: base64.b64decode(r["beforeBase64"]) for p, r in final_rows.items() if r["before"] is not None}
    donor_values = {**base_values, **{p: base64.b64decode(r["base64"]) for p, r in donors.items()}}
    final_values = {**base_values, **{p: base64.b64decode(r["base64"]) for p, r in final_rows.items()}}
    complete_values = {**final_values, **{PREFIX + "/" + p: base64.b64decode(r["base64"]) for p, r in evidence.items()}}
    checks, git_proof = local_git_preview(base_values, {"donors": donor_values, "source": final_values, "complete": complete_values})
    source_inverses = {path: inverse(base_values[path], final_values[path]) for path in sorted(base_values)}
    source_proof = {"schema": "pinkha-coherent-kit-sdk-auth-warm-static-source-proof/v1", "start": START, "startTree": START_TREE,
                    "baseLeafInventory": {"path": str(Path(args.base_leaves)), **ident(leaf_raw)},
                    "fullBaseTreeReconstructed": True, "baseLeafCount": len(leaves), "expectedDonorTree": donor_tree,
                    "expectedSourceTree": source_tree, "fullSourcePathCount": len(final_rows), "donorPaths": len(donors),
                    "rootPaths": len(root_rows), "sourceOrigins": origins, "allPreimagesAndAbsentTargetsMatchActualFullTree": True,
                    "original133RowsRetained": True, "sourceMapChangedIndices": [r["index"] for r in updates],
                    "row129OnlySharedSourceIndex3": True, "sourceMapAddedBaselineRows": 7, "expectedRetentionRows": 140,
                    "sdkOnlyRevisionChanged": True, "main56PinsUnchanged": True, "innerKitOnly10Literals": True,
                    "moduleLockMetadata": "PRESERVED_NOT_NEWLY_RESOLVED", "newRuntimeActivation": False,
                    "priorFullTreeAndInputSourceEvidenceOnly": True, "candidateImports": 0, "hostActions": 0,
                    "testsExecuted": 0, "compilerInvocations": 0, "materializations": 0,
                    "wholeFinalTree": "Computed and fully verified again by the original private-index controller after its actual custody evidence is formed."}
    for name, data in [("static-source-proof.json", canonical(source_proof)),
                       ("full-source-inverses.json", canonical({"schema": "pinkha-coherent-source-whole-file-inverses/v1", "files": source_inverses})),
                       ("local-finite-git-preview.original.json", canonical(git_proof))]:
        need(not data.endswith(b"\n\n") and all(not line.endswith((b" ", b"\t", b"\r")) for line in data.split(b"\n")), "Generated evidence whitespace changed")
        evidence[name] = {"after": ident(data), "base64": b64(data)}
    payload = {"schema": "pinkha-root-kit-sdk-auth-warm-source-payload/v1", "bindingReady": True,
               "start": START, "startTree": START_TREE,
               "priorReceipt": {"path": "/tmp/pinkha-root-inspector-native26-host-source-integration-20261127.json",
                                **{key: ident(prior_raw)[key] for key in ("bytes", "sha256")}},
               "donorTips": DONORS, "donorLinks": links, "retainedDonorFiles": retained,
               "integratedAncestors": ["92a2904112738619f2f689b137ba663b08378730", "0925ff79df8f70be288f96ea117dbd7059e24219", "d528e5413c72320c423ce9ccdbd4fbe423ca4a4a"],
               "donorRows": donors, "rootRows": root_rows, "finalSourcePathCount": len(final_rows),
               "expectedDonorTree": donor_tree, "expectedSourceTree": source_tree,
               "guardInputs": guarded, "diffChecks": checks, "evidence": evidence,
               "finalCommitMessage": "Merge reviewed SDK, Kit, account lifetime and mounted-renderer source\n\nRetain original N53/C21/78cc ancestry and all prior source. Compose the exact reviewed Kit26 revisions, actual c0b SDK pin, original account/Space/Bootstrap lifetime fixes and closed Core24/warm controls. Preserve original failures, all package locks outside the declared literals, source baselines and process custody. This is source integration only; no build, runtime acceptance or SDK materialization is claimed.\n",
               "runtimeAcceptance": False, "testsExecuted": 0, "compilerInvocations": 0, "materializations": 0}
    payload_raw = canonical(payload)
    need(len(payload_raw) <= MAX_LOG, "Final closed payload exceeds unchanged16MiB input bound")
    for label, files in [("guard-before", before_guards), ("guard-after", after_guards)]:
        unique = {v["gitBlob"]: v for v in files.values()}
        need(sum(v["bytes"] + 64 for v in unique.values()) < MAX_LOG, label + " batch exceeds original log bound")
    out.mkdir()
    def emit(name, data):
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)
    emit("payload.json", payload_raw)
    emit("payload.json.gz", gzip.compress(payload_raw, mtime=0))
    for path, item in final_rows.items():
        emit("after/" + path, base64.b64decode(item["base64"]))
        if item["before"] is not None:
            emit("before/" + path, base64.b64decode(item["beforeBase64"]))
    for name, item in evidence.items():
        emit("evidence/" + name, base64.b64decode(item["base64"]))
    emit("source-index.json", canonical({"schema": "pinkha-coherent-final-source-index/v1", "files": {
        path: {key: value for key, value in item.items() if key not in ("base64", "beforeBase64")}
        for path, item in final_rows.items()}, "origins": origins, "sourceCount": len(final_rows),
        "expectedSourceTree": source_tree, "donorCount": len(donors), "rootCount": len(root_rows)}))
    emit("prepare_inputs.original.py", Path(__file__).read_bytes())
    emit("input-bindings.json", canonical({"sourceOnly": True, "start": START, "startTree": START_TREE,
        "warmManifest": {"path": args.warm_manifest, **ident(warm_raw)}, "actualPriorReceipt": ident(prior_raw),
        "actualSDKReceipt": ident(sdk_receipt_raw), "fullBaseLeaves": ident(leaf_raw),
        "payload": ident(payload_raw), "packed": ident(gzip.compress(payload_raw, mtime=0)),
        "expectedDonorTree": donor_tree, "expectedSourceTree": source_tree,
        "sourcePaths": len(final_rows), "evidenceFiles": len(evidence), "hostActions": 0}))
    print(json.dumps({"payload": ident(payload_raw), "packed": ident(gzip.compress(payload_raw, mtime=0)),
                      "sourcePaths": len(final_rows), "donorPaths": len(donors), "rootPaths": len(root_rows),
                      "sourceTree": source_tree, "runtimeAcceptance": False}, indent=2))


if __name__ == "__main__":
    main()
