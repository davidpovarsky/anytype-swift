#!/usr/bin/env python3
"""Retain the five unchanged product-identity controls from their original run."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/validation/20261122-any-native-entry-failure"
SOURCE_SHA256 = {
    "Tools/AnyEnginePort/verify_custom_type.py": "217c77248f4b448971c1c6e30bb87714c7de4631a9a0f54d0ffeeec2e827b99a",
    "Tools/AnyEnginePort/test_compiled_product_identity.py": "9e6c2e4931ed7be365b2dc6d2ed0ee38ce219fe2a68e5e4411c9ab18317e45e4",
    "Tools/AnyEnginePort/verify_native_test_execution.py": "cc768d66aaee9081f8ff0c882b7dd15eca1625454e324e03f07a257c1ee56575",
    "Tools/AnyEnginePort/verify_archive_roundtrip.py": "5573eefcbf9eae9eea905210d15726ce7684f5529766531d4926eda39c7e2f29",
}
ZIP_SHA256 = "e3cd373b2e444bf6216b1847c57e4da023b13b1080cf99f3562efaf59ce12d83"
LOG_SHA256 = "8d5bfa21bd3b648b299b18571fd9e6029f6a60f09164fd3794e36b2d579d3036"


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def verify(root=ROOT, evidence=EVIDENCE):
    for path, expected in SOURCE_SHA256.items():
        require(digest((root / path).read_bytes()) == expected,
                "Changed control source requires new execution: " + path)
    archive = evidence / "original-failure-evidence.zip"
    require(digest(archive.read_bytes()) == ZIP_SHA256, "Original selected evidence changed")
    with zipfile.ZipFile(archive) as zipped:
        require(len(zipped.namelist()) == len(set(zipped.namelist())), "Duplicate original evidence members")
        log = zipped.read("compiled-product-identity-controls.log")
    require(digest(log) == LOG_SHA256, "Original control execution log changed")
    text = log.decode("utf-8")
    methods = re.findall(r"^(test_[a-z0-9_]+) \([^\n]+\) \.\.\. ok$", text, re.M)
    require(len(methods) == len(set(methods)) == 5 and re.search(r"\nRan 5 tests in [0-9.]+s\n\nOK\n\Z", text),
            "Original five controls did not finish successfully")
    return dict(schemaVersion=1, status="RETAINED_ORIGINAL_CONTROL_EXECUTION",
        originalRunID="45031455896", originalCommit="ef06a2c438104d1b47a715319bb78d31348edc04",
        originalArtifactSHA256="cb5275f3497c6b8580462e43dc69dca52bce1a819757005b49fda2136b2cb974",
        selectedEvidenceZIP_SHA256=ZIP_SHA256, originalLogSHA256=LOG_SHA256,
        sourceSHA256=SOURCE_SHA256, methods=sorted(methods), originalPassed=5, originalFailed=0,
        originalSkipped=0, methodsExecutedAgain=0, actualBuildAdmission="SEPARATE_REQUIRED_GATE",
        nativeUIAcceptance="NOT_PROVEN_BY_CONTROL_REUSE")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
