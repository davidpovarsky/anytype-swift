import Foundation
import Glibc

private struct Policy: Decodable {
    let archive_max_bytes: Int
    let archive_max_members: Int
    let archive_max_expanded_bytes: Int
    let snapshot_header_max_bytes: Int
    let snapshot_fixed_overhead_bytes: Int
    let snapshot_body_max_bytes: Int
    let unrelated_action_wire_max_bytes_unchanged: Int
}
private struct Inventory: Decodable { let specimens: [Specimen] }
private struct Specimen: Decodable {
    let kind: String
    let bytes: Int
    let members: Int
    let expanded_bytes: Int
    let inventory: [Member]
}
private struct Member: Decodable {
    let path: String
    let bytes: Int
    let compressed_bytes: Int
}
private struct ControlFailure: Error { let reason: String }

@main @MainActor
private struct AnnotationBudgetControls {
    static var assertions = 0
    static var passed: [String] = []

    static func require(_ condition: @autoclosure () -> Bool, _ reason: String) throws {
        assertions += 1
        guard condition() else { throw ControlFailure(reason: reason) }
    }

    static func run(_ name: String, _ body: () throws -> Void) throws {
        let before = assertions
        try body()
        passed.append(name)
        emit(["case": name, "status": "PASS", "assertions": assertions - before])
    }

    static func emit(_ object: [String: Any]) {
        let data = try! JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
        FileHandle.standardOutput.write(data + Data([10]))
    }

    static func main() {
        do {
            guard CommandLine.arguments.count == 3 else {
                throw ControlFailure(reason: "packet and synthetic fixture directories required")
            }
            let packet = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
            let synthetic = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
            let policy = try JSONDecoder().decode(Policy.self, from: Data(contentsOf: packet.appendingPathComponent("ANNOTATION_PAYLOAD_POLICY.json")))
            let inventory = try JSONDecoder().decode(Inventory.self, from: Data(contentsOf: packet.appendingPathComponent("GENUINE_EXPORT_INVENTORY.json")))
            let a = policy.archive_max_bytes
            let h = policy.snapshot_header_max_bytes
            let p = policy.snapshot_fixed_overhead_bytes
            let b = policy.snapshot_body_max_bytes
            let legacy = policy.unrelated_action_wire_max_bytes_unchanged

            try run("canonical-policy-correspondence") {
                try require(OriginalAnnotationPayloadBudget.maximumArchiveBytes == a, "archive policy")
                try require(OriginalAnnotationPayloadBudget.maximumHeaderBytes == h, "header policy")
                try require(OriginalAnnotationPayloadBudget.framePrefixBytes == p, "prefix policy")
                try require(OriginalAnnotationPayloadBudget.maximumBodyBytes == b, "body policy")
                try require(p + h + a == b, "independent policy sum")
                try require(OriginalAnnotationNativeArchiveLayout.maximumEntries == policy.archive_max_members, "member policy unchanged")
                try require(OriginalAnnotationNativeArchiveLayout.maximumExpandedBytes == policy.archive_max_expanded_bytes, "expanded policy unchanged")
            }

            try run("legacy-and-extreme-caller-limits") {
                for value in [legacy, b, p + 1] {
                    try require(OriginalAnnotationPayloadBudget.acceptsBodyLimit(value), "supported explicit caller limit")
                }
                for value in [Int.min, -1, 0, p, b + 1, Int.max] {
                    try require(!OriginalAnnotationPayloadBudget.acceptsBodyLimit(value), "invalid caller limit")
                }
            }

            try run("independent-archive-budget") {
                try require(OriginalAnnotationPayloadBudget.acceptsArchiveBytes(a, maximumBodyBytes: b), "exact archive maximum")
                try require(!OriginalAnnotationPayloadBudget.acceptsArchiveBytes(a + 1, maximumBodyBytes: b), "body headroom cannot enlarge archive")
                try require(!OriginalAnnotationPayloadBudget.acceptsArchiveBytes(Int.max, maximumBodyBytes: b), "extreme archive rejected")
                try require(!OriginalAnnotationPayloadBudget.acceptsArchiveBytes(-1, maximumBodyBytes: b), "negative archive rejected")
                try require(OriginalAnnotationPayloadBudget.acceptsArchiveBytes(legacy, maximumBodyBytes: legacy), "legacy archive comparison")
                try require(!OriginalAnnotationPayloadBudget.acceptsArchiveBytes(legacy + 1, maximumBodyBytes: legacy), "legacy caller remains strict")
            }

            try run("framed-body-header-and-legacy-boundaries") {
                try require(OriginalAnnotationPayloadBudget.acceptsFrame(headerBytes: h, archiveBytes: a, maximumBodyBytes: b), "exact maximum frame")
                try require(!OriginalAnnotationPayloadBudget.acceptsFrame(headerBytes: h, archiveBytes: a, maximumBodyBytes: b - 1), "caller frame one byte too small")
                try require(!OriginalAnnotationPayloadBudget.acceptsFrame(headerBytes: h + 1, archiveBytes: a - 1, maximumBodyBytes: b), "archive reduction cannot enlarge header")
                try require(!OriginalAnnotationPayloadBudget.acceptsFrame(headerBytes: h - 1, archiveBytes: a + 1, maximumBodyBytes: b), "header reduction cannot enlarge archive")
                try require(!OriginalAnnotationPayloadBudget.acceptsFrame(headerBytes: 0, archiveBytes: a, maximumBodyBytes: b), "empty header rejected")
                try require(!OriginalAnnotationPayloadBudget.acceptsFrame(headerBytes: Int.max, archiveBytes: Int.max, maximumBodyBytes: Int.max), "extreme inputs reject before arithmetic")
                let oldHeader = 1_024
                let oldArchive = legacy - p - oldHeader
                try require(OriginalAnnotationPayloadBudget.acceptsFrame(headerBytes: oldHeader, archiveBytes: oldArchive, maximumBodyBytes: legacy), "exact historical caller frame maximum")
                try require(!OriginalAnnotationPayloadBudget.acceptsFrame(headerBytes: oldHeader, archiveBytes: oldArchive + 1, maximumBodyBytes: legacy), "legacy frame one over rejected")
            }

            try require(inventory.specimens.map(\.kind) == ["text", "format", "nested", "attachment"], "four authenticated specimens")
            for specimen in inventory.specimens {
                try run("actual-original-export-layout-" + specimen.kind) {
                    let data = try Data(contentsOf: packet.appendingPathComponent("fixtures/" + specimen.kind + ".zip"))
                    try require(data.count == specimen.bytes, "authenticated archive length")
                    try require(data.count > legacy && data.count <= a, "actual newly admitted byte range")
                    let layout = try OriginalAnnotationNativeArchiveLayout(data)
                    try require(layout.entries.count == specimen.members, "entire original member count")
                    try require(layout.entries.count == specimen.inventory.count, "whole inventory correspondence")
                    try require(layout.entries.reduce(0) { $0 + $1.uncompressedBytes } == specimen.expanded_bytes, "whole expanded count")
                    for (actual, expected) in zip(layout.entries, specimen.inventory) {
                        try require(actual.path == expected.path, "exact original path")
                        try require(actual.pathBytes == Data(expected.path.utf8), "exact path bytes")
                        try require(actual.compressedBytes == expected.compressed_bytes, "original compressed member length")
                        try require(actual.uncompressedBytes == expected.bytes, "original uncompressed member length")
                    }
                }
            }

            try run("synthetic-zip-exact-archive-maximum") {
                let data = try Data(contentsOf: synthetic.appendingPathComponent("exact-limit.zip"))
                try require(data.count == a, "exact generated archive boundary")
                let layout = try OriginalAnnotationNativeArchiveLayout(data)
                try require(layout.entries.count == 1, "one synthetic member")
                try require(layout.entries[0].path == "a", "synthetic member identity")
                try require(layout.entries[0].compressedBytes == a - 100, "ordinary stored ZIP framing overhead")
                try require(layout.entries[0].uncompressedBytes == a - 100, "stored synthetic payload")
            }

            try run("synthetic-zip-one-over-archive-maximum") {
                let data = try Data(contentsOf: synthetic.appendingPathComponent("one-over.zip"))
                try require(data.count == a + 1, "one over generated archive boundary")
                do {
                    _ = try OriginalAnnotationNativeArchiveLayout(data)
                    throw ControlFailure(reason: "one-over archive unexpectedly accepted")
                } catch OriginalAnnotationNativeArchiveLayout.Failure.sizeLimit {
                    try require(true, "actual original size gate rejected")
                }
            }

            emit(["status": "PASS", "scope": "FOUNDATION_BUDGET_AND_ZIP_LAYOUT_ONLY", "passed": passed, "assertions": assertions,
                  "native_body_or_restore_qualified": false, "swift_snapshot_native_modules_compiled": false])
        } catch {
            emit(["status": "FAIL", "passed": passed, "assertions": assertions, "error": String(describing: error)])
            exit(1)
        }
    }
}
