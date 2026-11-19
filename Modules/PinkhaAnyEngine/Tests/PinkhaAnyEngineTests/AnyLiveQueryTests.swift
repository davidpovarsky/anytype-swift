import Foundation
import XCTest
@testable import PinkhaAnyEngine

final class AnyLiveQueryTests: XCTestCase {
    private func frame(_ event: String, _ value: AnyJSON) throws -> AnySSEFrame {
        .init(event: event, data: try JSONEncoder().encode(value))
    }

    private func initial(_ values: [AnyJSON]) throws -> AnySSEFrame {
        try frame("snapshot", .object([
            "records": .array(values), "total": .integer(Int64(values.count)), "hasNext": .bool(false)
        ]))
    }

    func testEveryByteBoundaryPreservesHebrewUTF8AndCRLF() throws {
        let bytes = Data("\u{feff}: heartbeat\r\nevent: snapshot\r\ndata: {\"name\":\"תורה\"}\r\n\r\n".utf8)
        for boundary in 0...bytes.count {
            var parser = AnySSEParser()
            let first = try parser.feed(bytes.prefix(boundary))
            let rest = try parser.feed(bytes.suffix(bytes.count - boundary))
            XCTAssertEqual(first + rest, [
                .init(event: "snapshot", data: Data("{\"name\":\"תורה\"}".utf8))
            ])
            try parser.finish()
        }
    }

    func testMultilineDataAndKeepaliveComments() throws {
        var parser = AnySSEParser()
        let values = try parser.feed(Data(": keepalive\n\nevent: changes\ndata: [\ndata: ]\n\n".utf8))
        XCTAssertEqual(values, [.init(event: "changes", data: Data("[\n]".utf8))])
    }

    func testInvalidUTF8AndUnterminatedFrameFailClosed() throws {
        var bad = AnySSEParser()
        XCTAssertThrowsError(try bad.feed(Data([0x64, 0x61, 0x74, 0x61, 0x3a, 0xc3, 0x28, 0x0a]))) {
            XCTAssertEqual($0 as? AnyLiveQueryError, .invalidUTF8)
        }
        var truncated = AnySSEParser()
        _ = try truncated.feed(Data("event: snapshot\ndata: {}".utf8))
        XCTAssertThrowsError(try truncated.finish())
    }

    func testOversizedFrameIsRejectedAcrossChunks() throws {
        var parser = AnySSEParser(maximumFrameBytes: 12)
        _ = try parser.feed(Data("data: 123".utf8))
        XCTAssertThrowsError(try parser.feed(Data("45678".utf8))) {
            XCTAssertEqual($0 as? AnyLiveQueryError, .frameTooLarge)
        }
    }

    func testReadyAndInitialSnapshotOrderIsRequired() throws {
        let generation = UUID()
        var window = AnyQueryWindow(generation: generation, limit: 4)
        XCTAssertThrowsError(try window.apply(initial([]), generation: generation))
        XCTAssertNil(try window.apply(frame("ready", .object([:])), generation: generation))
        XCTAssertThrowsError(try window.apply(frame("ready", .object([:])), generation: generation))
        XCTAssertThrowsError(try window.apply(frame("changes", .array([])), generation: generation))
        let update = try XCTUnwrap(window.apply(initial([]), generation: generation))
        XCTAssertTrue(update.initial)
        XCTAssertThrowsError(try window.apply(initial([]), generation: generation))
    }

    func testIncompleteSnapshotCannotFoldClaims() throws {
        let generation = UUID()
        var window = AnyQueryWindow(generation: generation, limit: 4, requireComplete: true)
        _ = try window.apply(frame("ready", .object([:])), generation: generation)
        XCTAssertThrowsError(try window.apply(frame("snapshot", .object([
            "records": .array([]), "total": .integer(1), "hasNext": .bool(true)
        ])), generation: generation)) {
            XCTAssertEqual($0 as? AnyLiveQueryError, .incompleteWindow)
        }
    }

    func testFullDocumentIsAuthoritativeAndEmptyVersionIsApplied() throws {
        let generation = UUID()
        var window = AnyQueryWindow(generation: generation, limit: 4, requireComplete: true)
        _ = try window.apply(frame("ready", .object([:])), generation: generation)
        _ = try window.apply(initial([.object(["id": .string("one"), "title": .string("old")])]), generation: generation)
        let next = AnyJSON.object(["id": .string("one"), "title": .string("תורה"), "future": .integer(42)])
        let update = try XCTUnwrap(window.apply(frame("changes", .array([.object([
            "versionId": .string(""),
            "updated": .array([.object(["id": .string("one"), "doc": next, "ops": .array([])])])
        ])])), generation: generation))
        XCTAssertEqual(update.records, [next])
        XCTAssertFalse(update.initial)
    }

    func testMalformedBatchDoesNotPartiallyCommitItsFirstRecord() throws {
        let generation = UUID()
        var window = AnyQueryWindow(generation: generation, limit: 4)
        _ = try window.apply(frame("ready", .object([:])), generation: generation)
        let original = AnyJSON.object(["id": .string("one"), "value": .integer(1)])
        _ = try window.apply(initial([original]), generation: generation)
        XCTAssertThrowsError(try window.apply(frame("changes", .array([.object([
            "versionId": .string("v1"),
            "updated": .array([
                .object(["id": .string("one"), "doc": .object(["id": .string("one"), "value": .integer(2)])]),
                .object(["id": .string("missing"), "doc": .object(["id": .string("missing")])])
            ])
        ])])), generation: generation))
        let unchanged = try XCTUnwrap(window.apply(frame("changes", .array([])), generation: generation))
        XCTAssertEqual(unchanged.records, [original])
    }

    func testDisplacedRecordInvalidatesACompleteWindow() throws {
        let generation = UUID()
        var window = AnyQueryWindow(generation: generation, limit: 4, requireComplete: true)
        _ = try window.apply(frame("ready", .object([:])), generation: generation)
        _ = try window.apply(initial([.object(["id": .string("one")])]), generation: generation)
        XCTAssertThrowsError(try window.apply(frame("changes", .array([.object([
            "versionId": .string("v1"),
            "removed": .array([.object(["id": .string("one"), "reason": .string("displaced")])])
        ])])), generation: generation)) {
            XCTAssertEqual($0 as? AnyLiveQueryError, .incompleteWindow)
        }
    }

    func testTerminalOverflowAndGenerationChangeRequireResnapshot() throws {
        let generation = UUID()
        var window = AnyQueryWindow(generation: generation, limit: 4)
        XCTAssertThrowsError(try window.apply(frame("ready", .object([:])), generation: UUID())) {
            XCTAssertEqual($0 as? AnyLiveQueryError, .staleGeneration)
        }
        XCTAssertThrowsError(try window.apply(frame("closed", .object(["reason": .string("overflow")])), generation: generation)) {
            XCTAssertEqual($0 as? AnyLiveQueryError, .closed("overflow"))
        }
    }

    func testRetainedWindowBytesAreBoundedAcrossSmallDeltas() throws {
        let generation = UUID()
        var window = AnyQueryWindow(generation: generation, limit: 4, maximumWindowBytes: 64)
        _ = try window.apply(frame("ready", .object([:])), generation: generation)
        let first = AnyJSON.object(["id": .string("one"), "value": .string(String(repeating: "a", count: 20))])
        _ = try window.apply(initial([first]), generation: generation)
        XCTAssertThrowsError(try window.apply(frame("changes", .array([.object([
            "versionId": .string("v1"),
            "added": .array([.object([
                "id": .string("two"),
                "doc": .object(["id": .string("two"), "value": .string(String(repeating: "b", count: 20))])
            ])])
        ])])), generation: generation)) {
            XCTAssertEqual($0 as? AnyLiveQueryError, .windowTooLarge)
        }
        let unchanged = try XCTUnwrap(window.apply(frame("changes", .array([])), generation: generation))
        XCTAssertEqual(unchanged.records, [first])
    }

    @MainActor
    func testSessionInvalidationCancelsRegisteredWorkAndPreventsReuse() async throws {
        let session = AnyStreamSession()
        let pair = AsyncStream<Bool>.makeStream()
        _ = try await session.register(generation: session.generation) {
            pair.continuation.yield(true)
            pair.continuation.finish()
        }
        await session.invalidate()
        var cancelled = false
        for await signal in pair.stream { cancelled = signal }
        XCTAssertTrue(cancelled)
        do {
            try await session.requireActive(generation: session.generation)
            XCTFail("invalidated generation was accepted")
        } catch { XCTAssertEqual(error as? AnyLiveQueryError, .staleGeneration) }
        do {
            _ = try await session.register(generation: session.generation) {}
            XCTFail("registered work on an invalidated generation")
        } catch { XCTAssertEqual(error as? AnyLiveQueryError, .staleGeneration) }
    }
}
