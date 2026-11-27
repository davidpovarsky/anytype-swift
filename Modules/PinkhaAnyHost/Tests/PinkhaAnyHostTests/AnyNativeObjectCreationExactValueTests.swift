import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

private actor ExactValueCreationJournal: AnyNativeCreationJournaling {
    nonisolated let workspace: AnyTorahWorkspace
    private var identities: [String: AnyNativeCreationIdentity] = [:]
    private var states: [String: AnyNativeCreationState] = [:]
    private var transitions: [AnyNativeCreationState] = []

    init(workspace: AnyTorahWorkspace) { self.workspace = workspace }

    func reserve(_ identity: AnyNativeCreationIdentity) throws -> AnyNativeCreationReservation {
        guard identity.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        if let existing = identities[identity.key] {
            guard existing == identity, let state = states[identity.key] else {
                throw AnyNativeCreationError.contentConflict
            }
            return .init(state: state, ownsDispatch: false)
        }
        identities[identity.key] = identity
        states[identity.key] = .reserved
        transitions.append(.reserved)
        return .init(state: .reserved, ownsDispatch: true)
    }

    func record(_ state: AnyNativeCreationState, identity: AnyNativeCreationIdentity) throws {
        guard identity.workspace == workspace, identities[identity.key] == identity,
              let previous = states[identity.key] else {
            throw AnyNativeCreationError.contentConflict
        }
        switch (previous, state) {
        case (.reserved, .created): break
        case (.created(let old), .verified(let new)) where old == new: break
        case (.verified(let old), .verified(let new)) where old == new: break
        default: throw AnyNativeCreationError.contentConflict
        }
        states[identity.key] = state
        transitions.append(state)
    }

    func lookup(_ identity: AnyNativeCreationIdentity) throws -> AnyNativeCreationState? {
        guard identity.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        if let existing = identities[identity.key], existing != identity {
            throw AnyNativeCreationError.contentConflict
        }
        return states[identity.key]
    }

    func recordedTransitions() -> [AnyNativeCreationState] { transitions }
}

/// Exercises the real creator's dispatch/inspection/journal path through its
/// existing internal initializer. It makes no HTTP or native-runtime claim.
private actor ExactValueCreationNative {
    private let identity: AnyNativeCreationIdentity
    private let objectID: String
    private var inspectedRecord: AnyJSON
    private var dispatches = 0
    private var inspectedIDs: [String] = []
    private var confirmedIDs: [String] = []

    init(identity: AnyNativeCreationIdentity, objectID: String, record: AnyJSON) {
        self.identity = identity
        self.objectID = objectID
        self.inspectedRecord = record
    }

    func dispatch(_ intent: AnyNativeObjectCreationIntent,
                  authorize: @escaping @Sendable () async throws -> Void) async throws -> String {
        guard intent.identity == identity else { throw AnyNativeCreationError.contentConflict }
        try await authorize()
        dispatches += 1
        return objectID
    }

    func inspect(_ id: String) throws -> AnyJSON {
        inspectedIDs.append(id)
        guard id == objectID, dispatches > 0 else {
            throw AnyEngineError.invalidIdentity("exact-value fixture object")
        }
        return inspectedRecord
    }

    func confirm(_ id: String) { confirmedIDs.append(id) }

    func observation() -> (dispatches: Int, inspectedIDs: [String], confirmedIDs: [String]) {
        (dispatches, inspectedIDs, confirmedIDs)
    }
}

@MainActor
final class AnyNativeObjectCreationExactValueTests: XCTestCase {
    private let objectID = "created-exact-object"
    private let latinComposed = "https://example.test/caf\u{00E9}?source=bookmark"
    private let latinDecomposed = "https://example.test/cafe\u{0301}?source=bookmark"
    private let hebrewUnordered = "https://example.test/\u{05E9}\u{05C1}\u{05B7}?source=bookmark"
    private let hebrewOrdered = "https://example.test/\u{05E9}\u{05B7}\u{05C1}?source=bookmark"

    private func workspace() throws -> AnyTorahWorkspace {
        try .init(accountID: "exact-value-account", spaceID: "exact-value-space")
    }

    private func properties(_ value: AnyJSON) -> AnyJSON {
        .object(["any": .object(["url": value])])
    }

    private func record(_ properties: AnyJSON) throws -> AnyJSON {
        var groups = try XCTUnwrap(properties.object)
        var any = groups["any"]?.object ?? [:]
        any["type"] = .string("bookmark")
        any["collections"] = .array([])
        any["nativeOnly"] = .integer(17)
        groups["any"] = .object(any)
        groups["id"] = .string(objectID)
        groups["spaceId"] = .string(try workspace().spaceID)
        groups["serverOnly"] = .object(["revision": .integer(9)])
        return .object(groups)
    }

    private func creator(_ journal: ExactValueCreationJournal,
                         _ native: ExactValueCreationNative) -> AnyNativeObjectCreator {
        .init(workspace: journal.workspace, journal: journal,
              dispatch: { intent, authorize in
                  try await native.dispatch(intent, authorize: authorize)
              }, inspect: { try await native.inspect($0) })
    }

    private func assertUnverifiedAfterDispatchAndResume(
        expected: AnyJSON, actual: AnyJSON, label: String,
        file: StaticString = #filePath, line: UInt = #line
    ) async throws {
        let scope = try workspace()
        let intent = try AnyNativeObjectCreationIntent(
            workspace: scope, mutationID: String(repeating: "a", count: 32),
            typeID: "bookmark", initialProperties: expected)
        let journal = ExactValueCreationJournal(workspace: scope)
        let native = ExactValueCreationNative(identity: intent.identity, objectID: objectID,
                                              record: try record(actual))
        // The second owner resumes the same journal entry. It must inspect the
        // original known ID, not obtain a replacement dispatch reservation.
        for attempt in 0..<2 {
            let owner = creator(journal, native)
            do {
                _ = try await owner.ensureObject(intent, authorize: {},
                    onNativeConfirmed: { await native.confirm($0) })
                XCTFail("Mismatch must not be delivered as verified: \(label), attempt \(attempt)",
                        file: file, line: line)
            } catch {
                XCTAssertEqual(error as? AnyNativeCreationError, .createdObjectIncomplete(objectID),
                               label, file: file, line: line)
            }
            let state = try await journal.lookup(intent.identity)
            let transitions = await journal.recordedTransitions()
            let knownID = try await owner.recordedObjectID(for: intent)
            let observed = await native.observation()
            XCTAssertEqual(state, .created(objectID), label, file: file, line: line)
            XCTAssertEqual(transitions, [.reserved, .created(objectID)], label, file: file, line: line)
            XCTAssertEqual(knownID, objectID, label, file: file, line: line)
            XCTAssertEqual(observed.dispatches, 1, label, file: file, line: line)
            XCTAssertEqual(observed.inspectedIDs, Array(repeating: objectID, count: attempt+1),
                           label, file: file, line: line)
            XCTAssertTrue(observed.confirmedIDs.isEmpty, label, file: file, line: line)
        }
    }

    private func assertVerifiedAndRecovered(
        expected: AnyJSON, label: String,
        file: StaticString = #filePath, line: UInt = #line
    ) async throws {
        let scope = try workspace()
        let intent = try AnyNativeObjectCreationIntent(
            workspace: scope, mutationID: String(repeating: "b", count: 32),
            typeID: "bookmark", initialProperties: expected)
        let journal = ExactValueCreationJournal(workspace: scope)
        let native = ExactValueCreationNative(identity: intent.identity, objectID: objectID,
                                              record: try record(expected))
        for attempt in 0..<2 {
            let owner = creator(journal, native)
            let actualID = try await owner.ensureObject(intent, authorize: {},
                onNativeConfirmed: { await native.confirm($0) })
            let state = try await journal.lookup(intent.identity)
            let transitions = await journal.recordedTransitions()
            let observed = await native.observation()
            XCTAssertEqual(actualID, objectID, label, file: file, line: line)
            XCTAssertEqual(state, .verified(objectID), label, file: file, line: line)
            XCTAssertEqual(transitions, [.reserved, .created(objectID), .verified(objectID)],
                           label, file: file, line: line)
            XCTAssertEqual(observed.dispatches, 1, label, file: file, line: line)
            XCTAssertEqual(observed.inspectedIDs, Array(repeating: objectID, count: attempt+1),
                           label, file: file, line: line)
            XCTAssertEqual(observed.confirmedIDs, Array(repeating: objectID, count: attempt+1),
                           label, file: file, line: line)
        }
    }

    func testLatinCanonicallyEquivalentURLDoesNotVerifyOrRedispatch() async throws {
        XCTAssertEqual(latinComposed, latinDecomposed, "Fixture must reproduce Swift canonical equality")
        XCTAssertNotEqual(Data(latinComposed.utf8), Data(latinDecomposed.utf8))
        try await assertUnverifiedAfterDispatchAndResume(
            expected: properties(.string(latinComposed)), actual: properties(.string(latinDecomposed)),
            label: "composed request versus decomposed native URL")
    }

    func testHebrewCanonicallyReorderedURLDoesNotVerifyOrRedispatch() async throws {
        XCTAssertEqual(hebrewUnordered, hebrewOrdered, "Fixture must reproduce Swift canonical equality")
        XCTAssertNotEqual(Data(hebrewUnordered.utf8), Data(hebrewOrdered.utf8))
        try await assertUnverifiedAfterDispatchAndResume(
            expected: properties(.string(hebrewUnordered)), actual: properties(.string(hebrewOrdered)),
            label: "same Hebrew grapheme with different UTF-8 mark order")
    }

    func testExactNonNormalizedURLVerifiesAndNewOwnerRecoversOriginalID() async throws {
        let exact = latinDecomposed + "&hebrew=" + "\u{05E9}\u{05C1}\u{05B7}"
        try await assertVerifiedAndRecovered(expected: properties(.string(exact)),
                                            label: "unchanged exact non-normalized URL")
    }

    func testArrayStringsRequireExactBytesLengthAndOrder() async throws {
        let expected: AnyJSON = .array([.string(latinComposed), .string(hebrewUnordered)])
        let mismatches: [(String, AnyJSON)] = [
            ("Latin bytes", .array([.string(latinDecomposed), .string(hebrewUnordered)])),
            ("Hebrew bytes", .array([.string(latinComposed), .string(hebrewOrdered)])),
            ("missing array item", .array([.string(latinComposed)])),
            ("extra array item", .array([.string(latinComposed), .string(hebrewUnordered), .null])),
            ("different array order", .array([.string(hebrewUnordered), .string(latinComposed)]))
        ]
        for (label, actual) in mismatches {
            try await assertUnverifiedAfterDispatchAndResume(
                expected: properties(expected), actual: properties(actual), label: label)
        }
    }

    func testObjectsInsideArraysRequireFullNestedEquality() async throws {
        let expected: AnyJSON = .array([.object([
            "entry": .object(["url": .string(latinComposed), "enabled": .bool(true)])
        ])])
        let mismatches: [(String, AnyJSON)] = [
            ("extra outer object field", .array([.object([
                "entry": .object(["url": .string(latinComposed), "enabled": .bool(true)]),
                "extra": .integer(1)
            ])])),
            ("extra nested object field", .array([.object([
                "entry": .object(["url": .string(latinComposed), "enabled": .bool(true), "extra": .integer(1)])
            ])])),
            ("missing nested object field", .array([.object([
                "entry": .object(["url": .string(latinComposed)])
            ])])),
            ("nested string is canonically equal but byte different", .array([.object([
                "entry": .object(["url": .string(latinDecomposed), "enabled": .bool(true)])
            ])]))
        ]
        for (label, actual) in mismatches {
            try await assertUnverifiedAfterDispatchAndResume(
                expected: properties(expected), actual: properties(actual), label: label)
        }
    }

    func testCanonicalEquivalentDictionaryKeysCannotVerifyOriginalProperties() async throws {
        let expectedKey = "caf\u{00E9}"
        let actualKey = "cafe\u{0301}"
        XCTAssertEqual(expectedKey, actualKey)
        XCTAssertNotEqual(Data(expectedKey.utf8), Data(actualKey.utf8))
        try await assertUnverifiedAfterDispatchAndResume(
            expected: .object(["custom": .object([expectedKey: .string("exact value")])]),
            actual: .object(["custom": .object([actualKey: .string("exact value")])]),
            label: "stored property key has different UTF-8")
        try await assertUnverifiedAfterDispatchAndResume(
            expected: properties(.array([.object([expectedKey: .string("exact value")])])),
            actual: properties(.array([.object([actualKey: .string("exact value")])])),
            label: "stored array-object key has different UTF-8")
    }

    func testExactStructuredValuesAllowUnrelatedNativeMetadataAndRecover() async throws {
        let exact: AnyJSON = .array([
            .string(latinDecomposed), .string(hebrewUnordered),
            .object(["entry": .object([
                "url": .string(latinDecomposed),
                "values": .array([.null, .bool(true), .integer(7), .number(0.25)])
            ])])
        ])
        // record() adds independent root and any-group fields. Those remain
        // legitimate metadata; an object inside the expected array is exact.
        try await assertVerifiedAndRecovered(expected: properties(exact),
                                            label: "exact arrays and nested values with unrelated native metadata")
    }
}
