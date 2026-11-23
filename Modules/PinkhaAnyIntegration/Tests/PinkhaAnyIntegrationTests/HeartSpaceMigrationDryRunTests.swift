import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration

final class HeartSpaceMigrationDryRunTests: XCTestCase {
    private typealias Plan = AnyHeartSpaceMigrationDryRun
    private typealias Entry = AnyHeartSpaceArchive.Entry
    private typealias ID = Plan.Identity
    private let sourceSpace = "heart-source"

    private func entry(_ path: String, _ value: AnyJSON) throws -> Entry {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return Entry(path: path, bytes: try encoder.encode(value))
    }
    private func index(_ manifest: [String: AnyJSON] = [:], extra: [String: AnyJSON] = [:]) throws -> Entry {
        var value: [String: AnyJSON] = ["formatVersion": .string("2.0"), "manifest": .object(manifest)]
        value.merge(extra) { _, new in new }
        return try entry("index.json", .object(value))
    }
    private func page(_ id: String, extra: [String: AnyJSON] = [:]) throws -> Entry {
        var value: [String: AnyJSON] = ["formatVersion": .string("2.0"), "id": .string(id)]
        value.merge(extra) { _, new in new }
        return try entry("objects/" + id + ".json", .object(value))
    }
    private func block(_ id: String, indent: Int64 = 0, type: String = "paragraph", text: String = "body") -> AnyJSON {
        .object(["id": .string(id), "type": .string(type), "indent": .integer(indent), "text": .string(text)])
    }
    private func definition(_ key: String, spelling: String, format: String = "text") -> AnyJSON {
        .object(["internal_key": .string(key), "property": .string(spelling), "format": .string(format)])
    }
    private func dictionary(_ values: [AnyJSON]) throws -> Entry {
        try entry("properties.json", .object(["formatVersion": .string("2.0"), "properties": .array(values)]))
    }
    private func identity(_ kind: ID.Kind, _ id: String, owner: String? = nil, space: String? = nil) -> ID {
        ID(kind: kind, sourceSpaceID: space ?? sourceSpace, sourceObjectID: owner, sourceID: id)
    }
    private func mapping(_ kind: ID.Kind, _ id: String, _ target: String) -> Plan.Mapping {
        .init(source: identity(kind, id), destinationReference: target)
    }
    private func plan(_ entries: [Entry], mappings: [Plan.Mapping] = [],
                      account: String = "any-account", space: String = "any-space",
                      sidecars: Set<String> = []) throws -> Plan {
        try Plan(archive: AnyHeartSpaceArchive(sourceSpaceID: sourceSpace, entries: entries,
                                               retainedNativeSidecarPaths: sidecars),
                 destination: AnyTorahWorkspace(accountID: account, spaceID: space), mappings: mappings)
    }
    private func row(_ plan: Plan, _ kind: ID.Kind, _ id: String, owner: String? = nil,
                     file: StaticString = #filePath, line: UInt = #line) throws -> Plan.Entity {
        try XCTUnwrap(plan.entities.first { $0.identity == identity(kind, id, owner: owner) }, file: file, line: line)
    }
    private func decision(_ plan: Plan, _ kind: ID.Kind, _ id: String,
                          file: StaticString = #filePath, line: UInt = #line) throws -> Plan.MappingDecision {
        try XCTUnwrap(plan.mappingDecisions.first { $0.source == identity(kind, id) }, file: file, line: line)
    }
    private func assertNotAdmitted(_ plan: Plan, file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertFalse(plan.permitsDestinationWrites, file: file, line: line)
        XCTAssertFalse(plan.hasNativeSourceAdmission, file: file, line: line)
        XCTAssertEqual(plan.inspectionIssues, plan.archive.issues, file: file, line: line)
        XCTAssertTrue(plan.inspectionIssues.contains { $0.code == .nativeSnapshotProofRequired }, file: file, line: line)
        XCTAssertTrue(plan.inspectionIssues.contains { $0.code == .nativeIdentityCensusRequired }, file: file, line: line)
    }

    func testEverySuppliedObjectBlockFilePropertyAndUseHasOneScopedDecision() throws {
        let entries = [
            try index(["properties": .string("properties.json"), "files": .object(["file": .string("payload/file.bin")])]),
            try dictionary([definition("title", spelling: "Title"), definition("unused", spelling: "Unused")]),
            try page("page", extra: [
                "type": .string("Book"), "type_internal_key": .string("book"),
                "blocks": .array([block("a"), block("b", indent: 1)]),
                "properties": .object(["Title": .string("Exact")]),
                "property_internal_keys": .object(["Title": .string("title"), "Missing": .string("ghost")])]),
            try page("type-definition", extra: ["kind": .string("object_type"), "internal_key": .string("book")]),
            try page("file", extra: ["kind": .string("file_object")]),
            Entry(path: "payload/file.bin", bytes: Data([0, 1, 255]))
        ]
        let result = try plan(entries, mappings: [
            mapping(.type, "book", "any-book"), mapping(.property, "title", "any-title"),
            mapping(.property, "unused", "any-unused"), mapping(.objectType, "file", "any-file"),
            mapping(.objectType, "type-definition", "any-type")
        ])
        let expected: Set<ID> = [
            identity(.object, "page"), identity(.object, "type-definition"), identity(.object, "file"),
            identity(.block, "a", owner: "page"), identity(.block, "b", owner: "page"),
            identity(.file, "file"), identity(.type, "book"),
            identity(.objectType, "type-definition"), identity(.objectType, "file"),
            identity(.property, "title"), identity(.property, "unused"), identity(.property, "ghost"),
            identity(.propertyUse, "Title", owner: "page"), identity(.propertyUse, "Missing", owner: "page")
        ]
        XCTAssertEqual(Set(result.entities.map(\.identity)), expected)
        XCTAssertEqual(result.entities.count, expected.count)
        XCTAssertEqual(result.coverage.entitiesByKind, [.object: 3, .block: 2, .file: 1, .type: 1,
                                                        .objectType: 2, .property: 3, .propertyUse: 2])
        XCTAssertEqual(result.coverage.retainedEntryCount, entries.count)
        XCTAssertEqual(result.coverage.retainedByteCount, entries.reduce(0) { $0 + $1.bytes.count })
        XCTAssertEqual(try row(result, .property, "title").proposedDestinationReference, "any-title")
        XCTAssertEqual(try row(result, .property, "unused").references, [])
        XCTAssertEqual(try row(result, .property, "ghost").disposition, .unresolvedSourceIdentity)
        assertNotAdmitted(result)
    }

    func testBlockParentsAndIdentitiesNeverCrossObjectsOrFileNamespace() throws {
        let result = try plan([
            try index(), try page("a", extra: ["blocks": .array([block("same"), block("child", indent: 1)])]),
            try page("b", extra: ["blocks": .array([block("same")])]),
            try page("same", extra: ["kind": .string("file_object")])
        ])
        let keys = [
            try row(result, .block, "same", owner: "a").identity,
            try row(result, .block, "same", owner: "b").identity,
            try row(result, .object, "same").identity,
            try row(result, .file, "same").identity
        ]
        XCTAssertEqual(Set(keys).count, 4)
        XCTAssertEqual(Set(keys.map(\.symbolicKey)).count, 4)
        let child = try row(result, .block, "child", owner: "a")
        XCTAssertEqual(child.parent, identity(.block, "same", owner: "a"))
        XCTAssertEqual(child.order, 1)
        XCTAssertEqual(Set(child.references), [identity(.object, "a"), identity(.block, "same", owner: "a")])
        XCTAssertEqual(try row(result, .block, "same", owner: "b").parent, identity(.object, "b"))
    }

    func testAmbiguousPropertySpellingsStayUnresolvedUnlessTheSourceLegendBindsThem() throws {
        let result = try plan([
            try index(["properties": .string("properties.json")]),
            try dictionary([definition("first", spelling: "Tag"), definition("second", spelling: "Tag")]),
            try page("explicit", extra: ["properties": .object(["Tag": .string("one")]),
                "property_internal_keys": .object(["Tag": .string("second")])]),
            try page("ambiguous", extra: ["properties": .object(["Tag": .string("two"), "tag": .string("three")])])
        ], mappings: [mapping(.property, "first", "target-first"), mapping(.property, "second", "target-second")])
        XCTAssertTrue(try row(result, .propertyUse, "Tag", owner: "explicit").references.contains(identity(.property, "second")))
        for spelling in ["Tag", "tag"] {
            let use = try row(result, .propertyUse, spelling, owner: "ambiguous")
            XCTAssertEqual(use.disposition, .unresolvedSourceIdentity)
            XCTAssertEqual(use.references, [identity(.object, "ambiguous")])
        }
        XCTAssertEqual(result.issues.filter { $0.code == .propertyIdentityUnresolved }.count, 2)
        assertNotAdmitted(result)
    }

    func testUnusedDefinitionsLegendOnlyIdentitiesAndEscapedLocationsAreRetained() throws {
        let result = try plan([
            try index(["properties": .string("properties.json")]),
            try dictionary([definition("unused", spelling: "Unused"), definition("slash", spelling: "a/b~")]),
            try page("p", extra: ["properties": .object(["a/b~": .null]),
                "property_internal_keys": .object(["a/b~": .string("slash"), "OnlyLegend": .string("unknown")])])
        ], mappings: [mapping(.property, "unknown", "proposed-unknown")])
        XCTAssertEqual(try row(result, .property, "unused").sourceValues.count, 1)
        XCTAssertTrue(try row(result, .property, "unused").references.isEmpty)
        let missing = try row(result, .propertyUse, "OnlyLegend", owner: "p")
        XCTAssertTrue(missing.sourceValues.isEmpty)
        XCTAssertTrue(result.issues.contains { $0.code == .propertyValueMissing && $0.identity == missing.identity })
        let unknown = try row(result, .property, "unknown")
        XCTAssertTrue(unknown.sourceValues.isEmpty)
        XCTAssertEqual(unknown.disposition, .unresolvedSourceIdentity)
        XCTAssertEqual(unknown.proposedDestinationReference, "proposed-unknown")
        let escaped = try row(result, .propertyUse, "a/b~", owner: "p")
        XCTAssertEqual(escaped.sourceValues, [.null])
        XCTAssertEqual(Set(escaped.locations.map(\.jsonPointer)),
                       ["/properties/a~1b~0", "/property_internal_keys/a~1b~0"])
    }

    func testMappingRequestsRefuseWrongSpaceWrongKindMalformedAndDuplicateBindings() throws {
        let entries = [try index(), try page("p")]
        let invalid: [Plan.Mapping] = [
            .init(source: identity(.property, "x", space: "foreign"), destinationReference: "target"),
            .init(source: identity(.object, "p"), destinationReference: "target"),
            .init(source: identity(.objectType, "p", owner: "p"), destinationReference: "target"),
            mapping(.objectType, "p", ""), mapping(.objectType, "p", "bad\u{0000}target"),
            mapping(.objectType, "p", String(repeating: "x", count: 4097))
        ]
        for item in invalid {
            XCTAssertThrowsError(try plan(entries, mappings: [item])) { error in
                guard case AnyHeartSpaceDryRunError.invalidMapping = error else { return XCTFail("\(error)") }
            }
        }
        for second in ["one", "two"] {
            XCTAssertThrowsError(try plan(entries, mappings: [
                mapping(.objectType, "p", "one"), mapping(.objectType, "p", second)
            ])) { error in
                guard case AnyHeartSpaceDryRunError.duplicateMapping = error else { return XCTFail("\(error)") }
            }
        }
    }

    func testDistinctSchemaIdentitiesCannotSilentlyMergeButOrdinaryTypeAssignmentsMayAgree() throws {
        let result = try plan([
            try index(), try page("one", extra: ["type": .string("A"), "type_internal_key": .string("type-a")]),
            try page("two", extra: ["type": .string("B"), "type_internal_key": .string("type-b")]),
            try page("plain-a"), try page("plain-b")
        ], mappings: [
            mapping(.type, "type-a", "same-type"), mapping(.type, "type-b", "same-type"),
            mapping(.objectType, "plain-a", "ordinary-page"), mapping(.objectType, "plain-b", "ordinary-page")
        ])
        for key in ["type-a", "type-b"] {
            XCTAssertEqual(try decision(result, .type, key).status, .aliasedDestination)
            XCTAssertNil(try row(result, .type, key).proposedDestinationReference)
        }
        for key in ["plain-a", "plain-b"] {
            XCTAssertEqual(try decision(result, .objectType, key).status, .proposedReferenceOnly)
        }
        XCTAssertEqual(result.issues.filter { $0.code == .sourceTypeDefinitionMissing }.count, 2)
        assertNotAdmitted(result)
    }

    func testDuplicateNativeTypeDefinitionIdentityRetainsBothObjectsAndRefusesResolution() throws {
        let result = try plan([
            try index(),
            try page("first-definition", extra: ["kind": .string("object_type"), "internal_key": .string("same"),
                                                 "future": .string("first")]),
            try page("second-definition", extra: ["kind": .string("object_type"), "internal_key": .string("same"),
                                                  "future": .string("second")]),
            try page("p", extra: ["type": .string("Title"), "type_internal_key": .string("same")])
        ], mappings: [mapping(.type, "same", "target")])
        let type = try row(result, .type, "same")
        XCTAssertEqual(type.sourceValues.count, 2)
        XCTAssertEqual(Set(type.references), [identity(.object, "first-definition"), identity(.object, "second-definition")])
        XCTAssertEqual(Set(type.sourceValues.compactMap { $0["future"]?.string }), ["first", "second"])
        XCTAssertEqual(try decision(result, .type, "same").status, .ambiguousSource)
        XCTAssertNil(type.proposedDestinationReference)
        XCTAssertTrue(result.issues.contains { $0.code == .ambiguousTypeIdentity && $0.identity == type.identity })
    }

    func testDisplayTypeNamesDoNotBecomeNativeIdentitiesAndUnknownMappingsRemainVisible() throws {
        let entries = [try index(), try page("p", extra: ["type": .string("Page")])]
        let guessed = try plan(entries, mappings: [mapping(.type, "Page", "target")])
        XCTAssertEqual(try decision(guessed, .type, "Page").status, .unboundSource)
        XCTAssertEqual(try decision(guessed, .objectType, "p").status, .missing)
        XCTAssertFalse(guessed.entities.contains { $0.identity == identity(.type, "Page") })
        let explicit = try plan(entries, mappings: [mapping(.objectType, "p", "target")])
        XCTAssertEqual(try decision(explicit, .objectType, "p").status, .proposedReferenceOnly)
        XCTAssertTrue(explicit.inspectionIssues.contains { $0.code == .missingTypeIdentity })
        assertNotAdmitted(explicit)
    }

    func testEveryFilePayloadIsClassifiedWithoutInferringOwnerOrRemoteBytes() throws {
        let files: [String: AnyJSON] = ["empty": .string("data/empty"), "inline": .string("data/inline"),
                                      "large": .string("data/large")]
        let entries = [
            try index(["files": .object(files)]),
            try page("empty", extra: ["kind": .string("file_object")]),
            try page("inline", extra: ["kind": .string("file")]),
            try page("large", extra: ["kind": .string("file_object")]),
            try page("remote", extra: ["kind": .string("file_object"), "file_remote": .string("opaque-only")]),
            try page("missing", extra: ["kind": .string("file_object")]),
            Entry(path: "data/empty", bytes: Data()),
            Entry(path: "data/inline", bytes: Data(repeating: 0xAB, count: 4095)),
            Entry(path: "data/large", bytes: Data(repeating: 0xCD, count: 4096))
        ]
        let result = try plan(entries)
        XCTAssertEqual(try row(result, .file, "empty").payload?.byteCount, 0)
        XCTAssertEqual(try row(result, .file, "inline").payload?.classification, .withinPreparedInlineByteBound)
        XCTAssertEqual(try row(result, .file, "inline").payload?.sha256,
                       AnyContentDigest.sha256(Data(repeating: 0xAB, count: 4095)))
        XCTAssertEqual(try row(result, .file, "large").payload?.classification, .requiresOtherFileStorage)
        XCTAssertEqual(try row(result, .file, "remote").payload?.classification, .remoteOnly)
        XCTAssertNil(try row(result, .file, "remote").payload?.sha256)
        XCTAssertEqual(try row(result, .file, "missing").payload?.classification, .missing)
        XCTAssertEqual(result.issues.filter { $0.code == .fileOwnerMappingRequired }.count, 5)
        XCTAssertEqual(result.coverage.entitiesByKind[.file], 5)
        for name in ["empty", "inline", "large", "remote", "missing"] {
            XCTAssertEqual(try row(result, .file, name).references, [identity(.object, name)])
        }
        assertNotAdmitted(result)
    }

    func testOriginalBytesUnknownValuesExactIntegerAndUnicodeAreNeverConverted() throws {
        let raw = Data(#"""
        { "formatVersion":"2.0", "id":"p",
          "future":{"large":9007199254740993,"text":"e\u0301\u05d0"},
          "blocks":[{"id":"b","type":"paragraph","text":"e\u0301\u05d0"}] }
        """#.utf8)
        let result = try plan([try index(), Entry(path: "objects/p.json", bytes: raw)],
                              mappings: [mapping(.objectType, "p", "target")])
        XCTAssertEqual(result.archive.originalEntries.first { $0.path == "objects/p.json" }?.bytes, raw)
        XCTAssertEqual(try row(result, .object, "p").sourceValues[0]["future"]?["large"]?.integer,
                       9_007_199_254_740_993)
        let text = try XCTUnwrap(try row(result, .block, "b", owner: "p").sourceValues[0]["text"]?.string)
        XCTAssertEqual(Data(text.utf8), Data("e\u{0301}\u{05d0}".utf8))
        XCTAssertTrue(result.inspectionIssues.contains { $0.code == .unknownEnvelopeField })
        XCTAssertEqual(result.entries.first { $0.path == "objects/p.json" }?.sha256, AnyContentDigest.sha256(raw))
    }

    func testUnclassifiedEntriesAndClaimedNativeSidecarsStayBytePreservedAndUnadmitted() throws {
        let sidecar = Entry(path: "native/census.json", bytes: Data(#"{"claimedComplete":true}"#.utf8))
        let opaque = Entry(path: "unknown/data.bin", bytes: Data([0, 255, 17]))
        let source = [try index(extra: ["future": .string("unknown")]), try page("p"), sidecar, opaque]
        let result = try plan(source, sidecars: [sidecar.path])
        XCTAssertEqual(Set(result.entries.map(\.path)), Set(source.map(\.path)))
        for original in source {
            XCTAssertEqual(result.archive.originalEntries.first { $0.path == original.path }?.bytes, original.bytes)
            XCTAssertEqual(result.entries.first { $0.path == original.path }?.sha256, AnyContentDigest.sha256(original.bytes))
        }
        XCTAssertTrue(try XCTUnwrap(result.entries.first { $0.path == sidecar.path }).identities.isEmpty)
        XCTAssertTrue(result.inspectionIssues.contains { $0.code == .unboundEntry && $0.path == opaque.path })
        assertNotAdmitted(result)
    }

    func testPlanBindingIsOrderIndependentAndIncludesSourceMappingsAndDestinationOwnership() throws {
        let entries = [try index(), try page("a"), try page("b"), Entry(path: "extra.bin", bytes: Data([1]))]
        let mappings = [mapping(.objectType, "a", "one"), mapping(.objectType, "b", "two")]
        let a = try plan(entries, mappings: mappings)
        let reordered = try plan(Array(entries.reversed()), mappings: Array(mappings.reversed()))
        XCTAssertEqual(a.planSHA256, reordered.planSHA256)
        XCTAssertEqual(a.entities.map(\.identity), reordered.entities.map(\.identity))
        XCTAssertNotEqual(a.planSHA256, try plan(entries, mappings: [mapping(.objectType, "a", "changed"), mappings[1]]).planSHA256)
        XCTAssertNotEqual(a.planSHA256, try plan(entries, mappings: mappings, account: "other-account").planSHA256)
        XCTAssertNotEqual(a.planSHA256, try plan(entries, mappings: mappings, space: "other-space").planSHA256)
        let changed = Array(entries.prefix(3)) + [Entry(path: "extra.bin", bytes: Data([2]))]
        XCTAssertNotEqual(a.planSHA256, try plan(changed, mappings: mappings).planSHA256)
        XCTAssertEqual(a.archive.contentSHA256, reordered.archive.contentSHA256)
    }

    func testMappingIdentityUsesExactUTF8WithoutUnicodeNormalizationOrCaseGuessing() throws {
        let key = "e\u{0301}"
        let entries = [try index(), try page("p", extra: ["type": .string("Visible"), "type_internal_key": .string(key)])]
        let wrong = try plan(entries, mappings: [mapping(.type, "\u{00e9}", "target"), mapping(.type, "E\u{0301}", "other")])
        XCTAssertEqual(try decision(wrong, .type, key).status, .missing)
        XCTAssertEqual(try decision(wrong, .type, "\u{00e9}").status, .unboundSource)
        XCTAssertEqual(try decision(wrong, .type, "E\u{0301}").status, .unboundSource)
        XCTAssertNotEqual(identity(.type, key), identity(.type, "\u{00e9}"))
        XCTAssertNotEqual(identity(.type, key).symbolicKey, identity(.type, "\u{00e9}").symbolicKey)
        let exact = try plan(entries, mappings: [mapping(.type, key, "target")])
        XCTAssertEqual(try decision(exact, .type, key).status, .proposedReferenceOnly)
        assertNotAdmitted(exact)
        let propertyAlias = try plan([
            try index(["properties": .string("properties.json")]),
            try dictionary([definition(key, spelling: "Title")]),
            try page("p", extra: ["properties": .object(["Title": .string("value")]),
                "property_internal_keys": .object(["Title": .string("\u{00e9}")])])
        ])
        XCTAssertEqual(try row(propertyAlias, .propertyUse, "Title", owner: "p").disposition, .unresolvedSourceIdentity)
        XCTAssertEqual(propertyAlias.coverage.entitiesByKind[.property], 2)
        XCTAssertEqual(try row(propertyAlias, .property, "\u{00e9}").disposition, .unresolvedSourceIdentity)
        XCTAssertEqual(try row(propertyAlias, .property, key).sourceValues.count, 1)
    }

    func testExcessMappingInputIsRejectedBeforeAnyPartialReportIsReturned() throws {
        let entries = [try index(), try page("p")]
        let tooMany = Array(repeating: mapping(.objectType, "p", "target"), count: Plan.maximumMappings + 1)
        XCTAssertThrowsError(try plan(entries, mappings: tooMany)) { error in
            XCTAssertEqual(error as? AnyHeartSpaceDryRunError, .limit)
        }
    }

    func testUnsupportedObjectsBlocksAndPropertyFormatsRemainExplicitAndUnconverted() throws {
        let result = try plan([
            try index(["properties": .string("properties.json")]),
            try dictionary([definition("future", spelling: "Future", format: "future-format")]),
            try page("unsupported", extra: ["kind": .string("future-kind"), "opaque": .bool(true),
                "blocks": .array([block("table", type: "table")]),
                "properties": .object(["Future": .object(["bytes": .string("preserved")])])])
        ], mappings: [mapping(.objectType, "unsupported", "target-type"), mapping(.property, "future", "target-property")])
        XCTAssertEqual(try row(result, .object, "unsupported").disposition, .unsupportedSourceKind)
        XCTAssertEqual(try row(result, .block, "table", owner: "unsupported").disposition, .unsupportedSourceKind)
        XCTAssertEqual(try row(result, .property, "future").sourceValues[0]["format"]?.string, "future-format")
        XCTAssertEqual(try row(result, .propertyUse, "Future", owner: "unsupported").sourceValues,
                       [.object(["bytes": .string("preserved")])])
        XCTAssertTrue(result.inspectionIssues.contains { $0.code == .unsupportedBlockType })
        XCTAssertTrue(result.inspectionIssues.contains { $0.code == .unsupportedObjectKind })
        assertNotAdmitted(result)
    }

    func testEmptySuppliedArchiveStillRequiresNativeAdmissionAndKeepsUnboundProposal() throws {
        let result = try plan([try index()], mappings: [mapping(.property, "not-supplied", "target")])
        XCTAssertTrue(result.entities.isEmpty)
        XCTAssertEqual(result.entries.count, 1)
        XCTAssertEqual(result.coverage.suppliedMappingCount, 1)
        XCTAssertEqual(try decision(result, .property, "not-supplied").status, .unboundSource)
        XCTAssertTrue(result.issues.contains { $0.code == .unboundMapping })
        assertNotAdmitted(result)
    }
}
