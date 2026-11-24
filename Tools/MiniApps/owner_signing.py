"""Verify the separate owner configuration without changing upstream defaults."""
import hashlib
import json
from pathlib import Path
import plistlib
import re

CONFIGURATION_PATTERN = re.compile(
    r"^\t\t([A-F0-9]{24}) /\* [^\n*]+ \*/ = \{\n\t\t\tisa = XCBuildConfiguration;.*?^\t\t\};",
    re.M | re.S)

def require(value, message):
    if not value:
        raise RuntimeError(message)

def verify_original_configurations(app):
    proof = json.loads((app / "Tools/MiniApps/original-configurations.json").read_text())
    for relative, original in proof["projects"].items():
        blocks = {m[1]: m[0] for m in CONFIGURATION_PATTERN.finditer((app / relative).read_text())}
        require(all(key in blocks for key in original["configuration_ids"]), "An original build configuration disappeared")
        raw = "\0".join(blocks[key] for key in original["configuration_ids"]).encode()
        require(hashlib.sha256(raw).hexdigest() == original["sha256"], "An original build configuration changed")
    return proof

def verify(app, *, require_profile_grants=True):
    app = Path(app)
    owner = json.loads((app / "Tools/MiniApps/owner-signing.json").read_text())
    require(owner["schema_version"] == 1 and owner["status"] in {"PENDING_APPLE_GRANT", "VERIFIED_OWNER_GROUPS"},
            "The owner group declaration is incomplete")
    if require_profile_grants:
        require(owner["status"] == "VERIFIED_OWNER_GROUPS" and str(owner["profile_evidence_run_id"]).isdigit(),
                "Signed/device qualification requires the authoritative Apple profile grant receipt")
    native = owner["native_app_group"]
    require(isinstance(native, str) and native.startswith("group.") and native != owner["shared_app_group"],
            "The owner native storage group declaration is invalid")
    settings = dict(re.findall(r"^([A-Z_]+)\s*=\s*([^\n]*)$",
        (app / "Config/Signing/MiniAppsOwner.xcconfig").read_text(), re.M))
    expected = {"PINKHA_OWNER_TEAM_ID": owner["team_id"], "PINKHA_NATIVE_APP_GROUP": native}
    targets = {"APP": "Anytype", "SHARE": "AnytypeShareExtension",
               "NOTIFICATION": "AnytypeNotificationServiceExtension", "WIDGET": "AnytypeWidgetExtension"}
    expected.update({"PINKHA_OWNER_" + key + "_BUNDLE_ID": owner["bundle_ids"][target]
                     for key, target in targets.items()})
    require(all(settings.get(key) == value for key, value in expected.items()), "Owner build settings differ from the declared owner configuration")
    for filename in ("AnytypeOwner.entitlements", "AnytypeShareOwner.entitlements", "AnytypeNotificationOwner.entitlements"):
        values = plistlib.loads((app / "Config/Signing" / filename).read_bytes())
        groups = [value.replace("$(PINKHA_NATIVE_APP_GROUP)", native)
                  for value in values["com.apple.security.application-groups"]]
        required = [native, owner["shared_app_group"]] if filename == "AnytypeOwner.entitlements" else [native]
        require(groups == required, "Owner entitlement groups differ from the declared owner configuration")
    for filename in ("Anytype/Supporting files/Info.plist", "AnytypeShareExtension/Info.plist",
                     "AnytypeNotificationServiceExtension/Info.plist"):
        values = plistlib.loads((app / filename).read_bytes())
        require(values["PinkhaNativeAppGroup"] == "$(PINKHA_NATIVE_APP_GROUP)", "Native group declaration is missing from a host bundle")
    verify_original_configurations(app)
    return owner
