"""Admit original simulator entitlements without changing any compiled product."""
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess
from simulator_entitlements import read_simulator_entitlements


def require(value, message):
    if not value:
        raise RuntimeError(message)


def verify_built_entitlements(app, built, executable, owner, evidence, stage):
    origin_path = Path(__file__).with_name("simulator-entitlements-origin.json")
    origin = json.loads(origin_path.read_text())
    reader = Path(__file__).with_name("simulator_entitlements.py")
    require(hashlib.sha256(reader.read_bytes()).hexdigest() == origin["sha256"],
            "The admitted simulator reader differs from the frozen original")
    require(origin["revision"] == "a774de24926ca13d563c45c42917d03b8c04296f"
            and origin["copy_policy"] == "EXACT_BYTES", "Unexpected simulator reader provenance")
    verification = subprocess.run(["codesign", "--verify", "--strict", str(built)],
        capture_output=True, text=True, timeout=120)
    (evidence / (stage + "-codesign-verify.log")).write_text(verification.stdout + verification.stderr)
    require(verification.returncode == 0, "The original app signature did not verify")
    signature = subprocess.run(["codesign", "-d", "--entitlements", ":-", str(built)],
        capture_output=True, check=True, timeout=120)
    signed_entitlements = plistlib.loads(signature.stdout)
    require(isinstance(signed_entitlements, dict), "The actual signature entitlement plist is invalid")
    embedded = read_simulator_entitlements(Path(executable))
    entitlements = embedded["entitlements"]
    source = app / "Config/Signing/AnytypeOwner.entitlements"
    expected = plistlib.loads(source.read_bytes())
    expected["com.apple.security.application-groups"] = [
        value.replace("$(PINKHA_NATIVE_APP_GROUP)", owner["native_app_group"])
        for value in expected["com.apple.security.application-groups"]]
    require(entitlements.get("application-identifier") ==
            owner["team_id"] + "." + owner["bundle_ids"]["Anytype"], "Actual simulator application identity differs")
    for key, value in expected.items():
        require(entitlements.get(key) == value, "Actual simulator entitlement differs from its source: " + key)
    require(set(entitlements["com.apple.security.application-groups"]) ==
            {owner["native_app_group"], owner["shared_app_group"]}, "Actual simulator groups differ")
    for key in signed_entitlements.keys() & entitlements.keys():
        require(signed_entitlements[key] == entitlements[key], "Signature and embedded entitlement disagree: " + key)
    proof = {"status": "ORIGINAL_SIMULATOR_SIGNATURE_AND_ENTITLEMENTS_VERIFIED",
        "signature_verification": "CODESIGN_VERIFY_STRICT_PASS", "signature_entitlements": signed_entitlements,
        "embedded": embedded, "reader_origin": origin, "source_entitlements": expected,
        "source_entitlements_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "os_container_admission": "REQUIRED_BY_ACTUAL_NATIVE_AND_UI_TESTS_NOT_YET_EXECUTED",
        "apple_profile_grants": owner["status"], "physical_sharing": "NOT_PROVEN_BY_SIMULATOR"}
    (evidence / (stage + "-entitlements.json")).write_text(json.dumps(proof, indent=2) + "\n")
    return proof
