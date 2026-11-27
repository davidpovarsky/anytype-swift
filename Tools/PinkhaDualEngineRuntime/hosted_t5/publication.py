"""Original public allowlist/scanner plus bounded ciphertext custody glue."""
from __future__ import annotations

import json
import os
from pathlib import Path

from profile import PREFIX, digest, require

RECIPIENT_SHA = "47a137c28c8564ba8c913b00db9a9e47e5669092b7112e10adfec59949cf6853"
RECIPIENT_SPKI = "f101e91b46c3389438f69ca00aaf3608f829a34219d84453ff3b36c518361c6a"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def private_json(path, value):
    path = Path(path)
    require(path.is_absolute() and path.parent.resolve() == path.parent, "Physical private metadata path required")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(canonical(value)); stream.flush(); os.fsync(stream.fileno())
    return {"path": str(path), "sha256": digest(path)}


def preflight(control, output, commands, shared, activation, binding):
    final = activation["finalProducerTuple"]
    public = Path(control) / PREFIX / "recipient-public.pem"
    require(digest(public) == RECIPIENT_SHA and activation["recipient"]
            == {"publicPEMSHA256": RECIPIENT_SHA, "spkiDERSHA256": RECIPIENT_SPKI}, "Exact public-only recipient required")
    script = Path(control) / PREFIX / "custody_crypto.mjs"
    data = {"schema": "pinkha-t5-private-preflight-v1", "nodeIdentity": final["nodeIdentity"], "publicKey": str(public), "binding": binding}
    plan = private_json(output / "private-control" / "crypto-preflight.json", data)
    log, command = commands.run([final["nodeIdentity"]["executable"], str(script), "preflight", plan["path"]],
                                "private-custody-preflight", 120)
    observed = shared.decode(shared.raw(log, 65536))
    require(observed == {"status": "PASS_PUBLIC_RECIPIENT_AND_NODE_NOT_CUSTODY", "recipientSPKISHA256": RECIPIENT_SPKI,
                         "nodeIdentity": final["nodeIdentity"]}, "Actual existing Node/recipient does not match selected source")
    return {"originalCommand": command, "observation": observed, "plan": plan, "scriptSHA256": digest(script)}


def account_scope(consumer, lane, directory, udid, shutdown, shared):
    """Called only after the actual owned shutdown, using its captured container."""
    container = consumer.t5_containers.get(udid)
    if container is None:
        require(udid not in consumer.invoked_devices, "An invoked fixture has no captured original account container")
        return None
    root = container / "Library/Application Support/Anytype/middleware-go"
    if not root.exists():
        require(udid not in consumer.invoked_devices, "An invoked fixture has no original native account root")
        return None
    require(shutdown["device"]["state"] == "Shutdown" and root.is_dir() and root.resolve() == root and not root.is_symlink()
            and root.is_relative_to(container), "Finite actual owned shutdown account scope required")
    observation = {"status": "ORIGINAL_OWNED_ACCOUNT_SHUTDOWN_OBSERVED", "lane": lane, "udid": udid,
        "container": str(container), "nativeRoot": str(root), "actualShutdown": shutdown,
        "originalOwnedGroupsAbsent": sorted(consumer.commands.absent_groups)}
    ref = private_json(directory / "native-account-custody.json", observation)
    return {"kind": "account", "id": "account-" + lane, "lane": lane, "root": str(root),
            "container": str(container), "observation": ref["path"]}


def encrypt_private(control, output, commands, shared, activation, binding, account_scopes):
    require(commands.is_open and set(commands.groups) == commands.absent_groups,
            "All actual original owned groups must be absent before encryption can spawn")
    require(all(scope["kind"] == "account" for scope in account_scopes), "Only exact owned account roots accepted")
    scopes = [{"kind": "evidence", "id": "original-evidence", "root": str(output / "evidence")}, *account_scopes]
    # Retain only completed command directories. The encryptor's own live log
    # cannot be part of its plaintext input and is separately public-only JSON.
    for index, directory in enumerate(sorted(commands.root.iterdir())):
        require(directory.is_dir() and not directory.is_symlink() and directory.resolve() == directory,
                "Original command custody directory is not physical")
        require(directory.name != "encrypt-private-custody", "Ciphertext command already exists; no retry or replacement")
        scopes.append({"kind": "command", "id": "command-" + str(index), "root": str(directory)})
    final = activation["finalProducerTuple"]
    ciphertext = output / "ciphertext" / "original-private-custody.bin"
    value = {"schema": "pinkha-t5-private-seal-plan-v1", "output": str(output), "scopes": scopes,
        "processClosure": "ALL_ORIGINAL_OWNED_GROUPS_ABSENT", "noFurtherNativeEffects": True,
        "nodeIdentity": final["nodeIdentity"], "publicKey": str(Path(control) / PREFIX / "recipient-public.pem"),
        "recipientSPKISHA256": RECIPIENT_SPKI, "binding": binding, "ciphertext": str(ciphertext)}
    plan = private_json(output / "private-control" / "seal-plan.json", value)
    log, command = commands.run([final["nodeIdentity"]["executable"], str(Path(control) / PREFIX / "custody_crypto.mjs"),
                                "seal", plan["path"]], "encrypt-private-custody", 120)
    report = shared.decode(shared.raw(log, 65536))
    require(report["status"] == "PASS_AUTHENTICATED_PRIVATE_CIPHERTEXT_NOT_RESTORED"
            and report["recipientSPKISHA256"] == RECIPIENT_SPKI and report["ciphertextSHA256"] == digest(ciphertext)
            and report["ciphertextBytes"] == ciphertext.stat().st_size and report["plaintextUploaded"] is False
            and report["originalDataDeleted"] is False and report["restoredBytesVerified"] is False,
            "Actual original encrypted custody is incomplete")
    # This is safe public metadata only, never the private inventory or scope.
    receipt = {**report, "binding": binding, "originalCommandExit": command["exitCode"],
               "accountScopes": len(account_scopes), "privateCustodyRestoreStillRequired": True}
    private_json(output / "ciphertext" / "ciphertext-receipt.json", receipt)
    return receipt


def credential_inventory(consumer, t5):
    records = []
    for udid, container in sorted(consumer.t5_containers.items()):
        require(udid in consumer.invoked_devices, "No foreign/uninvoked credential scope")
        candidates = (container / t5["helpers"]["run_t5_native_ui"].UI_SECRETS,
                      container / t5["helpers"]["t5_remaining_freshness"].PRIVATE / "secrets.json")
        found = False
        for path in candidates:
            if not path.exists():
                continue
            require(path.is_file() and path.resolve() == path and not path.is_symlink()
                    and path.is_relative_to(container) and 0 < path.stat().st_size <= 65536, "Owned complete credential inventory required")
            value = t5["helpers"]["t5_native_ui_evidence"].json.loads(path.read_text())
            require(all(isinstance(value.get(key), str) and value[key] for key in ("token", "mnemonic", "accountKey")),
                    "Partial credential inventory cannot authorize public log upload")
            records.append(value); found = True
        require(found, "Missing original private credentials; public original logs remain withheld")
    require(records, "No complete original credential inventory for public evidence")
    return records


def original_allowed_files(output, t5):
    """Map the original finite UI allowlist to the unchanged e574 stage paths.

    The original freshness runner's separate JSON/log policy is restricted to
    its one original lane. No generic extension-based scan of the whole job is
    accepted for UI attachments or the copied private account witnesses.
    """
    allowed = []
    ui = output / "evidence/lanes/t5-native-ui"
    # Same original evidence roles: execution, fixture, native mutations, core
    # result and the two independent R08 results. Only physical path names differ.
    for relative in ("execution.json", "private/pinkha-t5-native-ui-fixture.json",
                     "private/pinkha-t5-native-ui-mutations.json", "core-ui/result.json",
                     "r08-he-light/result.json", "r08-he-dark/result.json"):
        path = ui / relative
        if path.is_file():
            allowed.append(path)
    for name in ("preparation", "core-ui", "r08-he-light", "r08-he-dark"):
        directory = ui / name
        if directory.is_dir():
            allowed.extend(path for path in directory.iterdir() if path.is_file()
                and (path.name.endswith(".log") or path.name.endswith(".command.json")
                     or path.name in {"selection.json", "summary.json", "tests.json", "simulators-before.json",
                                      "simulators-after-create.json", "simulators-final.json"}))
    evidence, r08 = t5["evidence"], t5["helpers"]["t5_native_ui_r08"]
    for name, methods in [("core-ui", list(evidence.METHODS.values())),
                          *(("r08-he-" + appearance, [r08.METHOD]) for appearance in r08.APPEARANCES)]:
        directory = ui / name / "private-attachments"
        manifest = directory / "manifest.json"
        if manifest.is_file():
            value = json.loads(manifest.read_text(encoding="utf-8-sig"))
            evidence.require(isinstance(value, list), "Unexpected failed UI attachment manifest")
            allowed.append(manifest)
            for case in value:
                if case.get("testIdentifier", "").removesuffix("()") in methods:
                    allowed.extend(evidence.attachment_path(directory, item.get("exportedFileName"))
                                   for item in case.get("attachments", []))
    freshness = output / "evidence/lanes/t5-remaining-freshness"
    if freshness.is_dir():
        allowed.extend(path for path in freshness.rglob("*") if path.is_file() and path.suffix in (".json", ".log")
            and not any(part.endswith(".xcresult") or part in {"secrets.json", "final-private-sandbox"}
                        for part in path.relative_to(freshness).parts)
            and path.name not in {"native-account-custody.json", "invocation.json", "descriptor-binding.json"})
    commands = output / "commands"
    if commands.is_dir():
        # The original command allowlist admits log/.command.json files only.
        # Process receipts and arbitrary other JSON remain in ciphertext.
        for directory in commands.iterdir():
            if directory.is_dir() and not directory.is_symlink():
                allowed.extend(path for path in directory.iterdir() if path.is_file()
                               and (path.name.endswith(".log") or path.name.endswith(".command.json")))
    return allowed


def publish(output, consumer, t5, public_status):
    """Use the original validator, original streaming scanner and finite files.

    All raw xcresults and account stores travel only in authenticated ciphertext.
    If a failed preparation did not leave its full original credential inventory,
    original logs/attachments remain private instead of guessing that they are safe.
    """
    records = credential_inventory(consumer, t5)
    needles = [row[key].encode(encoding) for row in records for key in ("mnemonic", "accountKey")
               for encoding in ("utf8", "utf-16-le", "utf-16-be")]
    scanner = t5["pair"].contains_secret
    def all_original_credentials(path, original_needles):
        return scanner(path, list(set([*needles, *original_needles])))
    private_json(output / "public-status.json", public_status)
    allowed = [output / "public-status.json", *original_allowed_files(output, t5)]
    require(len(allowed) <= 10000, "Finite original public evidence file count required")
    return t5["evidence"].publish_evidence(output, output / "public", allowed,
        secret_record=records[0], token=records[0]["token"], contains_secret=all_original_credentials)
