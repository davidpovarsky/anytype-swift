"""Repair unsigned Pinkha IPA extension identifiers without rebuilding app or Heart.

The original fast packager rebranded the parent bundle ID but retained upstream
extension IDs. iOS requires every PlugIns/*.appex ID to start with parent ID + '.'.
This rewrites only extension Info.plist entries and preserves all binaries.
"""
import argparse
import hashlib
import json
import plistlib
import re
import shutil
import zipfile
from pathlib import Path

EXPECTED_PARENT = "com.gloiiire.anytype.torahtrial"
APP_INFO = re.compile(r"^Payload/[^/]+\\.app/Info\\.plist$")
EXT_INFO = re.compile(r"^Payload/[^/]+\\.app/PlugIns/([^/]+)\\.appex/Info\\.plist$")


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as src:
        for block in iter(lambda: src.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def retarget(original: Path, output: Path, receipt: Path):
    original, output, receipt = original.resolve(), output.resolve(), receipt.resolve()
    if output == original or output.exists():
        raise RuntimeError("Refuse to overwrite the input or an existing output IPA")
    output.parent.mkdir(parents=True, exist_ok=True)
    replacements = {}
    conversions = []
    with zipfile.ZipFile(original) as src:
        names = src.namelist()
        if len(names) != len(set(names)):
            raise RuntimeError("Duplicate ZIP paths")
        roots = [name for name in names if APP_INFO.fullmatch(name)]
        if len(roots) != 1:
            raise RuntimeError("Expected exactly one top-level .app")
        parent = plistlib.loads(src.read(roots[0]))
        if parent.get("CFBundleIdentifier") != EXPECTED_PARENT:
            raise RuntimeError("Source IPA has wrong parent bundle ID")
        if not parent.get("PinkhaNativeHeartMarker") or not parent.get("PinkhaNativeAppCommit"):
            raise RuntimeError("Original custom-Heart provenance missing")
        if any("/_CodeSignature/" in name for name in names):
            raise RuntimeError("Source IPA contains signatures; only unsigned IPA supported")
        used = {EXPECTED_PARENT}
        for path in names:
            match = EXT_INFO.fullmatch(path)
            if not match:
                continue
            props = plistlib.loads(src.read(path))
            previous = props.get("CFBundleIdentifier")
            if not isinstance(previous, str):
                raise RuntimeError("Extension is missing a bundle identifier: " + path)
            if previous.startswith(EXPECTED_PARENT + "."):
                suffix = previous[len(EXPECTED_PARENT)+1:]
            elif previous.startswith("io.anytype.app."):
                suffix = previous[len("io.anytype.app."):]
            elif previous == EXPECTED_PARENT:
                suffix = match.group(1)
            else:
                raise RuntimeError("Unexpected pre-signing extension ID: " + previous)
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", suffix) or ".." in suffix:
                raise RuntimeError("Invalid extension suffix: " + suffix)
            updated = EXPECTED_PARENT + "." + suffix
            if updated in used:
                raise RuntimeError("Duplicate extension ID: " + updated)
            used.add(updated)
            if updated != previous:
                props["CFBundleIdentifier"] = updated
                replacements[path] = plistlib.dumps(props, fmt=plistlib.FMT_BINARY)
            conversions.append({"extension": path, "from": previous, "to": updated})
        if not conversions:
            raise RuntimeError("No PlugIns .appex bundles found in source")
        with zipfile.ZipFile(output, "w", allowZip64=True) as dest:
            dest.comment = src.comment
            for entry in src.infolist():
                if entry.filename in replacements:
                    dest.writestr(entry, replacements[entry.filename])
                else:
                    with src.open(entry) as incoming, dest.open(entry, "w", force_zip64=True) as outgoing:
                        shutil.copyfileobj(incoming, outgoing, length=1024 * 1024)
    with zipfile.ZipFile(original) as original_zip, zipfile.ZipFile(output) as fixed:
        if fixed.testzip() is not None:
            raise RuntimeError("Corrupted repaired IPA")
        if set(original_zip.namelist()) != set(fixed.namelist()):
            raise RuntimeError("Repaired IPA member inventory changed")
        for name in original_zip.namelist():
            if name not in replacements and original_zip.getinfo(name).CRC != fixed.getinfo(name).CRC:
                raise RuntimeError("Unexpected changed member: " + name)
        for entry in conversions:
            actual = plistlib.loads(fixed.read(entry["extension"]))["CFBundleIdentifier"]
            if actual != entry["to"] or not actual.startswith(EXPECTED_PARENT + "."):
                raise RuntimeError("Bad fixed extension ID")
    result = {
        "status": "PASS",
        "scope": "unsigned IPA metadata repair only",
        "original_sha256": sha256(original),
        "repaired_sha256": sha256(output),
        "parent_bundle_id": EXPECTED_PARENT,
        "app_sha": parent["PinkhaNativeAppCommit"],
        "heart_marker": parent["PinkhaNativeHeartMarker"],
        "extensions": conversions,
        "changed_plists": len(replacements),
        "all_other_bundle_members_unchanged": True,
        "binaries_rebuilt": False,
        "signed": False,
        "physical_ipad_install_verified": False
    }
    receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    retarget(args.input, args.output, args.receipt)
