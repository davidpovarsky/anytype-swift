#!/usr/bin/env python3
"""Replay original native evidence; never rerun a product test or rewrite its result."""
import argparse, ast, hashlib, json, re, tarfile, zipfile
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from datetime import datetime, timezone

def require(ok, label):
    if not ok:
        raise RuntimeError(label)

def digest(stream):
    h = hashlib.sha256()
    while data := stream.read(1024 * 1024):
        h.update(data)
    return h.hexdigest()

def sha(path):
    with Path(path).open("rb") as f:
        return digest(f)

def read(path):
    return json.loads(Path(path).read_bytes())

def member_path(name):
    p = PurePosixPath(name)
    require(not p.is_absolute() and p.parts and all(x not in ("", ".", "..") for x in p.parts), "relative_member")
    return Path(*p.parts)

def checked_file(path, expected):
    require(path.is_file() and not path.is_symlink(), "regular_original")
    require((path.stat().st_size, sha(path)) == tuple(expected), "original_bytes_hash")

def audit(root, controller):
    require(sha(controller) == "4db3dbf17c147ad92d5d7d9d85588acdc3c86c9abcc21fc4a836b5342580902b", "exact_original_controller")
    result = read(root / "result.json")
    require(result["run_id"] == "45501479246" and result["run_attempt"] == "1" and
            result["controller_sha"] == "c0482eefb372ecd2cf6ccc91b6a2d5083b75a1c7" and
            result["heart_sha"] == "ea796999d648e27dcb7ad23a0bbd849d35fadc5a" and
            result["status"] == "FAIL" and result["error"] == "native_peer_running", "original_failure_preserved")
    checked_file(root / "artifact.zip", (100141950, "3dece544572620b0feb8761d0120258c3344f78b470021d763f329162e54a10c"))
    custody = result["private_custody"]
    checked_file(root / "private-evidence.tar.gz", (custody["plaintext_bytes"], custody["plaintext_sha256"]))
    checked_file(root / "private-evidence.cms", (custody["ciphertext_bytes"], custody["ciphertext_sha256"]))
    with zipfile.ZipFile(root / "artifact.zip") as z:
        require(z.read("result.json") == (root / "result.json").read_bytes(), "original_public_result")
        require(hashlib.sha256(z.read("private-evidence.cms")).hexdigest() == custody["ciphertext_sha256"], "original_ciphertext")
    index = read(root / "private-original-index.json")
    require(index["artifactID"] == 14972345626 and index["runId"] == result["run_id"] and
            index["controllerSHA"] == result["controller_sha"], "recipient_index_binding")
    expected = {x["path"]: (x["bytes"], x["sha256"]) for x in index["members"]}
    require(len(expected) == len(index["members"]), "unique_original_members")
    originals = {}
    with tarfile.open(root / "private-evidence.tar.gz", "r|gz") as archive:
        for m in archive:
            member_path(m.name)
            require(m.isdir() or m.isfile(), "no_links_in_original_archive")
            if m.isfile():
                require(m.name not in originals, "no_duplicate_tar_member")
                originals[m.name] = (m.size, digest(archive.extractfile(m)))
    require(originals == expected, "all_original_archive_members_verified")
    selected = root / "private-audit-inputs"
    for item in index["selected"]:
        require(expected[item["path"]] == (item["bytes"], item["sha256"]), "selected_original_binding")
        checked_file(selected / member_path(item["path"]), expected[item["path"]])
    private = selected / "private"
    commands = read(private / "commands.json")
    require(len(commands) == result["command_count"] and len({x["label"] for x in commands}) == len(commands),
            "all_original_commands")
    by_label = {x["label"]: x for x in commands}
    for command in commands:
        require(command["returncode"] == 0, "original_command_success")
        for suffix in ("stdout", "stderr"):
            path = private / "commands" / (command["label"] + "." + suffix)
            require(originals[path.relative_to(selected).as_posix()][1] == command[suffix + "_sha256"], "original_command_stream")
    # Execute only pure validators extracted from the unchanged original controller.
    # The producer, capture routines, and test/build dispatch code never execute.
    original_ast = ast.parse(controller.read_text(encoding="utf-8"))
    names = {"audit_owner_tree_census", "require_tree_census_receipt", "audit_capture_attempts", "audit_one"}
    pure = [n for n in original_ast.body if isinstance(n, ast.FunctionDef) and n.name in names]
    require({n.name for n in pure} == names, "original_pure_validators_present")
    scope = dict(require=require, sha=sha, json=json, re=re, hashlib=hashlib)
    exec(compile(ast.Module(body=pure, type_ignores=[]), str(controller), "exec"), scope)
    original_class = next(n for n in original_ast.body if isinstance(n, ast.ClassDef) and n.name == "RemoteFileRunner")
    schema_fn = next(n for n in original_class.body if isinstance(n, ast.FunctionDef) and n.name == "custom_schema")
    def archived_checked(path, expected):
        require(originals[path.relative_to(selected).as_posix()] == tuple(expected), "original_archived_bytes_hash")
    scope.update(CUSTOM_METHOD="TestLoadedAccountCustomSchemaSource",
                 native=SimpleNamespace(relative_member=member_path, checked_file=archived_checked))
    exec(compile(ast.Module(body=[schema_fn], type_ignores=[]), str(controller), "exec"), scope)
    schema_out = {}
    schema_self = SimpleNamespace(private=private, binary=None, result={"executions":[]})
    schema_self.container = lambda *a, **k: (0, private / "commands/native-custom-schema.stdout", None)
    scope["custom_schema"](schema_self)
    schema_out = schema_self.result["nativeCustomSchema"]
    def receipt(role, label):
        return read(private / "peers" / role / (label + ".json"))
    owner = receipt("owner", "identity")
    member = receipt("member", "identity")
    source, a, b = owner["source"], owner["identity"], member["identity"]
    nonce = owner["nonce"]
    phases = [("owner",x) for x in ("identity","grant","rerouted","final")] + [
        ("member",x) for x in ("identity","joined","cold","received","final","reopen-final")]
    for role, label in phases:
        r = receipt(role, label)
        reopen = label == "reopen-final"
        require(r["protocol"] == "pinkha-native-source-file-peers-v1" and r["nonce"] == nonce and
                r["role"] == role and r["phase"] == label and r["walletCreateCalls"] == (0 if reopen else 1)
                and r["walletRecoverCalls"] == (1 if reopen else 0) and not r["fullSpaceMigrationComplete"]
                and not r["historySemanticsValidated"], "original_owned_phase")
    require(a["AccountID"] != b["AccountID"] and a["PeerID"] != b["PeerID"] and
            a["Namespace"] != b["Namespace"], "independent_native_accounts")
    rows, census = scope["audit_owner_tree_census"](source)
    for r in (owner["createdSource"], receipt("member","cold"), receipt("member","received"), receipt("member","reopen-final")):
        scope["require_tree_census_receipt"](r, rows, census)
    require(set(source) == {"SpaceID","PageID","FileObjectID","FileID","Variants","TreeCensus","TreeCensusSHA256"} and len(source["Variants"]) == 1, "exact_original_source_contract")
    variant = source["Variants"][0]
    grant, joined = receipt("owner","grant"), receipt("member","joined")
    require(grant["memberAccountID"] == b["AccountID"] and grant["aclHead"] and
            grant["memberPermission"] > 0 and joined["aclHead"] == grant["aclHead"] and
            joined["memberPermission"] == grant["memberPermission"] and
            joined["actualNativeFileObjectID"] == source["FileObjectID"] and
            joined["actualNativeFileID"] == source["FileID"], "native_grant_and_delivery")
    cold = receipt("member","cold")
    require(not cold["actualIPv4"] and cold["missingLocalRoot"] and cold["explicitFileGap"] and
            not cold["sourceReceipt"]["CurrentFilePayloadCompleteness"], "remote_payload_absent_initially")
    received, reopened = receipt("member","received"), receipt("member","reopen-final")
    p = received["prefetch"]
    require(received["networkPayloadVerified"] and p["NativeFetches"] > 0 and
            all(p[k] is True for k in ("AccountSessionAuthorizedAtFinalRead","CapturedFileIDsBoundToUnchangedCheckpoint",
                                      "EveryFetchedBlockRereadFromLocalStore","RequiresNewFrozenCapture")) and
            all(p[k] is False for k in ("FilePayloadCompleteness","HasNativeSourceAdmission","PermitsDestinationWrites")),
            "authorized_native_transport")
    for r in (received, reopened):
        require(r["fullPlaintextBytes"] == variant["PlaintextBytes"] == 2097152 and
                r["exactMetadataBytesVerified"] and r["nativeOwnerReferenceVerified"], "exact_full_payload")
    require(reopened["identity"]["AccountID"] == b["AccountID"] and reopened["identity"]["PeerID"] == b["PeerID"] and
            not reopened["actualIPv4"] and reopened["offlineFreshProcess"] and reopened["testPassed"] and
            reopened["accountStopped"] and reopened["sourceSpaceID"] == source["SpaceID"], "native_offline_fresh_process")
    ids = set()
    infos = {}
    for key in ("owner-online","member-online","member-reopen"):
        info = read(private / "commands" / ("inspect-" + key + ".stdout"))[0]
        require(info["Id"] not in ids and info["Id"] == (private / "commands" / ("start-" + key + ".stdout")).read_text().strip(),
                "exact_distinct_container")
        ids.add(info["Id"]); infos[key] = info
        host, config, state = info["HostConfig"], info["Config"], info["State"]
        require(info["Image"] == result["compiler_image"] and host["ReadonlyRootfs"] and
                config["User"] == "1001:1001" and host["CapDrop"] == ["ALL"] and
                "no-new-privileges" in host["SecurityOpt"] and not state["OOMKilled"] and
                not state["Dead"] and not state["Error"], "original_process_isolation")
        if key == "member-reopen":
            require(host["NetworkMode"] == "none" and not state["Running"] and state["Status"] == "exited"
                    and state["ExitCode"] == 0 and state["StartedAt"] < state["FinishedAt"], "fast_successful_offline_exit")
        else:
            require(state["Running"] and state["Pid"] > 0, "actual_online_process")
        role, phase = key.split("-")
        scope["audit_one"](private / "peers" / role / ("native-" + phase + ".stdout"), "TestLoadedAccountRemoteFilePeer")
    for role in ("owner","member"):
        final = receipt(role,"final")
        stopped = read(private / "commands" / ("finished-" + role + "-online.stdout"))[0]
        require(final["testPassed"] and final["accountStopped"] and not stopped["State"]["Running"] and
                stopped["State"]["ExitCode"] == 0 and
                stopped["State"]["FinishedAt"] < infos["member-reopen"]["State"]["StartedAt"], "cold_process_order")
    # Match byte-preserving manifest members from the tar without extracting private payloads.
    manifests, declared = [], 0
    for path in (private / "peers").glob("*/native-source-*/manifest.json"):
        manifest = read(path)
        members = [manifest["SourceRows"]]
        for obj in manifest["Objects"]:
            members += [obj["Snapshot"], obj["NativeJSONView"]]
        prefix = path.parent.relative_to(selected).as_posix()
        for item in members:
            require(originals[prefix + "/" + item["Path"]] == (item["Bytes"], item["SHA256"]), "captured_object_bytes")
        declared += len(members)
        manifests.append({"sha256":sha(path), "objects":len(manifest["Objects"])})
    attempts = {}
    for role, stage in (("owner","owner-initial"),("member","member-cold"),("member","member-prefetched"),("member","member-offline-reopen")):
        attempts[stage] = scope["audit_capture_attempts"](private / "peers" / role, "capture-" + stage + "-attempt-",stage)
    require(all(x["returncode"] == 0 for x in result["peer_container_cleanup"] + result["container_cleanup"])
            and result["network_cleanup"]["returncode"] == 0 and result["compiled_source_unchanged"], "original_cleanup_and_source")
    return dict(format="pinkha-retained-native-peer-audit-v1",status="PASS",
                auditedAtUTC=datetime.now(timezone.utc).isoformat(),runId=result["run_id"],runAttempt="1",
                artifactID=14972345626,controllerSHA=result["controller_sha"],nativeSourceSHA=result["heart_sha"],
                producerStatus="FAIL",producerError="native_peer_running",producerResultSHA256=sha(root/"result.json"),
                originalArchiveSHA256=sha(root/"artifact.zip"),originalRegularFiles=len(originals),
                originalCommandStreams=2*len(commands),selectedOriginalsVerified=len(index["selected"]),
                originalControllerSHA256=sha(controller),auditorSHA256=sha(Path(__file__)),
                nativeSchema=schema_out,nativePeerExecutions=3,nativeOnlineAccounts=2,
                nativePayloadBytes=2097152,nativePeerTreeRows=rows,nativePeerTreeCensusSHA256=census,
                originalPeerManifests=manifests,originalDeclaredObjectMembers=declared,
                networkPayloadVerified=True,offlineFreshProcessVerified=True,
                rootCause="offline reopen exited successfully before State.Running inspection; old namespace inode was reused after prior process termination",
                processIdentityProof="distinct immutable Docker IDs; original native receipts; start time after both prior containers exited",
                originalNamespacePredicateWouldFail=reopened["identity"]["Namespace"] in (a["Namespace"],b["Namespace"]),
                nativeReopenStdoutSHA256=sha(private/"peers/member/native-reopen.stdout"),
                nativeReopenReceiptSHA256=sha(private/"peers/member/reopen-final.json"),
                originalReopenDockerInspectSHA256=sha(private/"commands/inspect-member-reopen.stdout"),
                peerCaptureAttempts=attempts,productTestsRerun=0,productBuilds=0,
                wholeSpaceMigrationComplete=False,historySemanticsValidated=False,
                destinationMigrationValidated=False)

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("root",type=Path); p.add_argument("controller",type=Path); p.add_argument("output",type=Path)
    a=p.parse_args()
    r=audit(a.root,a.controller)
    a.output.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(r,sort_keys=True))
