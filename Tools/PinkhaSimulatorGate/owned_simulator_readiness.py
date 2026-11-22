"""Bounded readiness and retirement of an already verified, job-owned simulator.

The boot -> bootstatus(-b, 180s) sequence is the one used by the qualified
Heart iOS host and existing native acceptance controllers. This helper adds
explicit preboot destination identity evidence; it never chooses a device.
Do not repeat CoreSimulator inventory after boot: that redundant query timed
out in the original retained Release run after bootstatus had succeeded.
"""
import json
import re


def inventory(*, app, evidence, pair, name, udid):
    path = evidence / (name + ".json")
    pair.run_logged(["xcrun", "simctl", "list", "devices", udid, "--json"], app, evidence, name, 60, output=path)
    return json.loads(path.read_text(encoding="utf-8"))


def owned_identity(value, selection, expected_name, pair):
    udid = selection.get("udid", "")
    pair.require(re.fullmatch(r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}", udid)
                 and selection.get("name") == expected_name and expected_name,
                 "Explicit owned simulator name and UUID required")
    matches = [(runtime, item) for runtime, devices in value.get("devices", {}).items()
               for item in devices if item.get("udid", "").lower() == udid.lower()]
    pair.require(len(matches) == 1, "Owned simulator is missing or ambiguous")
    runtime, item = matches[0]
    observed = {key: item.get(key) for key in ("udid", "name", "deviceTypeIdentifier", "state", "isAvailable")}
    observed["runtime_identifier"] = runtime
    return validate_identity(observed, selection, expected_name, pair)


def validate_identity(item, selection, expected_name, pair):
    pair.require(selection.get("name") == expected_name and expected_name
                 and item.get("udid", "").lower() == selection["udid"].lower()
                 and item.get("runtime_identifier") == selection["runtime"]["identifier"]
                 and item.get("deviceTypeIdentifier") == selection["device"]["identifier"]
                 and item.get("name") == expected_name and item.get("isAvailable") is True
                 and item.get("state") in {"Shutdown", "Booted"},
                 "Actual simulator type, runtime, name, availability or stable state differs")
    return item


def ensure_ready(*, app, evidence, selection, expected_name, pair, require_initial_shutdown=False):
    """Do not start test discovery until the exact owned destination is ready."""
    evidence.mkdir(parents=True, exist_ok=False)
    receipt = dict(status="RUNNING", tests_executed=0, boot_timeout_seconds=120,
                   bootstatus_timeout_seconds=180, destination=selection["udid"],
                   postboot_inventory_performed=False, actual_xcresult_destination_validation="REQUIRED")
    try:
        before = inventory(app=app, evidence=evidence, pair=pair, name="before", udid=selection["udid"])
        receipt["before"] = owned_identity(before, selection, expected_name, pair)
        pair.require(not require_initial_shutdown or receipt["before"]["state"] == "Shutdown",
                     "Freshly created native-account destination must start Shutdown")
        receipt["preboot_identity_sha256"] = pair.digest(evidence / "before.json")
        udid = selection["udid"]
        receipt["boot_required"] = receipt["before"]["state"] == "Shutdown"
        if receipt["boot_required"]:
            pair.run_logged(["xcrun", "simctl", "boot", udid], app, evidence, "boot", 120)
        observed, log = pair.run_logged(["xcrun", "simctl", "bootstatus", udid, "-b"], app, evidence, "boot-status", 180)
        pair.require(observed.get("return_code") == 0 and not observed.get("timed_out"),
                     "Actual owned bootstatus did not complete successfully")
        receipt.update(status="OWNED_SIMULATOR_READY", bootstatus_return_code=observed["return_code"],
                       bootstatus_log_sha256=pair.digest(log),
                       readiness_basis="VERIFIED_PREBOOT_IDENTITY_AND_SUCCESSFUL_OWNED_BOOTSTATUS")
        return receipt
    except BaseException as error:
        receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL",
                       error_type=type(error).__name__, error=str(error))
        raise
    finally:
        pair.write(evidence / "readiness.json", receipt)


def shutdown_owned(*, app, evidence, selection, expected_name, pair, readiness_receipt_path):
    """Use the same verified ownership receipt and record only actual command success."""
    evidence.mkdir(parents=True, exist_ok=False)
    receipt = dict(status="RUNNING", destination=selection["udid"], final_state_inventory_performed=False,
                   observed_final_state="NOT_QUERIED")
    try:
        pair.require(readiness_receipt_path.is_file() and not readiness_receipt_path.is_symlink()
                     and readiness_receipt_path.stat().st_size <= 64 * 1024,
                     "The same validated ownership/readiness receipt is required for shutdown")
        ownership = json.loads(readiness_receipt_path.read_text(encoding="utf-8"))
        pair.require(ownership.get("destination") == selection["udid"] and isinstance(ownership.get("before"), dict)
                     and re.fullmatch("[0-9a-f]{64}", ownership.get("preboot_identity_sha256", "")),
                     "Shutdown ownership receipt lacks the verified exact preboot identity")
        receipt["validated_ownership"] = validate_identity(ownership["before"], selection, expected_name, pair)
        receipt["readiness_receipt_sha256"] = pair.digest(readiness_receipt_path)
        outcome, log = pair.run_logged(["xcrun", "simctl", "shutdown", selection["udid"]], app, evidence,
                                      "shutdown", 120, check=False)
        receipt.update(command_return_code=outcome.get("return_code"), command_timed_out=outcome.get("timed_out", False),
                       command_log_sha256=pair.digest(log))
        pair.require(outcome.get("return_code") == 0 and not outcome.get("timed_out"),
                     "Owned simulator shutdown command failed or timed out")
        receipt["status"] = "OWNED_SIMULATOR_SHUTDOWN_COMMAND_SUCCEEDED"
        return receipt
    except BaseException as error:
        receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL",
                       error_type=type(error).__name__, error=str(error))
        raise
    finally:
        pair.write(evidence / "shutdown.json", receipt)
