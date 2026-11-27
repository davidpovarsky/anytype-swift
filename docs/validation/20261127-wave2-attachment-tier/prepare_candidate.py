from __future__ import annotations

import base64
import difflib
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BASE = "bd684a8ad5b12cc2eef3b14d4fb64a34bd98f304"
PRODUCT = "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeAttachments.swift"
TESTS = "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeAttachmentMetadataTests.swift"
EXPECTED = {
    PRODUCT: "75cac2b2b7ffe0d84e0f461d80c94e3be48d804896170a2b67e895e006977631",
    TESTS: "b9d0f1b8c72e503d4e4952b33f519fc93680d54a8384e828f001d498ddd71a91",
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"Expected exactly one source anchor: {old!r}")
    return text.replace(old, new, 1)


ADDITION = '''    @Test
    func validStorageTiersRetainRawRootAndAllowAvailabilityProgress() throws {
        let inlineWithoutRoot = try AnyNativeAttachment(row([
            "inline": .bool(true), "cached": .bool(true), "durable": .bool(true)
        ], omitting: ["rootCid", "name", "mime"]), objectID: "doc-1")
        let inlineWithEmptyRoot = try AnyNativeAttachment(row([
            "inline": .bool(true), "cached": .bool(true), "durable": .bool(true),
            "rootCid": .string("")
        ], omitting: ["name", "mime"]), objectID: "doc-1")
        #expect(inlineWithoutRoot.inline && inlineWithoutRoot.cached && inlineWithoutRoot.durable)
        #expect(inlineWithoutRoot.rootCID == nil)
        #expect(inlineWithEmptyRoot.inline && inlineWithEmptyRoot.rootCID == "")
        #expect(inlineWithoutRoot.name.isEmpty && inlineWithEmptyRoot.name.isEmpty)
        #expect(inlineWithoutRoot.mime == "application/octet-stream")
        #expect(inlineWithEmptyRoot.mime == "application/octet-stream")

        let full = try AnyNativeAttachment(row(), objectID: "doc-1")
        #expect(!full.inline && full.rootCID == "root-one")
        #expect(!full.sameContent(as: inlineWithoutRoot))
        for (cached, durable) in [(false, false), (true, false), (false, true), (true, true)] {
            let progressed = try AnyNativeAttachment(row([
                "cached": .bool(cached), "durable": .bool(durable)
            ]), objectID: "doc-1")
            #expect(!progressed.inline)
            #expect(progressed.cached == cached && progressed.durable == durable)
            #expect(full.sameContent(as: progressed), "Availability and backup progress must not change content identity")
        }
        let rawRoot = "root-Original-Case"
        let preserved = try AnyNativeAttachment(row(["rootCid": .string(rawRoot)]), objectID: "doc-1")
        #expect(preserved.rootCID?.utf8.elementsEqual(rawRoot.utf8) == true)
    }

    @Test(arguments: ["missing-inline", "null-inline", "wrong-inline", "inline-with-root", "inline-not-cached", "inline-not-durable", "full-missing-root", "full-empty-root", "null-root", "wrong-root"])
    func missingMalformedOrContradictoryTierMetadataIsRejected(invalidCase: String) throws {
        var fields = try #require(row().object)
        switch invalidCase {
        case "missing-inline": fields.removeValue(forKey: "inline")
        case "null-inline": fields["inline"] = .null
        case "wrong-inline": fields["inline"] = .string("false")
        case "inline-with-root":
            fields["inline"] = .bool(true); fields["durable"] = .bool(true)
        case "inline-not-cached":
            fields["inline"] = .bool(true); fields["cached"] = .bool(false)
            fields["durable"] = .bool(true); fields.removeValue(forKey: "rootCid")
        case "inline-not-durable":
            fields["inline"] = .bool(true); fields.removeValue(forKey: "rootCid")
        case "full-missing-root": fields.removeValue(forKey: "rootCid")
        case "full-empty-root": fields["rootCid"] = .string("")
        case "null-root": fields["rootCid"] = .null
        case "wrong-root": fields["rootCid"] = .integer(3)
        default: Issue.record("Unknown finite attachment tier fixture"); return
        }
        #expect(throws: AnyHostError.invalidDocument("native attachment metadata")) {
            try AnyNativeAttachment(.object(fields), objectID: "doc-1")
        }
    }

'''


def main() -> None:
    originals = {path: (ROOT / "source" / path).read_bytes() for path in EXPECTED}
    for path, raw in originals.items():
        if sha(raw) != EXPECTED[path]:
            raise ValueError(f"Wrong immutable preimage: {path}")

    product = originals[PRODUCT].decode()
    product = replace_once(product, "    let rootCID: String?\n    let cached: Bool\n", "    let rootCID: String?\n    let inline: Bool\n    let cached: Bool\n")
    product = replace_once(product, '        let mime = value["mime"]?.string ?? ""\n', '        let mime = value["mime"]?.string ?? ""\n        let rootCID = value["rootCid"]?.string\n')
    product = replace_once(product, '              let cached = value["cached"]?.bool, let durable = value["durable"]?.bool,\n', '              let inline = value["inline"]?.bool,\n              let cached = value["cached"]?.bool, let durable = value["durable"]?.bool,\n')
    product = replace_once(product, '              mime.utf8.count <= 1_024 else {\n', '              mime.utf8.count <= 1_024,\n              value["rootCid"] == nil || rootCID != nil,\n              (inline\n                ? (rootCID ?? "").isEmpty && cached && durable\n                : !(rootCID ?? "").isEmpty) else {\n')
    product = replace_once(product, '        rootCID = value["rootCid"]?.string\n        self.cached = cached; self.durable = durable\n', '        self.rootCID = rootCID; self.inline = inline\n        self.cached = cached; self.durable = durable\n')
    product = replace_once(product, '        mime == other.mime && size == other.size && rootCID == other.rootCID\n', '        mime == other.mime && size == other.size && rootCID == other.rootCID && inline == other.inline\n')
    product = replace_once(product, '              row.objectID.utf8.elementsEqual(intent.objectID.utf8), row.size == file.byteCount,\n', '              row.objectID.utf8.elementsEqual(intent.objectID.utf8), row.size == file.byteCount,\n              row.inline == file.inline,\n')

    tests = originals[TESTS].decode()
    helper = '    private func row(_ overrides: [String: AnyJSON] = [:], omitting: [String] = []) -> AnyJSON {\n'
    original_methods = tests[:tests.index(helper)]
    tests = replace_once(tests, helper, ADDITION + helper)
    tests = replace_once(tests, '            "cached": .bool(true), "durable": .bool(false), "rootCid": .string("root-one"),\n', '            "inline": .bool(false),\n            "cached": .bool(true), "durable": .bool(false), "rootCid": .string("root-one"),\n')
    assert tests.startswith(original_methods)

    candidates = {PRODUCT: product.encode(), TESTS: tests.encode()}
    patch = []
    files = []
    for path, after in candidates.items():
        before = originals[path]
        target = ROOT / "candidate" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(after)
        old_lines, new_lines = before.splitlines(keepends=True), after.splitlines(keepends=True)
        old_offsets = [0]
        new_offsets = [0]
        for line in old_lines: old_offsets.append(old_offsets[-1] + len(line))
        for line in new_lines: new_offsets.append(new_offsets[-1] + len(line))
        spans = []
        for tag, a, b, c, d in difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False).get_opcodes():
            if tag == "equal": continue
            spans.append({"originalOffset": old_offsets[a], "candidateOffset": new_offsets[c], "originalBase64": base64.b64encode(b"".join(old_lines[a:b])).decode(), "candidateBase64": base64.b64encode(b"".join(new_lines[c:d])).decode()})
        restored = after
        for span in reversed(spans):
            at = span["candidateOffset"]
            selected = base64.b64decode(span["candidateBase64"])
            assert restored[at:at + len(selected)] == selected
            restored = restored[:at] + base64.b64decode(span["originalBase64"]) + restored[at + len(selected):]
        assert restored == before
        files.append({"path": path, "original": {"bytes": len(before), "sha256": sha(before), "gitBlob": blob(before)}, "candidate": {"bytes": len(after), "sha256": sha(after), "gitBlob": blob(after)}, "inverse": spans})
        patch.extend(difflib.unified_diff(before.decode().splitlines(keepends=True), after.decode().splitlines(keepends=True), fromfile="a/" + path, tofile="b/" + path))
    (ROOT / "source.patch").write_text("".join(patch))
    (ROOT / "source-inverse.json").write_text(json.dumps({"status": "PASS_LOCAL_EXACT_SOURCE_INVERSES_ONLY", "baseCommit": BASE, "files": files}, indent=2) + "\n")
    manifest = {"status": "SOURCE_CANDIDATE_NOT_COMPILED_NOT_RUN", "baseCommit": BASE, "baseTree": "42049d3ea1d63f80d29f1b894407ab4cf2fe97fc", "files": [{k: v for k, v in file.items() if k != "inverse"} for file in files], "metadataSuite": {"oldMethods": 3, "oldDeclaredCases": 13, "originalMethodPrefixBytes": len(original_methods.encode()), "originalMethodPrefixSHA256": sha(original_methods.encode()), "originalMethodPrefixUnchanged": True, "addedMethods": 2, "addedDeclaredCases": 11, "resultingMethods": 5, "resultingDeclaredCases": 24, "actualEnumeration": None, "actualResults": None}, "changesToPackagePBXOriginAllowlistProducer": False, "compiler": False, "native": False, "appleUI": False}
    (ROOT / "candidate-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (ROOT / "new-test-methods.swift").write_text(ADDITION)
    print(json.dumps({"files": [{"path": f["path"], **f["candidate"]} for f in files], "inverseSHA256": sha((ROOT / "source-inverse.json").read_bytes()), "manifestSHA256": sha((ROOT / "candidate-manifest.json").read_bytes()), "originalMethodsPrefix": manifest["metadataSuite"], "newMethodsSHA256": sha(ADDITION.encode())}, indent=2))


if __name__ == "__main__":
    main()
