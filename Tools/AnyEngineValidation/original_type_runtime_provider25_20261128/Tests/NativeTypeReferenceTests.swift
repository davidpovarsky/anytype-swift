import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Original-source controls read only the qualified bundle/plan/mapping files.
/// Synthetic envelopes below exercise representation and refusal; they are not
/// native source captures, native receipts, or evidence of a migrated family.
final class NativeTypeReferenceTests: XCTestCase {
    func testAllOriginalTypesKeepCompleteOrderedRecommendationEvidence() throws {
        let fixture = try TypeReferenceOriginalFixture.load()
        let plan = try fixture.references()
        XCTAssertEqual(plan.presentations.count, 20)
        XCTAssertEqual(plan.presentations.filter { !$0.isMaterializedType }.count, 19)
        XCTAssertFalse(plan.permitsSourceAdmission)
        XCTAssertFalse(plan.permitsDestinationWrites)
        XCTAssertEqual(Set(plan.presentations.map { Data($0.sourceType.sourceObjectID.utf8) }),
            Set(fixture.catalog.types.map { Data($0.objectID.utf8) }))
        for sourceType in fixture.catalog.types {
            let presentation = try XCTUnwrap(plan.presentation(sourceTypeObjectID: sourceType.objectID))
            XCTAssertEqual(presentation.sourceType.protobufBytes, sourceType.snapshot.protobufBytes)
            XCTAssertEqual(presentation.sourceType.jsonViewBytes, sourceType.snapshot.jsonViewBytes)
            XCTAssertEqual(try wire(presentation.descriptor["originalDetails"]),
                try wire(.object(sourceType.snapshot.details)))
            XCTAssertEqual(presentation.groups.map(\.field), AnyNativeTypeReferenceGroup.Field.allCases)
            XCTAssertFalse(presentation.permitsDestinationWrites)
            XCTAssertFalse(presentation.qualifiesOriginalFamilyBehavior)
            for group in presentation.groups {
                let original = sourceType.snapshot.details[group.field.rawValue]
                XCTAssertEqual(group.isPresent, original != nil)
                let ids = try (original?.array ?? []).map { try XCTUnwrap($0.string) }
                XCTAssertEqual(group.references.map { Data($0.sourceObjectID.utf8) }, ids.map { Data($0.utf8) })
                for reference in group.references {
                    let captured = try XCTUnwrap(fixture.catalog.relation(objectID: reference.sourceObjectID))
                    XCTAssertEqual(reference.evidence.protobufBytes, captured.snapshot.protobufBytes)
                    XCTAssertEqual(reference.evidence.jsonViewBytes, captured.snapshot.jsonViewBytes)
                }
            }
            try presentation.requireExactDescriptor(presentation.descriptor)
            XCTAssertEqual(presentation.fingerprint, AnyContentDigest.sha256(try wire(presentation.descriptor)))
        }
        try fixture.requireUnchanged()
    }

    func testExistingPropertyAndComputedReferencesKeepDifferentNativeContracts() throws {
        let fixture = try TypeReferenceOriginalFixture.load()
        let plan = try fixture.references()
        var seenProperties = Set<Data>(), seenComputed = Set<String>(), seenSemantics = Set<String>()
        for presentation in plan.presentations {
            for reference in presentation.groups.flatMap(\.references) + presentation.definitionHidden {
                XCTAssertFalse(reference.permitsDestinationWrites)
                switch reference.target {
                case .property(let binding):
                    let entry = try XCTUnwrap(plan.directory.definition(sourceObjectID: reference.sourceObjectID))
                    XCTAssertEqual(entry.address, binding.entry.address)
                    XCTAssertEqual(entry.address, .property(ownerKind: binding.ownerKind, key: binding.key))
                    XCTAssertFalse(binding.permitsDestinationWrites)
                    XCTAssertNil(reference.descriptor["target"]?["contract"])
                    if let semantics = binding.canonicalValueSemantics { seenSemantics.insert(semantics.rawValue) }
                    seenProperties.insert(Data(reference.sourceObjectID.utf8))
                case .computed(let binding):
                    XCTAssertNil(plan.directory.definition(sourceObjectID: reference.sourceObjectID))
                    XCTAssertEqual(binding.readContract, AnyHeartNativeComputedRelationBinding.contract)
                    XCTAssertEqual(Data(binding.sourceRelationKey.utf8), Data(reference.relationKey.utf8))
                    XCTAssertNil(reference.descriptor["target"]?["ownerID"])
                    XCTAssertNil(reference.descriptor["target"]?["propertyID"])
                    XCTAssertFalse(binding.permitsDestinationWrites)
                    seenComputed.insert(binding.role.rawValue)
                case .unresolved(let reason):
                    XCTAssertEqual(reason, .noQualifiedNativeBinding)
                    XCTAssertFalse(reference.isExecutable)
                    XCTAssertNil(reference.descriptor["target"]?["ownerID"])
                    XCTAssertNil(reference.descriptor["target"]?["propertyID"])
                }
            }
        }
        XCTAssertFalse(seenProperties.isEmpty)
        XCTAssertEqual(seenComputed, ["links", "backlinks"])
        XCTAssertTrue(seenSemantics.contains(AnyNativeCanonicalValueSemantics.translatedIdentity.rawValue))
        XCTAssertTrue(seenSemantics.contains(AnyNativeCanonicalValueSemantics.destinationDerived.rawValue))
        let actualType = try XCTUnwrap(plan.presentations.first { $0.isMaterializedType })
        XCTAssertEqual(actualType.currentNativeTypeID,
            "bafyreiahhb7h2xpibzakaat54fjxmi6ocyti2wntr3rdxd6q475u2sajhq")
        for builtin in plan.presentations where !builtin.isMaterializedType {
            XCTAssertNil(builtin.currentNativeTypeID)
            XCTAssertEqual(builtin.descriptor["destinationType"], .null)
            let expected = Set((builtin.groups.flatMap(\.references) + builtin.definitionHidden)
                .filter { !$0.isExecutable }.map { Data($0.sourceObjectID.utf8) })
            XCTAssertEqual(Set(builtin.unresolvedSourceDefinitionIDs.map { Data($0.utf8) }), expected)
        }
        try fixture.requireUnchanged()
    }

    func testPartialForeignAndChangedCatalogsCannotSelectOriginalBindings() throws {
        let fixture = try TypeReferenceOriginalFixture.load()
        for kind in [Int64(528), 521, 529] {
            let removed = try XCTUnwrap(fixture.snapshots.first { $0.nativeType == kind })
            let partial = try fixture.catalog(rows: fixture.snapshots.filter {
                Data($0.sourceObjectID.utf8) != Data(removed.sourceObjectID.utf8)
            })
            XCTAssertThrowsError(try AnyHeartNativeTypeReferencePlan(catalog: partial, directory: fixture.directory)) {
                XCTAssertEqual($0 as? AnyNativeTypeReferenceError, .wrongSource)
            }
        }
        let foreign = try fixture.catalog(rows: fixture.snapshots, accountID: "foreign-source-account")
        XCTAssertThrowsError(try AnyHeartNativeTypeReferencePlan(catalog: foreign, directory: fixture.directory))
        let selected = try XCTUnwrap(fixture.catalog.relations.first)
        let altered = try TypeReferenceTestWire.replacing(selected.snapshot,
            details: ["description": .string("changed captured descriptor")])
        let changed = try fixture.catalog(rows: fixture.snapshots.map {
            Data($0.sourceObjectID.utf8) == Data(selected.objectID.utf8) ? altered : $0
        })
        XCTAssertThrowsError(try AnyHeartNativeTypeReferencePlan(catalog: changed, directory: fixture.directory))
        XCTAssertThrowsError(try {
            let differentWire = try TypeReferenceTestWire.replacing(selected.snapshot, protobufSuffix: Data([0]))
            let changedWire = try fixture.catalog(rows: fixture.snapshots.map {
                Data($0.sourceObjectID.utf8) == Data(selected.objectID.utf8) ? differentWire : $0
            })
            return try AnyHeartNativeTypeReferencePlan(catalog: changedWire, directory: fixture.directory)
        }())
        try fixture.requireUnchanged()
    }

    func testClosedDescriptorRejectsOmittedComputedRefsAliasAndReorderedSource() throws {
        let fixture = try TypeReferenceOriginalFixture.load()
        let plan = try fixture.references()
        let presentation = try XCTUnwrap(plan.presentations.first { value in
            value.groups.contains { $0.references.count > 1 && $0.references.contains { reference in
                if case .computed = reference.target { return true }; return false
            } }
        })
        var top = try XCTUnwrap(presentation.descriptor.object)
        top["contract"] = .string("pinkha-heart-type-references-v2")
        XCTAssertThrowsError(try presentation.requireExactDescriptor(.object(top)))
        top = try XCTUnwrap(presentation.descriptor.object); top["futureAuthority"] = .bool(true)
        XCTAssertThrowsError(try presentation.requireExactDescriptor(.object(top)))
        let group = try XCTUnwrap(presentation.groups.first { $0.references.count > 1 && $0.references.contains {
            if case .computed = $0.target { return true }; return false
        } })
        let references = group.references.map(\.descriptor)
        let computedIndex = try XCTUnwrap(group.references.firstIndex {
            if case .computed = $0.target { return true }; return false
        })
        func changed(_ rows: [AnyJSON]) throws -> AnyJSON {
            var root = try XCTUnwrap(presentation.descriptor.object)
            var groups = try XCTUnwrap(root["groups"]?.object)
            var field = try XCTUnwrap(groups[group.field.rawValue]?.object)
            field["references"] = .array(rows); groups[group.field.rawValue] = .object(field)
            root["groups"] = .object(groups); return .object(root)
        }
        XCTAssertThrowsError(try presentation.requireExactDescriptor(changed(references.enumerated()
            .filter { $0.offset != computedIndex }.map(\.element))))
        XCTAssertThrowsError(try presentation.requireExactDescriptor(changed(Array(references.reversed()))))
        var alias = references
        var row = try XCTUnwrap(alias[computedIndex].object)
        row["target"] = .object(["kind": .string("property"), "ownerKind": .string("types"),
            "ownerID": .string("any"), "propertyID": .string("links")])
        alias[computedIndex] = .object(row)
        XCTAssertThrowsError(try presentation.requireExactDescriptor(changed(alias)))
        try fixture.requireUnchanged()
    }

    func testAbsentEmptyRepeatedAndUnresolvedRecommendationsRemainDistinct() throws {
        let fixture = try TypeReferenceSyntheticFixture.make()
        let presentation = try XCTUnwrap(fixture.plan.presentation(sourceTypeObjectID: fixture.typeID))
        let recommended = try XCTUnwrap(presentation.groups.first { $0.field == .recommended })
        XCTAssertEqual(recommended.references.map { Data($0.sourceObjectID.utf8) },
            [fixture.computedID, fixture.unknownID, fixture.computedID].map { Data($0.utf8) })
        let featured = try XCTUnwrap(presentation.groups.first { $0.field == .featured })
        let hidden = try XCTUnwrap(presentation.groups.first { $0.field == .hidden })
        XCTAssertFalse(featured.isPresent); XCTAssertTrue(featured.references.isEmpty)
        XCTAssertTrue(hidden.isPresent); XCTAssertTrue(hidden.references.isEmpty)
        XCTAssertNotEqual(try wire(presentation.descriptor["groups"]?[featured.field.rawValue]),
            try wire(presentation.descriptor["groups"]?[hidden.field.rawValue]))
        XCTAssertEqual(presentation.orderedReferences.map { Data($0.sourceObjectID.utf8) },
            [fixture.computedID, fixture.unknownID].map { Data($0.utf8) })
        XCTAssertEqual(presentation.unresolvedSourceDefinitionIDs.map { Data($0.utf8) },
            [Data(fixture.unknownID.utf8)])
        XCTAssertNil(presentation.currentNativeTypeID)
        XCTAssertThrowsError(try TypeReferenceSyntheticFixture.make(recommendations: ["missing-source-relation"])) {
            XCTAssertEqual($0 as? AnyNativeTypeReferenceError, .missingSourceDefinition("missing-source-relation"))
        }
    }

    func testCapturedProviderOverrideAndExactUTF8NeverSelectAnAlias() throws {
        let changes: [[String: AnyJSON]] = [
            ["relationReadonlyValue": .bool(false)], ["relationMaxCount": .integer(1)],
            ["relationDefaultValue": .array([])], ["relationFormat": .integer(11)],
            ["description": .string("different provider semantics")]
        ]
        for change in changes {
            let fixture = try TypeReferenceSyntheticFixture.make(computedOverrides: change)
            let presentation = try XCTUnwrap(fixture.plan.presentation(sourceTypeObjectID: fixture.typeID))
            let reference = try XCTUnwrap(presentation.orderedReferences.first)
            guard case .unresolved(let reason) = reference.target else { return XCTFail("captured override became a provider") }
            XCTAssertEqual(reason, .capturedProviderContractMismatch)
            XCTAssertFalse(reference.isExecutable)
            XCTAssertNil(reference.descriptor["target"]?["ownerID"])
        }
        let fixture = try TypeReferenceSyntheticFixture.make()
        XCTAssertNil(fixture.plan.presentation(sourceTypeObjectID: "synthetic-type-\u{e1}"))
        let presentation = try XCTUnwrap(fixture.plan.presentation(sourceTypeObjectID: fixture.typeID))
        var root = try XCTUnwrap(presentation.descriptor.object)
        var details = try XCTUnwrap(root["originalDetails"]?.object)
        XCTAssertEqual(details["name"]?.string, "Synthetic Type \u{e1}")
        XCTAssertNotEqual(details["name"]?.string.map { Data($0.utf8) }, Data("Synthetic Type \u{e1}".utf8))
        details["name"] = .string("Synthetic Type \u{e1}"); root["originalDetails"] = .object(details)
        XCTAssertThrowsError(try presentation.requireExactDescriptor(.object(root)))
    }

    private func wire(_ value: AnyJSON?) throws -> Data {
        try AnyHostCanonical.bytes(XCTUnwrap(value), maximumBytes: 262_144)
    }
}

private struct TypeReferenceOriginalFixture {
    let retained: NativeCanonicalSupplementFixture
    let snapshots: [AnyHeartNativeSnapshotView]
    let catalog: AnyHeartNativeDefinitionCatalog
    let directory: AnyNativeImportedDefinitionDirectory

    static func load() throws -> Self {
        let environment = ProcessInfo.processInfo.environment
        guard environment["PINKHA_NATIVE_DEFINITION_RETAINED"] != nil,
              environment["PINKHA_NATIVE_ORIGINAL156"] != nil else {
            throw TypeReferenceFixtureError.missingQualifiedOriginalInputs
        }
        let retained = try NativeCanonicalSupplementFixture.load()
        let rows = try XCTUnwrap(retained.manifest["Objects"]?.array).filter {
            [Int64(521), 528, 529].contains($0["NativeType"]?.integer ?? -1)
        }
        let snapshots = try rows.map { row in
            try retained.evidence(XCTUnwrap(row["UniqueKey"]?.string)).snapshot
        }
        guard snapshots.count == 150 else { throw TypeReferenceFixtureError.originalIdentity }
        let source = retained.plan.source
        let catalog = try AnyHeartNativeDefinitionCatalog(sourceAccountID: source.accountID,
            sourceSpaceID: source.spaceID, captureManifestSHA256: source.captureManifestSHA256,
            sourceWitnessSHA256: source.witnessSHA256, snapshots: snapshots)
        let directory = try AnyNativeImportedDefinitionDirectory(plan: retained.plan, mappings: retained.mappings,
            supplementalCanonicalDefinitions: retained.bindings())
        return .init(retained: retained, snapshots: snapshots, catalog: catalog, directory: directory)
    }

    func references() throws -> AnyHeartNativeTypeReferencePlan { try .init(catalog: catalog, directory: directory) }

    func catalog(rows: [AnyHeartNativeSnapshotView], accountID: String? = nil) throws -> AnyHeartNativeDefinitionCatalog {
        try .init(sourceAccountID: accountID ?? retained.plan.source.accountID,
            sourceSpaceID: retained.plan.source.spaceID,
            captureManifestSHA256: retained.plan.source.captureManifestSHA256,
            sourceWitnessSHA256: retained.plan.source.witnessSHA256, snapshots: rows)
    }

    func requireUnchanged() throws {
        try retained.requireRetainedInputsUnchanged()
        for row in snapshots {
            let stem = "snapshot-" + AnyContentDigest.sha256(Data(row.sourceObjectID.utf8))
            let protobuf = try Data(contentsOf: retained.bundle.appendingPathComponent(stem + ".pb"))
            let json = try Data(contentsOf: retained.bundle.appendingPathComponent(stem + ".json"))
            guard protobuf == row.protobufBytes, json == row.jsonViewBytes else {
                throw TypeReferenceFixtureError.originalIdentity
            }
        }
    }
}

private enum TypeReferenceFixtureError: Error { case missingQualifiedOriginalInputs, originalIdentity }

private enum TypeReferenceTestWire {
    static func replacing(_ source: AnyHeartNativeSnapshotView, details: [String: AnyJSON] = [:],
                          protobufSuffix: Data = Data()) throws -> AnyHeartNativeSnapshotView {
        var view = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: source.jsonViewBytes).object)
        var snapshot = try XCTUnwrap(view["Snapshot"]?.object)
        var changed = try XCTUnwrap(snapshot["details"]?.object)
        changed.merge(details) { _, new in new }; snapshot["details"] = .object(changed)
        view["Snapshot"] = .object(snapshot)
        let bytes = source.protobufBytes + protobufSuffix
        view["SnapshotSHA256"] = .string(AnyContentDigest.sha256(bytes))
        view["SnapshotBytes"] = .integer(Int64(bytes.count))
        return try .init(jsonView: AnyDestinationDefinitionChecks.bytes(.object(view)), snapshotBytes: bytes,
            sourceSpaceID: source.sourceSpaceID, sourceObjectID: source.sourceObjectID)
    }
}

private struct TypeReferenceSyntheticFixture {
    let plan: AnyHeartNativeTypeReferencePlan
    let typeID: String
    let computedID: String
    let unknownID: String

    static func make(computedOverrides: [String: AnyJSON] = [:], recommendations: [String]? = nil) throws -> Self {
        let account = "synthetic-account", space = "synthetic-space", typeID = "synthetic-type-a\u{301}"
        let computedID = "synthetic-links", unknownID = "synthetic-unsupported", witness = String(repeating: "b", count: 64)
        func snapshot(_ id: String, kind: Int64, key: String, details: [String: AnyJSON]) throws -> AnyHeartNativeSnapshotView {
            let protobuf = Data(("SYNTHETIC-NOT-NATIVE:" + id).utf8)
            let value: AnyJSON = .object(["Contract": .string("pinkha-native-snapshot-json-v1"),
                "SpaceID": .string(space), "ObjectID": .string(id), "NativeType": .integer(kind), "UniqueKey": .string(key),
                "SnapshotSHA256": .string(AnyContentDigest.sha256(protobuf)), "SnapshotBytes": .integer(Int64(protobuf.count)),
                "Snapshot": .object(["blocks": .array([]), "details": .object(details),
                    "objectTypes": .array([]), "relationLinks": .array([])])])
            return try .init(jsonView: AnyDestinationDefinitionChecks.bytes(value), snapshotBytes: protobuf,
                sourceSpaceID: space, sourceObjectID: id)
        }
        var links: [String: AnyJSON] = ["name": .string("Links"), "description": .string("Outgoing links"),
            "relationKey": .string("links"), "relationFormat": .integer(100), "relationMaxCount": .integer(0),
            "relationReadonlyValue": .bool(true), "relationDefaultValue": .null,
            "relationFormatIncludeTime": .bool(false), "relationFormatObjectTypes": .array([])]
        links.merge(computedOverrides) { _, new in new }
        let rows = try [snapshot(typeID, kind: 528, key: "ot-synthetic", details: [
            "name": .string("Synthetic Type a\u{301}"), "recommendedLayout": .integer(7),
            "recommendedRelations": .array((recommendations ?? [computedID, unknownID, computedID]).map(AnyJSON.string)),
            "recommendedHiddenRelations": .array([]), "unknownFutureLayoutData": .object(["preserved": .bool(true)])]),
            snapshot(computedID, kind: 521, key: "rel-links", details: links),
            snapshot(unknownID, kind: 521, key: "rel-unsupported", details: ["name": .string("Unsupported"),
                "relationKey": .string("unsupported"), "relationFormat": .integer(102)])]
        let objects: [AnyJSON] = rows.map { row in
            let stem = "snapshot-" + AnyContentDigest.sha256(Data(row.sourceObjectID.utf8))
            return .object(["ObjectID": .string(row.sourceObjectID), "NativeType": .integer(row.nativeType),
                "UniqueKey": .string(row.uniqueKey), "Snapshot": .object(["Path": .string(stem + ".pb"),
                    "SHA256": .string(row.snapshotSHA256), "Bytes": .integer(Int64(row.protobufBytes.count))]),
                "NativeJSONView": .object(["Path": .string(stem + ".json"), "SHA256": .string(row.viewSHA256),
                    "Bytes": .integer(Int64(row.jsonViewBytes.count))])])
        }
        let accountSHA = AnyContentDigest.sha256(Data(account.utf8)), spaceSHA = AnyContentDigest.sha256(Data(space.utf8))
        let manifest = try AnyDestinationDefinitionChecks.bytes(.object([
            "Contract": .string("pinkha-native-whole-source-bundle-v1"), "Objects": .array(objects),
            "Receipt": .object(["Version": .string("loaded-account-native-space-source-v1"),
                "AccountSessionAuthorizedAtFinalCapture": .bool(true), "AllNativeHeadRowsAccounted": .bool(true),
                "CapturedSnapshotsBoundToUnchangedCheckpoint": .bool(true),
                "Inventory": .object(["SpaceSHA256": .string(spaceSHA), "SourceWitnessSHA256": .string(witness)]),
                "Source": .object(["accountSHA256": .string(accountSHA), "source": .object([
                    "accountSHA256": .string(accountSHA), "spaceSHA256": .string(spaceSHA),
                    "native": .object(["WitnessSHA256": .string(witness)])])])])]))
        let catalog = try AnyHeartNativeDefinitionCatalog(sourceAccountID: account, sourceSpaceID: space,
            captureManifestSHA256: AnyContentDigest.sha256(manifest), sourceWitnessSHA256: witness, snapshots: rows)
        let source = try AnyDestinationSourceBinding(accountID: account, spaceID: space, witnessSHA256: witness,
            captureManifestSHA256: AnyContentDigest.sha256(manifest), semanticPlanSHA256: catalog.contentSHA256,
            sourceObjectIDs: rows.map(\.sourceObjectID), definitionManifestBytes: manifest)
        let item = AnyDestinationMigrationItem(sourceKey: "synthetic-archive", sourceObjectID: typeID,
            operation: .typeDefinition(.init(xKey: "synthetic_archive", name: "Not an original Type mapping")))
        let original = try AnyDestinationMigrationPlan(source: source,
            workspace: .init(accountID: "synthetic-destination-account", spaceID: "synthetic-destination-space"),
            storeID: "synthetic-store", planID: String(repeating: "c", count: 64), coverage: rows.map { row in
                .init(sourceObjectID: row.sourceObjectID, disposition: row.sourceObjectID == typeID
                    ? .mapped(itemSourceKeys: [item.sourceKey]) : .blocked(reasons: ["synthetic representation control"]))
            }, items: [item])
        let identity = AnyContentDigest.sha256(AnyPreparedMigrationPlanBinding.material([
            "pinkha-native-prepared-migration-intent/v1", original.binding.workspace.accountID,
            original.binding.workspace.spaceID, original.binding.storeID, original.binding.planID,
            item.sourceKey, item.operation.kind]))
        let mapping = AnyDestinationMigrationMapping(sourceKey: item.sourceKey, sourceObjectID: typeID,
            kind: item.operation.kind, intentID: identity, objectID: "synthetic-archive-object",
            recordIDs: ["synthetic-archive-object"], fileID: nil, fingerprint: String(repeating: "d", count: 64),
            signedChangeIDs: ["synthetic-not-native-change"], currentReceiptSHA256: String(repeating: "e", count: 64))
        let directory = try AnyNativeImportedDefinitionDirectory(plan: original, mappings: [mapping])
        return .init(plan: try .init(catalog: catalog, directory: directory),
            typeID: typeID, computedID: computedID, unknownID: unknownID)
    }
}
