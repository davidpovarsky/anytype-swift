#!/usr/bin/env python3
"""Exercise a real Any process with disposable data; never read an existing wallet."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

ANY_SOURCE = "88fae2e5ae7d0f46d6707567a3123081faa8de9a"
RELEASE_EXE_SHA256 = "5993e211157985cb42fdec95c678f0c1b96da04796b4d0cd15cff9ef6bf52591"


class ContractFailure(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, url):
        return None


HTTP = urllib.request.build_opener(NoRedirect)


def require(value, message):
    if not value:
        raise ContractFailure(message)


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def source_provenance():
    script = Path(__file__).resolve()
    repository = next((parent for parent in script.parents if (parent / ".git").exists()), None)
    if repository is None:
        return {"gitHEAD": None, "trackedSourceDirty": None}
    revision = subprocess.run(["git", "-C", str(repository), "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=10)
    status = subprocess.run(["git", "-C", str(repository), "status", "--porcelain=v1", "--",
                             "Tools/AnyEngineValidation/run_runtime_validation.py", "Modules/PinkhaAnyEngine"],
                            capture_output=True, text=True, timeout=10)
    require(revision.returncode == 0 and status.returncode == 0, "source provenance could not be read")
    result = {"gitHEAD": revision.stdout.strip(), "trackedSourceDirty": bool(status.stdout.strip())}
    package = repository / "Modules" / "PinkhaAnyEngine"
    sources = list((package / "Sources").rglob("*.swift")) if package.exists() else []
    sources += [path for path in (package / "Package.swift", package / "Package.resolved") if path.exists()]
    manifest = {path.relative_to(repository).as_posix(): digest(path) for path in sorted(sources)}
    result["swiftSourceManifestSHA256"] = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    result["swiftSourceFiles"] = len(manifest)
    return result


class Peer:
    def __init__(self, binary, folder, network=None):
        self.folder = Path(folder)
        self.folder.mkdir()
        private_binary = self.folder / ("any.exe" if os.name == "nt" else "any")
        shutil.copy2(binary, private_binary)
        self.binary = str(private_binary)
        self.network = network
        self.process = None
        self.endpoint = None
        self.token = None
        self.boot = 0
        self.streams = []

    def start(self):
        self.boot += 1
        config = {
            "mode": "managed", "webUI": {"enabled": False},
            "p2p": {"enabled": False, "localDiscovery": False,
                    "global": {"enabled": False}},
            "push": {"enabled": False}, "index": {"embedder": "none"},
            "log": {"defaultLevel": "error", "format": 2},
        }
        if self.network:
            config["network"] = {"nodeconf": self.network}
        config_file = self.folder / "config.json"
        config_file.write_text(json.dumps(config), encoding="utf-8")
        out_path = self.folder / ("stdout-%s.private.log" % self.boot)
        err_path = self.folder / ("stderr-%s.private.log" % self.boot)
        self.streams = [out_path.open("wb"), err_path.open("wb")]
        env = {k: v for k, v in os.environ.items() if not k.startswith("ANY_")}
        self.process = subprocess.Popen(
            [self.binary, "run", "--mode", "managed", "--config", str(config_file),
             "--data-dir", str(self.folder / "data"), "--addr", "127.0.0.1:0"],
            cwd=self.folder, env=env, stdin=subprocess.DEVNULL,
            stdout=self.streams[0], stderr=self.streams[1])
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            require(self.process.poll() is None, "engine exited before readiness")
            text = out_path.read_text(encoding="utf-8", errors="replace")
            address = re.search(r"(?m)^LISTENING (127\.0\.0\.1:\d+)\s*$", text)
            token = re.search(r"(?m)^CONTROL_TOKEN ([0-9a-f]+)\s*$", text)
            if address and token:
                self.endpoint = "http://" + address.group(1)
                self.token = token.group(1)
                health = self.request("GET", "/v1/health")
                require(health.get("status") == "ok", "health was not ready")
                return health
            time.sleep(0.1)
        raise ContractFailure("engine readiness timed out")

    def request(self, method, path, body=None, timeout=30, control=False):
        raw = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if control:
            headers["X-Any-Control-Token"] = self.token
        request = urllib.request.Request(self.endpoint + path, raw, headers, method=method)
        try:
            with HTTP.open(request, timeout=timeout) as response:
                data = response.read()
                value = json.loads(data) if data else {}
                if method in ("POST", "PATCH", "PUT", "DELETE") and isinstance(value, dict):
                    pages = value.get("pages") or []
                    rejected = value.get("rejections") or any(
                        page.get("rejections") for page in pages if isinstance(page, dict))
                    require(not rejected, "mutation contains rejections inside a successful HTTP response")
                return value
        except urllib.error.HTTPError as error:
            try:
                code = json.loads(error.read()).get("error", {}).get("code", "unknown")
            except (ValueError, AttributeError):
                code = "non_json_error"
            # Never include request bodies, auth responses, or server-provided secrets.
            raise ContractFailure("HTTP %s: %s" % (error.code, code)) from None

    def auth(self, mnemonic=None):
        request = {} if mnemonic is None else {"mnemonic": mnemonic}
        return self.request("POST", "/v1/auth", request, control=True)

    def stop(self):
        if self.process is None:
            return
        failure = None
        if self.process.poll() is None:
            try:
                self.request("POST", "/v1/shutdown", {}, control=True)
                self.process.wait(timeout=20)
                require(self.process.returncode == 0, "engine shutdown returned nonzero")
            except Exception as error:
                failure = error
                self.process.kill()
                self.process.wait(timeout=10)
        elif self.process.returncode != 0:
            failure = ContractFailure("engine exited unexpectedly before cleanup")
        for stream in self.streams:
            stream.close()
        self.streams = []
        self.process = None
        if failure:
            raise failure


class OutboundBlock:
    """Windows rule restricted to one private temporary executable copy."""
    def __init__(self, peer):
        self.peer = peer
        self.name = "PinkhaAnyValidation-" + str(uuid.uuid4())
        self.created = False
        self.evidence = None

    def powershell(self, script):
        result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                                 "$ErrorActionPreference='Stop'; " + script],
                                capture_output=True, encoding="utf-8", errors="replace", timeout=40)
        require(result.returncode == 0, "temporary firewall rule operation failed; no policy bypass attempted")
        return json.loads(result.stdout) if result.stdout.strip() else None

    def enable(self):
        require(os.name == "nt", "verified offline test requires the Windows process-specific firewall fixture")
        require(self.peer.process is None, "stop the test engine before isolating it")
        profiles = self.powershell("@(Get-NetFirewallProfile | ForEach-Object { [bool]$_.Enabled }) | ConvertTo-Json -Compress")
        require(profiles and all(profiles), "all firewall profiles must already be enabled")
        existing = self.powershell("@(Get-NetFirewallRule -Name '" + self.name +
                                  "' -ErrorAction SilentlyContinue).Count | ConvertTo-Json")
        require(existing == 0, "refusing to change an existing firewall rule")
        self.created = True
        program = self.peer.binary.replace("'", "''")
        self.powershell("New-NetFirewallRule -Name '" + self.name + "' -DisplayName '" + self.name +
                        "' -Direction Outbound -Action Block -Program '" + program +
                        "' -Enabled True -Profile Any -PolicyStore PersistentStore | Out-Null")
        active = self.powershell("$r=Get-NetFirewallRule -PolicyStore ActiveStore -Name '" + self.name +
            "'; $a=$r | Get-NetFirewallApplicationFilter; "
            "[pscustomobject]@{name=$r.Name; enabled=$r.Enabled.ToString(); direction=$r.Direction.ToString(); "
            "action=$r.Action.ToString(); program=$a.Program} | ConvertTo-Json -Compress")
        require(active["enabled"] == "True" and active["direction"] == "Outbound" and
                active["action"] == "Block" and Path(active["program"]) == Path(self.peer.binary),
                "active firewall rule differs from the isolated test executable")
        self.evidence = {"method": "Windows outbound firewall rule on unique temporary executable",
                         "ruleName": self.name, "activeVerified": True,
                         "privateExecutableSHA256": digest(self.peer.binary),
                         "existingRulesModified": False, "globalProfileChanges": False}
        return self.evidence

    def disable(self):
        if not self.created:
            return
        self.powershell("Remove-NetFirewallRule -Name '" + self.name + "' -PolicyStore PersistentStore")
        count = self.powershell("@(Get-NetFirewallRule -PolicyStore ActiveStore -Name '" + self.name +
                               "' -ErrorAction SilentlyContinue).Count | ConvertTo-Json")
        require(count == 0, "temporary firewall rule removal was not verified")
        self.created = False
        if self.evidence:
            self.evidence["removalVerified"] = True


def eventually(check, label, timeout=90):
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            if check():
                return
        except (ContractFailure, urllib.error.URLError, OSError) as error:
            last_error = str(error)
        time.sleep(0.35)
    raise ContractFailure(label + " did not converge" + (": " + last_error if last_error else ""))


class Subscription:
    def __init__(self, peer, path, body):
        self.events = queue.Queue()
        self.closed = threading.Event()
        self.response = None
        self.error = None
        raw = json.dumps(body).encode("utf-8")
        self.request = urllib.request.Request(peer.endpoint + path, raw,
                                              {"Content-Type": "application/json"}, method="POST")
        self.thread = threading.Thread(target=self.read, daemon=True)
        self.thread.start()

    def read(self):
        try:
            with HTTP.open(self.request, timeout=15) as response:
                self.response = response
                event, data = None, []
                while not self.closed.is_set():
                    line = response.readline()
                    if not line:
                        break
                    line = line.decode("utf-8").rstrip("\r\n")
                    if not line:
                        if event and data:
                            self.events.put((event, json.loads("\n".join(data))))
                        event, data = None, []
                    elif line.startswith("event:"):
                        event = line[6:].strip()
                    elif line.startswith("data:"):
                        data.append(line[5:].lstrip())
        except Exception as error:
            if not self.closed.is_set():
                self.error = type(error).__name__

    def wait(self, event, predicate=lambda value: True):
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            try:
                kind, data = self.events.get(timeout=0.3)
                if kind == event and predicate(data):
                    return data
            except queue.Empty:
                if self.error:
                    raise ContractFailure("SSE stream failed: " + self.error)
        raise ContractFailure("SSE " + event + " was not observed")

    def close(self):
        self.closed.set()
        if self.response is not None:
            # CPython exposes the socket through the response's buffered reader.
            # shutdown unblocks readline before close waits for its I/O lock.
            raw = getattr(getattr(self.response, "fp", None), "raw", None)
            connection = getattr(raw, "_sock", None)
            if connection is not None:
                try:
                    connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            self.response.close()
        self.thread.join(timeout=2)
        require(not self.thread.is_alive(), "SSE reader did not terminate after closing the socket")


def run(args):
    binary = Path(args.binary).resolve(strict=True)
    summary = {"schemaVersion": 1, "status": "RUNNING", "scope": "real-engine-component-integration",
               "startedAtUTC": datetime.now(timezone.utc).isoformat(), "anySourceSHA": ANY_SOURCE,
               "binarySHA256": digest(binary), "harnessSHA256": digest(__file__),
               "network": "explicit-config" if args.network_config else "official-disposable-only",
               "localEmbedding": "disabled", "productionUserData": "never-opened",
               "checks": [], "limitations": ["Not full iOS application acceptance.",
                 "Does not test physical iPad, UI rendering, files, or semantic embedding quality."]}
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def check(name, action):
        started = time.monotonic()
        try:
            result = action()
        except Exception as error:
            # Exception messages in this harness are bounded and never include auth data.
            reason = str(error) if isinstance(error, ContractFailure) else type(error).__name__
            summary["checks"].append({"name": name, "status": "FAIL", "error": reason,
                                      "durationMs": round((time.monotonic() - started) * 1000)})
            save()
            raise
        summary["checks"].append({"name": name, "status": "PASS",
                                  "durationMs": round((time.monotonic() - started) * 1000)})
        save()
        return result

    space_id, mnemonic = None, None
    peers, subscription, block, second_block = [], None, None, None
    with tempfile.TemporaryDirectory(prefix="pinkha-any-validation-") as temporary:
        root = Path(temporary)
        try:
            summary["sourceAtStart"] = check("source_provenance", source_provenance)
            if args.probe_binary:
                summary["swiftProbeBinarySHA256"] = check("swift_probe_binary_digest", lambda: digest(args.probe_binary))
            expected = args.expected_binary_sha256 or RELEASE_EXE_SHA256
            check("pinned_binary_digest", lambda: require(summary["binarySHA256"] == expected,
                                                         "binary digest differs from expected"))
            network = Path(args.network_config).read_text(encoding="utf-8") if args.network_config else None
            first = Peer(binary, root / "peer-a", network)
            second = Peer(binary, root / "peer-b", network)
            peers = [first, second]
            check("managed_boot", first.start)
            auth = check("fresh_disposable_account", first.auth)
            mnemonic, account_id = auth["mnemonic"], auth["accountId"]
            del auth
            health = first.request("GET", "/v1/health")
            require(health["account"] == account_id, "account identity mismatch")
            summary["runtimeVersion"] = health["version"]
            space = check("create_owned_disposable_space", lambda: first.request(
                "POST", "/v1/spaces", {"name": "Disposable Pinkha engine validation"}))
            space_id = space["id"]
            require(space["ownRole"] == "owner", "test space is not owned by test account")
            del space
            base = "/v1/spaces/" + space_id
            obj = check("create_native_page", lambda: first.request("POST", base + "/objects", {
                "type": "page", "initialProperties": {"any": {"name": "בדיקת מנוע התורה"}}}))
            object_id = obj["objectId"]
            block_path = base + "/objects/" + object_id + "/editor/editor_blocks/blocks"
            original = "בראשית ברא אלהים — Hebrew and English 123"
            created = check("create_hebrew_editor_block", lambda: first.request("POST", block_path, {
                "type": "paragraph", "text": original}))
            require(not created.get("rejections"), "editor write was rejected inside 2xx response")
            block_id = created["recordIds"][0]
            query = {"objectId": object_id, "dataset": "editor_blocks", "sort": ["nav.pos", "id"]}

            def texts(peer):
                return {record["id"]: record.get("text") for record in
                        peer.request("POST", base + "/query", query)["records"]}

            check("hebrew_exact_readback", lambda: require(texts(first).get(block_id) == original,
                                                           "Hebrew block did not round trip exactly"))
            subscription = Subscription(first, base + "/query/subscribe", query)
            check("sse_initial_snapshot", lambda: subscription.wait("snapshot", lambda data: original in
                                                                    json.dumps(data, ensure_ascii=False)))
            updated = original + " | live edit"
            check("edit_native_block", lambda: first.request("PATCH", block_path + "/" + block_id,
                                                              {"set": {"text": updated}}))
            check("sse_live_delta", lambda: subscription.wait("changes", lambda data: updated in
                                                              json.dumps(data, ensure_ascii=False)))
            subscription.close()

            probe_result = None
            claim_baseline = None
            anchor_remove, anchor_replace = None, None

            def invoke_probe(peer, options):
                command = [str(Path(args.probe_binary).resolve()), "--endpoint", peer.endpoint,
                           "--account-id", account_id, "--space-id", space_id] + options
                result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        encoding="utf-8", timeout=90)
                require(result.returncode == 0, "Swift component probe returned nonzero")
                value = json.loads(result.stdout)
                require(value.get("status", "").startswith("PASS"), "Swift probe did not pass")
                return value

            def claim_snapshot(peer, expected_ids):
                return invoke_probe(peer, ["--mode", "verify", "--expected-claims",
                                           ",".join(sorted(expected_ids))])

            def same_snapshot(snapshot, expected):
                return all(sorted(snapshot.get(key, [])) == sorted(expected.get(key, []))
                           for key in ("allClaimIds", "liveClaimIds", "conflictKeys"))

            def append_claim(peer, operation, kind, marker="", source_ref="Genesis.1.1", observed=(), collision=False):
                options = ["--mode", "append", "--kind", kind, "--operation-id", operation,
                           "--target-id", object_id, "--allow-disposable-writes"]
                if kind in ("add", "replace"):
                    payload = base64.b64encode(json.dumps({"synthetic": marker}).encode("utf-8")).decode("ascii")
                    options += ["--provider-id", "sefaria", "--source-ref", source_ref,
                                "--payload-base64", payload]
                if observed:
                    options += ["--observed", ",".join(observed)]
                if collision:
                    options += ["--expect-collision"]
                return invoke_probe(peer, options)

            def verify_probe(peer):
                expected_ids = claim_baseline.get("allClaimIds", [])
                require(bool(expected_ids), "Swift provision probe omitted physical claim ids")
                try:
                    value = claim_snapshot(peer, expected_ids)
                except ContractFailure:
                    return False
                return same_snapshot(value, claim_baseline)

            if args.probe_binary:
                probe_result = check("swift_adapter_real_http", lambda: invoke_probe(
                    first, ["--allow-disposable-writes"]))
                summary["swiftProbe"] = {key: probe_result[key] for key in ("status", "scope", "checks")
                                          if key in probe_result}
                anchor_remove = check("swift_create_remove_anchor", lambda: append_claim(
                    first, uuid.uuid4().hex, "add", "remove anchor", "Genesis.1.2"))
                anchor_replace = check("swift_create_replace_anchor", lambda: append_claim(
                    first, uuid.uuid4().hex, "add", "replace anchor", "Genesis.1.3"))
                baseline_ids = set(probe_result["allClaimIds"]) | {anchor_remove["claimId"], anchor_replace["claimId"]}
                claim_baseline = check("swift_anchor_snapshot", lambda: claim_snapshot(first, baseline_ids))
                summary["scope"] = "real-engine-and-swift-claims-component-integration"
            else:
                summary["checks"].append({"name": "swift_adapter_real_http", "status": "NOT_RUN",
                                           "reason": "No Swift probe binary supplied."})

            check("second_peer_boot", second.start)
            check("second_peer_restore_separate_device", lambda: require(
                second.auth(mnemonic)["accountId"] == account_id, "restored account differs"))
            check("second_peer_space_discovery", lambda: eventually(
                lambda: any(row.get("id") == space_id for row in
                            second.request("GET", "/v1/spaces")["spaces"]),
                "restored space index", args.sync_timeout))
            check("two_peer_native_block_convergence", lambda: eventually(
                lambda: texts(second).get(block_id) == updated, "second-peer native block", args.sync_timeout))
            if probe_result:
                check("swift_claims_two_peer_convergence", lambda: eventually(
                    lambda: verify_probe(second), "Swift claim projection", args.sync_timeout))
            peer_update = updated + " | peer two"
            check("second_peer_native_write", lambda: second.request("PATCH", block_path + "/" + block_id,
                                                                    {"set": {"text": peer_update}}))
            check("reverse_peer_convergence", lambda: eventually(
                lambda: texts(first).get(block_id) == peer_update, "first-peer native block", args.sync_timeout))
            check("first_peer_graceful_shutdown", first.stop)
            block = OutboundBlock(first)
            summary["offlineIsolation"] = check("activate_scoped_network_block", block.enable)
            if probe_result:
                check("second_peer_shutdown_before_partition", second.stop)
                second_block = OutboundBlock(second)
                summary["secondPeerOfflineIsolation"] = check("activate_second_scoped_block", second_block.enable)
                check("second_peer_offline_restart", second.start)
                check("second_peer_offline_account_reopen", lambda: require(
                    second.auth(mnemonic)["accountId"] == account_id, "second offline account differs"))
                check("second_peer_offline_claim_baseline", lambda: require(
                    verify_probe(second), "second peer lost the shared baseline"))
            check("isolated_offline_restart", first.start)
            check("offline_account_reopen", lambda: require(first.auth(mnemonic)["accountId"] == account_id,
                                                            "offline account differs"))
            check("offline_persisted_read", lambda: require(texts(first).get(block_id) == peer_update,
                                                            "persisted block differs after offline reopen"))
            if probe_result:
                check("swift_claims_offline_reopen", lambda: require(verify_probe(first),
                                                                   "Swift claims changed after offline reopen"))
                collision_operation = uuid.uuid4().hex
                collision_a = check("partitioned_collision_variant_a", lambda: append_claim(
                    first, collision_operation, "add", "collision A", "Genesis.1.5"))
                collision_b = check("partitioned_collision_variant_b", lambda: append_claim(
                    second, collision_operation, "add", "collision B", "Genesis.1.5"))
                require(collision_a["claimId"] != collision_b["claimId"], "distinct claims lost their physical identity")
                require(collision_a["logicalKey"] == collision_b["logicalKey"], "logical operation identity differs")
                independent_operation_a = uuid.uuid4().hex
                independent_a = check("partitioned_independent_add_a", lambda: append_claim(
                    first, independent_operation_a, "add", "independent A", "Genesis.1.4"))
                independent_b = check("partitioned_independent_add_b", lambda: append_claim(
                    second, uuid.uuid4().hex, "add", "independent B", "Genesis.1.4"))
                removed = check("partitioned_observed_remove", lambda: append_claim(
                    first, uuid.uuid4().hex, "remove", observed=[anchor_remove["claimId"]]))
                unobserved_add = check("partitioned_unobserved_add", lambda: append_claim(
                    second, uuid.uuid4().hex, "add", "unobserved concurrent add", "Genesis.1.2"))
                replacement_a = check("partitioned_replace_a", lambda: append_claim(
                    first, uuid.uuid4().hex, "replace", "replacement A", "Genesis.1.3", [anchor_replace["claimId"]]))
                replacement_b = check("partitioned_replace_b", lambda: append_claim(
                    second, uuid.uuid4().hex, "replace", "replacement B", "Genesis.1.3", [anchor_replace["claimId"]]))
                own_ids_a = {r["claimId"] for r in (collision_a, independent_a, removed, replacement_a)}
                own_ids_b = {r["claimId"] for r in (collision_b, independent_b, unobserved_add, replacement_b)}
                a_partition_snapshot = check("partitioned_snapshot_a", lambda: claim_snapshot(
                    first, baseline_ids | own_ids_a))
                b_partition_snapshot = check("partitioned_snapshot_b", lambda: claim_snapshot(
                    second, baseline_ids | own_ids_b))
                check("partition_did_not_cross_peer_boundary", lambda: require(
                    not own_ids_b.intersection(a_partition_snapshot["allClaimIds"]) and
                    not own_ids_a.intersection(b_partition_snapshot["allClaimIds"]),
                    "claims crossed an active offline partition"))
                retry = check("offline_exact_retry", lambda: append_claim(
                    first, independent_operation_a, "add", "independent A", "Genesis.1.4"))
                check("offline_exact_retry_is_noop", lambda: require(
                    retry["claimId"] == independent_a["claimId"] and retry["created"] is False and
                    same_snapshot(claim_snapshot(first, baseline_ids | own_ids_a), a_partition_snapshot),
                    "exact retry created or changed a claim"))
                refused = check("ordered_conflicting_payload_refused", lambda: append_claim(
                    first, independent_operation_a, "add", "different local payload", "Genesis.1.4", collision=True))
                check("ordered_refusal_does_not_mutate", lambda: require(
                    refused["status"] == "PASS_ORDERED_COLLISION_REFUSED" and
                    same_snapshot(claim_snapshot(first, baseline_ids | own_ids_a), a_partition_snapshot),
                    "local collision refusal changed the canonical snapshot"))
                expected_claims = {
                    "allClaimIds": sorted(baseline_ids | own_ids_a | own_ids_b),
                    "liveClaimIds": sorted((set(claim_baseline["liveClaimIds"]) -
                        {anchor_remove["claimId"], anchor_replace["claimId"]}) |
                        {r["claimId"] for r in (independent_a, independent_b, unobserved_add, replacement_a, replacement_b)}),
                    "conflictKeys": sorted(set(claim_baseline["conflictKeys"]) | {collision_a["logicalKey"]}),
                }
            offline_text = "כתיבה ללא רשת — שלום"
            offline_write = check("offline_native_write", lambda: first.request("POST", block_path,
                {"type": "paragraph", "text": offline_text}))
            require(not offline_write.get("rejections"), "offline write was rejected inside 2xx response")
            offline_id = offline_write["recordIds"][0]
            check("offline_write_readback", lambda: require(texts(first).get(offline_id) == offline_text,
                                                            "offline readback differs"))
            def blocked_write_stays_local():
                deadline = time.monotonic() + 4
                while time.monotonic() < deadline:
                    require(offline_id not in texts(second), "isolated peer write reached the online peer")
                    time.sleep(0.25)
            check("offline_write_not_visible_to_other_peer", blocked_write_stays_local)
            check("offline_graceful_shutdown", first.stop)
            if probe_result:
                check("claims_restart_while_still_partitioned", first.start)
                check("claims_auth_while_still_partitioned", lambda: first.auth(mnemonic))
                check("partitioned_claims_survive_cold_reopen", lambda: require(
                    same_snapshot(claim_snapshot(first, baseline_ids | own_ids_a), a_partition_snapshot),
                    "offline claims changed after cold reopen"))
                check("partitioned_reopen_shutdown", first.stop)
            check("remove_scoped_network_block", block.disable)
            check("online_restart_after_offline_write", first.start)
            check("online_account_reopen", lambda: first.auth(mnemonic))
            check("offline_write_survives_reopen", lambda: require(texts(first).get(offline_id) == offline_text,
                                                                   "offline write was not durable"))
            if probe_result:
                check("second_peer_partition_shutdown", second.stop)
                check("remove_second_scoped_block", second_block.disable)
                check("second_peer_online_restart", second.start)
                check("second_peer_online_reopen", lambda: second.auth(mnemonic))
                def merged_claims_match(peer):
                    try:
                        return same_snapshot(claim_snapshot(peer, expected_claims["allClaimIds"]), expected_claims)
                    except ContractFailure:
                        return False
                check("concurrent_claims_converge_on_both_peers", lambda: eventually(
                    lambda: merged_claims_match(first) and merged_claims_match(second),
                    "concurrent claim projection", args.sync_timeout))
                merged = claim_snapshot(first, expected_claims["allClaimIds"])
                live = set(merged["liveClaimIds"])
                check("collision_variants_retained_and_quarantined", lambda: require(
                    collision_a["claimId"] in merged["allClaimIds"] and collision_b["claimId"] in merged["allClaimIds"] and
                    collision_a["claimId"] not in live and collision_b["claimId"] not in live and
                    collision_a["logicalKey"] in merged["conflictKeys"], "merged collision was silently resolved"))
                check("concurrent_independent_adds_retained", lambda: require(
                    {independent_a["claimId"], independent_b["claimId"]}.issubset(live), "an independent add was lost"))
                check("observed_remove_preserves_unobserved_add", lambda: require(
                    anchor_remove["claimId"] not in live and unobserved_add["claimId"] in live,
                    "remove erased an unobserved concurrent add or resurrected its anchor"))
                check("concurrent_replace_retains_both_successors", lambda: require(
                    anchor_replace["claimId"] not in live and
                    {replacement_a["claimId"], replacement_b["claimId"]}.issubset(live),
                    "concurrent replacement lost a successor or resurrected its anchor"))
                merged_retry = check("post_merge_exact_retry", lambda: append_claim(
                    first, independent_operation_a, "add", "independent A", "Genesis.1.4"))
                check("post_merge_retry_has_no_new_claim", lambda: require(
                    merged_retry["created"] is False and merged_claims_match(first),
                    "post-merge retry altered the projection"))
                summary["claimConvergence"] = {"allClaims": len(merged["allClaimIds"]),
                    "liveClaims": len(merged["liveClaimIds"]), "conflictKeys": len(merged["conflictKeys"]),
                    "bothPeersPhysicallyPartitioned": True}
            check("offline_write_replicates_to_second_peer", lambda: eventually(
                lambda: texts(second).get(offline_id) == offline_text, "offline native write", args.sync_timeout))
            final_sources = source_provenance()
            check("executed_source_unchanged", lambda: require(
                digest(__file__) == summary["harnessSHA256"] and
                (not args.probe_binary or final_sources["swiftSourceManifestSHA256"] ==
                 summary["sourceAtStart"]["swiftSourceManifestSHA256"]),
                "harness or Swift sources changed during validation"))
            summary["sourceAtFinish"] = final_sources
            summary["status"] = "PASS_REAL_ENGINE_COMPONENT"
        except Exception as error:
            summary["status"] = "FAIL_REAL_ENGINE_COMPONENT"
            summary["fatalFailure"] = str(error) if isinstance(error, ContractFailure) else type(error).__name__
        finally:
            if subscription:
                try:
                    subscription.close()
                except Exception:
                    summary["cleanupSubscription"] = "reader-close-not-confirmed"
                    summary["status"] = "FAIL_REAL_ENGINE_COMPONENT"
            for active_block in (block, second_block):
                if active_block is None or not active_block.created:
                    continue
                try:
                    active_block.disable()
                except Exception:
                    summary["cleanupFirewall"] = "rule-removal-not-confirmed"
                    summary["status"] = "FAIL_REAL_ENGINE_COMPONENT"
            if space_id and peers and peers[0].process is not None:
                try:
                    peers[0].request("DELETE", "/v1/spaces/" + space_id, timeout=20)
                    summary["cleanupSpace"] = "local-deletion-accepted"
                except Exception:
                    summary["cleanupSpace"] = "not-confirmed"
            for peer in peers:
                try:
                    peer.stop()
                except Exception:
                    summary["cleanupProcess"] = "forced-stop-required"
                    summary["status"] = "FAIL_REAL_ENGINE_COMPONENT"
            mnemonic = None
            summary["finishedAtUTC"] = datetime.now(timezone.utc).isoformat()
            save()
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 0 if summary["status"].startswith("PASS") else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True)
    parser.add_argument("--expected-binary-sha256")
    parser.add_argument("--output", required=True)
    parser.add_argument("--probe-binary")
    parser.add_argument("--sync-timeout", type=int, default=90)
    network = parser.add_mutually_exclusive_group(required=True)
    network.add_argument("--network-config", help="Explicit staging/local-network nodeconf YAML")
    network.add_argument("--allow-public-network", action="store_true",
                         help="Allow fresh synthetic account bootstrap on the official network")
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
