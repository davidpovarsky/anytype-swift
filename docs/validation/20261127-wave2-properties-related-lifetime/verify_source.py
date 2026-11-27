#!/usr/bin/env python3
"""Local byte custody only; this script does not compile or run Swift."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
BASE = "d8a2c67b6dae09a7b769e803a319de3d3080019c"
DOC = "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyDocumentPresentation.swift"
VIEW = "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativePropertiesView.swift"
TEST = "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTorahRelatedIdentityTests.swift"
MODEL = "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeSourceDocumentsPresentation.swift"
PREIMAGES = {
    DOC: ("f9cc5b324ec9e3d965aac5ea185beb7a1296c08a", "422eed9e20b72f673e7b2b3fed303a314c2bd402ae2fd3cf74bd2d4f7727b67a"),
    VIEW: ("24cd3e10f410977bec1ab137a93455ac78e403fe", "1e7f81384ba53a9b136056866a65667ff3537eb21883e249f7cdfe79b2d5ae3c"),
    TEST: ("5c2f413005d9e2252f97f6a6b3b46f5f7c81d14d", "af7e3270f8b29d56ade52603e648d2ef36bb6a07dfea8bc07b9d7c2d448d8095"),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def native_body(data):
    source = data.decode()
    method = source.split("    public func showDocuments(with item:", 1)[1]
    start = method.index("            let output = try await nativeSession.perform { lease in\n")
    end = method.index("                return (rows, final.readiness.complete)\n            }\n", start)
    end += len("                return (rows, final.readiness.complete)\n            }\n")
    return method[start:end].encode()


def main():
    old = {}
    current = {}
    records = []
    changes = []
    for relative in [DOC, VIEW, TEST, MODEL]:
        before = (ROOT / "source" / relative).read_bytes() if relative in PREIMAGES else b""
        after = (ROOT / "candidate" / relative).read_bytes()
        assert before != after
        if relative in PREIMAGES:
            expected_blob, expected_sha = PREIMAGES[relative]
            assert blob(before) == expected_blob and sha(before) == expected_sha
        old[relative] = before
        current[relative] = after
        records.append({"path": relative, "originalGitBlob": blob(before) if before else None,
                        "originalSHA256": sha(before) if before else None,
                        "candidateGitBlob": blob(after), "candidateSHA256": sha(after),
                        "originalBytes": len(before), "candidateBytes": len(after)})
        changes.extend(difflib.unified_diff(before.decode().splitlines(keepends=True),
                        after.decode().splitlines(keepends=True),
                        fromfile="a/" + relative if before else "/dev/null",
                        tofile="b/" + relative))

    patch = "".join(changes).encode()
    (ROOT / "source.patch").write_bytes(patch)
    assert native_body(old[DOC]) == native_body(current[DOC])
    assert current[TEST].startswith(old[TEST])
    test_suffix = current[TEST][len(old[TEST]):]
    (ROOT / "test-suffix.swift").write_bytes(test_suffix)
    proof_root = ROOT / "inverse-check-v3"
    assert not proof_root.exists(), "Keep each original proof attempt; choose a new attempt directory for a successor"
    shutil.copytree(ROOT / "candidate", proof_root)
    argv = ["git", "apply", "--reverse", str(ROOT / "source.patch")]
    result = subprocess.run(argv, cwd=proof_root, capture_output=True, check=False)
    (ROOT / "inverse-command.json").write_text(json.dumps({"argv": argv, "cwd": str(proof_root),
        "exitCode": result.returncode, "stdout": result.stdout.decode(), "stderr": result.stderr.decode()}, indent=2) + "\n")
    assert result.returncode == 0, result.stderr.decode()
    for relative in PREIMAGES:
        assert (proof_root / relative).read_bytes() == old[relative]
    assert not (proof_root / MODEL).exists()
    assert sorted(str(p.relative_to(proof_root)) for p in proof_root.rglob("*") if p.is_file()) == sorted(PREIMAGES)
    proof = {
        "schema": "wave2-source-documents-publication-inverse/v1",
        "status": "PASS_SOURCE_BYTE_INVERSE_ONLY",
        "baseCommit": BASE,
        "files": records,
        "patchSHA256": sha(patch),
        "nativeReadBody": {"unchanged": True, "sha256": sha(native_body(old[DOC])),
                           "bytes": len(native_body(old[DOC])),
                           "scope": "original typed query, metadata, second query/readiness comparison and lease validation"},
        "tests": {"originalPrefixBytes": len(old[TEST]), "originalPrefixSHA256": sha(old[TEST]),
                  "originalMethods": 5, "originalDeclaredCases": 7,
                  "newSuffixSHA256": sha(test_suffix), "newSuffixBytes": len(test_suffix),
                  "newSuite": "AnyNativeSourceDocumentsPublicationTests",
                  "newMethods": 5, "newDeclaredCases": 11,
                  "execution": "NOT_RUN", "typecheck": "NOT_RUN"},
        "newModelAbsentFromOriginal": True,
        "fullInverseRestoredAllOriginalBytes": True,
        "productRuntimeAdmission": False,
        "operations": {"oracle": 0, "mac": 0, "compiler": 0, "native": 0, "simulator": 0, "xctest": 0},
    }
    output = (json.dumps(proof, indent=2) + "\n").encode()
    (ROOT / "source-inverse.json").write_bytes(output)
    print(json.dumps({"status": proof["status"], "proofSHA256": sha(output), "files": records,
                      "nativeReadBody": proof["nativeReadBody"], "tests": proof["tests"]}, indent=2))


if __name__ == "__main__":
    main()
