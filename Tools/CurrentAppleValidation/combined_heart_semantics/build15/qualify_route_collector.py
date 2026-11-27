"""Qualify the route-only attachment collector against retained actual evidence."""
from pathlib import Path
import argparse
import ast
import copy
import hashlib
import json
import stat
import tarfile
import types

NEW = "39cb1d84f78efb922b71dc55ccb371647c90296093e365452b1291ef854aacf6"
OLD = "ed57e0df1b461fe559b8e82af1ad4c1a95e1100802c96fdd87cada9bbd1598a6"
ARCHIVE = "467da5b58ea673206f76a3519566d08545a1fc264d6fc79fc170a8105c4fa373"

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def require(ok, message):
    if not ok:
        raise ValueError(message)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--custody", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    repo, custody, out = map(Path, (args.repo, args.custody, args.out))
    out.mkdir(mode=0o700)
    control = repo / "Tools/CurrentAppleValidation/combined_heart_semantics/build15"
    before = (control / "semantic_link_route_observation.py").read_bytes()
    after = (control / "semantic_link_route_typed_attachments.py").read_bytes()
    require(digest(before) == OLD and digest(after) == NEW, "Collector source changed")
    old_tree, new_tree = ast.parse(before), ast.parse(after)
    function = lambda tree, name: next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    require(ast.dump(function(old_tree, "validate"), include_attributes=False)
            == ast.dump(function(new_tree, "validate"), include_attributes=False), "Outcome validator changed")
    old, new = {}, {}
    exec(compile(old_tree, "<original-route>", "exec"), old)
    exec(compile(new_tree, "<typed-route>", "exec"), new)
    archive = custody / "originals-private.tar.gz"
    require(digest(archive.read_bytes()) == ARCHIVE, "Original custody changed")
    actual = {}
    with tarfile.open(archive, "r:gz") as t:
        for name in ("execution/evidence/linked-ui/private-attachments/manifest.json",
                     "execution/evidence/execution.json"):
            member = t.getmember(name)
            require(member.isfile(), "Original evidence is not regular")
            actual[name] = t.extractfile(member).read()
        execution = json.loads(actual["execution/evidence/execution.json"])
        binding = execution["binding"]
        manifest_raw = actual["execution/evidence/linked-ui/private-attachments/manifest.json"]
        manifest = json.loads(manifest_raw)
        originals = {}
        wanted = ("semantic-source-existing-link-opening_", "semantic-source-menu-navigation_")
        for row in manifest:
            for item in row.get("attachments", []):
                if str(item.get("suggestedHumanReadableName", "")).startswith(wanted):
                    name = item["exportedFileName"]
                    require(Path(name).name == name, "Original path escaped")
                    member = t.getmember("execution/evidence/linked-ui/private-attachments/" + name)
                    require(member.isfile(), "Original attachment is not regular")
                    originals[name] = t.extractfile(member).read()
    original_core = (control / "combined_heart_semantics_replacement.py").read_bytes()
    core_tree = ast.parse(original_core)
    ns = {"Path": Path, "stat": stat, "json": json, "hashlib": hashlib}
    nodes = [function(core_tree, n) for n in ("require", "sha", "raw", "decode")]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<original-core-functions>", "exec"), ns)
    c = types.SimpleNamespace(**{n: ns[n] for n in ("require", "sha", "raw", "decode")})
    policy_source = (repo / "Tools/CurrentAppleValidation/page154_contract.py").read_bytes()
    policy_tree = ast.parse(policy_source)
    pn = {"Path": Path, "require": require,
          "common": types.SimpleNamespace(strict_json=c.decode, read=c.raw, sha=c.sha)}
    exec(compile(ast.Module(body=[function(policy_tree, "attachment")], type_ignores=[]),
                 "<original-attachment-policy>", "exec"), pn)
    policy = types.SimpleNamespace(attachment=pn["attachment"])
    directory = out / "private-actual-attachments"
    directory.mkdir(mode=0o700)
    for name, raw in originals.items():
        (directory / name).write_bytes(raw)
    (directory / "manifest.json").write_bytes(manifest_raw)
    stage = execution["stages"]["linked-ui"]
    selector = stage["selector"]
    device = stage["actual"]["device"]["deviceId"]
    result = {"protocol": "pinkha-typed-route-collector-qualification-v1",
              "collectorSHA256": NEW, "originalCollectorSHA256": OLD,
              "originalExecutionSHA256": digest(actual["execution/evidence/execution.json"]),
              "originalManifestSHA256": digest(manifest_raw),
              "originalCoreSHA256": digest(original_core), "originalPolicySHA256": digest(policy_source),
              "originalOutcomeValidatorASTUnchanged": True, "engineCalls": 0, "testsInvoked": 0,
              "controls": []}
    try:
        old["qualify_routes"](c, policy, directory, selector, device, "linked", binding)
    except ValueError as exc:
        require("bounded regular file required" in str(exc) and str(exc).endswith(".png"),
                "Different original collector failure")
        result["originalCollectorFailureReproduced"] = True
    else:
        raise ValueError("Original collector unexpectedly accepted")
    proof = new["qualify_routes"](c, policy, directory, selector, device, "linked", binding)
    require(proof["realSemanticLinkTaps"] == 2 and proof["firstOriginalNativeMenuActionTaps"] == 1
            and proof["originalScreenshotCount"] == 2, "Actual route proof changed")
    result["actualOriginalAttachmentQualification"] = proof
    result["controls"].append({"name": "actual-two-json-two-png-and-original-menu", "status": "PASS"})
    route_items = [(row, item) for row in manifest for item in row.get("attachments", [])
                   if str(item.get("suggestedHumanReadableName", "")).startswith(wanted[0])]
    json_name = next(item["exportedFileName"] for _, item in route_items
                     if item["exportedFileName"].endswith(".json"))
    png_name = next(item["exportedFileName"] for _, item in route_items
                    if item["exportedFileName"].endswith(".png"))
    menu_name = next(item["exportedFileName"] for row in manifest for item in row.get("attachments", [])
                     if str(item.get("suggestedHumanReadableName", "")).startswith(wanted[1]))
    def control(name, mutate):
        current = copy.deepcopy(manifest)
        for filename, raw in originals.items():
            (directory / filename).write_bytes(raw)
        mutate(current)
        (directory / "manifest.json").write_text(json.dumps(current))
        try:
            new["qualify_routes"](c, policy, directory, selector, device, "linked", binding)
        except (ValueError, KeyError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
            result["controls"].append({"name": name, "status": "PASS_REFUSED", "errorType": type(exc).__name__})
        else:
            raise ValueError("Forged attachment set accepted: " + name)
    def items(m):
        return [item for row in m for item in row.get("attachments", [])
                if str(item.get("suggestedHumanReadableName", "")).startswith(wanted[0])]
    def remove(m, suffix):
        for row in m:
            for i, item in enumerate(row.get("attachments", [])):
                if item["exportedFileName"].endswith(suffix) and item in items(m):
                    row["attachments"].pop(i)
                    return
    control("missing-json", lambda m: remove(m, ".json"))
    control("missing-png", lambda m: remove(m, ".png"))
    control("duplicate-path", lambda m: m[0]["attachments"].append(copy.deepcopy(items(m)[0])))
    control("foreign-device", lambda m: items(m)[0].update(deviceId="00000000-0000-0000-0000-000000000000"))
    control("failure-associated", lambda m: items(m)[0].update(isAssociatedWithFailure=True))
    control("foreign-test", lambda m: m[0].update(testIdentifier="Foreign/testForeign()"))
    control("mismatched-attachment-kind", lambda m: items(m)[0].update(suggestedHumanReadableName="semantic-source-existing-link-opening_0_00000000-0000-0000-0000-000000000000.bin"))
    control("path-escape", lambda m: items(m)[0].update(exportedFileName="../escape.json"))
    control("malformed-png", lambda m: (directory / png_name).write_bytes(b"bad PNG"))
    control("oversized-json", lambda m: (directory / json_name).write_bytes(b" " * 65537))
    def change_json(name, key, value):
        payload = json.loads(originals[name])
        payload[key] = value
        (directory / name).write_text(json.dumps(payload))
    control("foreign-binding", lambda m: change_json(json_name, "nonce", "foreign"))
    control("unknown-route-field", lambda m: change_json(json_name, "untrusted", True))
    control("missing-original-menu-action", lambda m: change_json(menu_name, "sourceActionTaps", 0))
    for filename, raw in originals.items():
        (directory / filename).write_bytes(raw)
    (directory / "manifest.json").write_bytes(manifest_raw)
    result["status"] = "PASS_COLLECTOR_ONLY_NOT_NEW_UI_OR_NATIVE_ACCEPTANCE"
    result["controlCount"] = len(result["controls"])
    (out / "receipt.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "controls": result["controlCount"],
                      "receiptSHA256": digest((out / "receipt.json").read_bytes()),
                      "proof": proof}))

if __name__ == "__main__":
    main()
