import Foundation
import Testing
import PinkhaKit
import ProtobufMessages
import SwiftProtobuf

@Suite
struct OriginalAnnotationNativeMetadataTests {
    @Test func testNativeDescriptorUsesLosslessStringStorageAndDelimiterSafeSchemaKeys() throws {
        let parts = OriginalAnnotationNativeMetadata.originalTypeUniqueKey.split(
            separator: "-", omittingEmptySubsequences: false
        )
        #expect(parts.count == 2)
        #expect(parts.first == "ot")
        #expect(parts.last?.isEmpty == false)
        #expect(OriginalAnnotationMetadataField.allCases.count == 17)
        for field in OriginalAnnotationMetadataField.allCases {
            let relation = ("rel-" + field.rawValue).split(separator: "-", omittingEmptySubsequences: false)
            #expect(relation.count == 2)
            #expect(relation.first == "rel")
            #expect(relation.last?.isEmpty == false)
        }
        #expect(OriginalAnnotationNativeMetadata.relationFormat == .longtext)
        #expect(OriginalAnnotationNativeMetadata.relationFormat != .shorttext)
        #expect(OriginalAnnotationNativeMetadata.relationFormat != .number)
        #expect(Anytype_Model_RelationFormat.longtext.rawValue == 0)
        let beyondDouble: Int64 = 9_007_199_254_740_993
        #expect(Double(exactly: beyondDouble) == nil)
        #expect(Double(exactly: Int64.max) == nil)
        let original = valueString(String(Int64.max))
        let roundTrip = try Google_Protobuf_Value(serializedBytes: original.serializedData())
        #expect(roundTrip.kind == .stringValue("9223372036854775807"))
    }

    @Test func testRealBinaryProtobufRoundTripPreservesExactCandidate() throws {
        let input = fixture(applied: true)
        let data = try encoded(input)
        let decoded = try Google_Protobuf_Struct(serializedBytes: data)
        let result = try OriginalAnnotationNativeMetadata.decode(decoded, rootID: "native-root")
        #expect(decoded == input)
        #expect(result.identity.objectID == "native-root")
        let scope = try expectedScope()
        #expect(result.identity.scope == scope)
        #expect(result.nativeTypeID == "native-annotation-type")
        #expect(result.creationCommitment.revision == 17)
        #expect(result.creationCommitment.sourceDigest == String(repeating: "c", count: 64))
        #expect(result.creationCommitment.payloadDigest == String(repeating: "d", count: 64))
        let applied = try #require(result.appliedCommitment)
        #expect(applied.revision == 18)
        #expect(applied.sourceDigest == String(repeating: "e", count: 64))
        #expect(applied.payloadDigest == String(repeating: "f", count: 64))
        #expect(result.nativeSnapshotDigest == nil)
    }

    @Test func testNativeRootIdentityMatchesByteExactlyAndIsNonempty() throws {
        #expect(throws: OriginalAnnotationMetadataError.wrongRoot) {
            try OriginalAnnotationNativeMetadata.decode(fixture(), rootID: "NATIVE-ROOT")
        }
        #expect(throws: OriginalAnnotationMetadataError.wrongRoot) {
            try OriginalAnnotationNativeMetadata.decode(fixture(), rootID: "")
        }
        var empty = fixture()
        empty.fields["id"] = valueString("")
        #expect(throws: TorahAnnotationNativeContractError.invalidObjectIdentity) {
            try OriginalAnnotationNativeMetadata.decode(empty, rootID: "")
        }
    }

    @Test func testNativeSpaceMatchesCreatorSpaceByteExactly() throws {
        for space in ["NATIVE-SPACE", "another-space", ""] {
            var input = fixture()
            input.fields["spaceId"] = valueString(space)
            #expect(throws: OriginalAnnotationMetadataError.wrongNativeSpace) {
                try OriginalAnnotationNativeMetadata.decode(input, rootID: "native-root")
            }
        }
    }

    @Test func testNativeTypeRequiresExactlyOneString() throws {
        let invalid: [Google_Protobuf_Value] = [
            valueList([]), valueList([valueString("native-annotation-type"), valueString("native-annotation-type")]),
            valueList([valueNumber(1)]), valueList([valueNull()]),
            valueString("native-annotation-type"), valueNull(), Google_Protobuf_Value()
        ]
        for value in invalid {
            var input = fixture()
            input.fields["type"] = value
            #expect(throws: OriginalAnnotationMetadataError.malformedNativeType) {
                try OriginalAnnotationNativeMetadata.decode(input, rootID: "native-root")
            }
        }
    }

    @Test func testNativeTypeIDUsesExistingIdentifierBounds() throws {
        for type in ["", "not a type", "סוג", String(repeating: "a", count: 513)] {
            var input = fixture()
            input.fields["type"] = valueList([valueString(type)])
            #expect(throws: TorahAnnotationNativeContractError.invalidObjectIdentity) {
                try OriginalAnnotationNativeMetadata.decode(input, rootID: "native-root")
            }
        }
        var input = fixture()
        input.fields["type"] = valueList([valueString(String(repeating: "a", count: 512))])
        let observed = try OriginalAnnotationNativeMetadata.decode(input, rootID: "native-root")
        #expect(observed.nativeTypeID == String(repeating: "a", count: 512))
        #expect(TorahAnnotationCreateRecovery.assessIdentity(
            commitment: observed.creationCommitment, expectedIdentity: observed.identity,
            candidate: observed, annotationTypeID: "native-annotation-type", ownerIsCurrent: true
        ) == .conflict(.annotationTypeMismatch))
    }

    @Test func testProtocolRejectsUnknownVersions() throws {
        for marker in ["", "pinkha.torah.annotation/2", "Pinkha.torah.annotation/1", "annotation"] {
            var input = fixture()
            input.fields["pinkhaTorahAnnotationProtocol"] = valueString(marker)
            #expect(throws: OriginalAnnotationMetadataError.unsupportedProtocol) {
                try OriginalAnnotationNativeMetadata.decode(input, rootID: "native-root")
            }
        }
    }

    @Test func testEveryRequiredMarkerIsRequired() throws {
        for key in requiredMarkers {
            var input = fixture()
            input.fields.removeValue(forKey: key)
            #expect(throws: OriginalAnnotationMetadataError.missingOrMalformedField(key)) {
                try OriginalAnnotationNativeMetadata.decode(input, rootID: "native-root")
            }
        }
    }

    @Test func testRequiredMarkersRejectNonStringProtobufKinds() throws {
        for key in requiredMarkers {
            for value in nonStringValues {
                var input = fixture()
                input.fields[key] = value
                #expect(throws: OriginalAnnotationMetadataError.missingOrMalformedField(key)) {
                    try OriginalAnnotationNativeMetadata.decode(input, rootID: "native-root")
                }
            }
        }
    }

    @Test func testNativeFieldsRejectMissingAndMalformedKinds() throws {
        for key in ["id", "spaceId"] {
            var missing = fixture()
            missing.fields.removeValue(forKey: key)
            #expect(throws: OriginalAnnotationMetadataError.missingOrMalformedField(key)) {
                try OriginalAnnotationNativeMetadata.decode(missing, rootID: "native-root")
            }
            for value in nonStringValues {
                var input = fixture()
                input.fields[key] = value
                #expect(throws: OriginalAnnotationMetadataError.missingOrMalformedField(key)) {
                    try OriginalAnnotationNativeMetadata.decode(input, rootID: "native-root")
                }
            }
        }
        var noType = fixture()
        noType.fields.removeValue(forKey: "type")
        #expect(throws: OriginalAnnotationMetadataError.malformedNativeType) {
            try OriginalAnnotationNativeMetadata.decode(noType, rootID: "native-root")
        }
    }

    @Test func testCanonicalUUIDsRetainExistingMessageAsAttempt() throws {
        let observed = try OriginalAnnotationNativeMetadata.decode(fixture(applied: true), rootID: "native-root")
        let annotation = try #require(UUID(uuidString: annotationUUID))
        let creationMessage = try #require(UUID(uuidString: creationMessageID))
        let creationMutation = try #require(UUID(uuidString: creationMutationID))
        let appliedMessage = try #require(UUID(uuidString: appliedMessageID))
        let appliedMutation = try #require(UUID(uuidString: appliedMutationID))
        #expect(observed.identity.scope.annotationUUID == annotation)
        #expect(observed.creationCommitment.messageID == creationMessage)
        #expect(observed.creationCommitment.mutationID == creationMutation)
        #expect(observed.creationAttemptID == creationMessage)
        let applied = try #require(observed.appliedCommitment)
        #expect(applied.messageID == appliedMessage)
        #expect(applied.mutationID == appliedMutation)
    }

    @Test func testNoncanonicalUUIDSpellingsRejected() throws {
        for key in uuidFields {
            let initial = fixture(applied: true)
            let canonical = try #require(initial.fields[key]?.stringValue)
            for spelling in [canonical.lowercased(), " " + canonical, canonical + " ",
                             "{" + canonical + "}", canonical.replacingOccurrences(of: "-", with: ""), "invalid"] {
                var input = initial
                input.fields[key] = valueString(spelling)
                #expect(throws: OriginalAnnotationMetadataError.noncanonicalUUID(key)) {
                    try OriginalAnnotationNativeMetadata.decode(input, rootID: "native-root")
                }
            }
        }
    }

    @Test func testRevisionPreservesIntegersBeyondDoubleAndInt64Max() throws {
        let revisions: [Int64] = [1, 9_007_199_254_740_993, Int64.max]
        for revision in revisions {
            var input = fixture(applied: true)
            input.fields["pinkhaTorahAnnotationCreationRevision"] = valueString(String(revision))
            input.fields["pinkhaTorahAnnotationAppliedRevision"] = valueString(String(revision))
            let wire = try encoded(input)
            let actual = try OriginalAnnotationNativeMetadata.decode(
                Google_Protobuf_Struct(serializedBytes: wire), rootID: "native-root"
            )
            #expect(actual.creationCommitment.revision == revision)
            #expect(actual.appliedCommitment?.revision == revision)
        }
    }

    @Test func testRevisionRejectsNoncanonicalOrOutOfRangeDecimal() throws {
        let invalid = ["", "0", "-1", "+1", "01", "1.0", "1e3", " 1", "1 ",
                       "１２", "١", "9223372036854775808", "18446744073709551616"]
        for key in revisionFields {
            for text in invalid {
                var input = fixture(applied: true)
                input.fields[key] = valueString(text)
                #expect(throws: OriginalAnnotationMetadataError.invalidRevision(key)) {
                    try OriginalAnnotationNativeMetadata.decode(input, rootID: "native-root")
                }
            }
        }
    }

    @Test func testRevisionRejectsNativeNumberKind() throws {
        for key in revisionFields {
            for number in [1.0, 9_007_199_254_740_992.0, Double(Int64.max)] {
                var input = fixture(applied: true)
                input.fields[key] = valueNumber(number)
                #expect(throws: OriginalAnnotationMetadataError.missingOrMalformedField(key)) {
                    try OriginalAnnotationNativeMetadata.decode(input, rootID: "native-root")
                }
            }
        }
    }

    @Test func testScopeIdentifiersUseExistingCaseSensitiveBounds() throws {
        let fields = ["pinkhaTorahAnnotationCreationDestination", "pinkhaTorahAnnotationCreationAccount",
                      "pinkhaTorahAnnotationCreationSpace", "pinkhaTorahAnnotationNamespace"]
        for key in fields {
            for bad in ["", "contains space", "חשבון", "slash/value", String(repeating: "a", count: 513)] {
                var input = fixture()
                input.fields[key] = valueString(bad)
                #expect(throws: TorahAnnotationNativeContractError.invalidScope) {
                    try OriginalAnnotationNativeMetadata.decode(input, rootID: "native-root")
                }
            }
        }
        var input = fixture()
        let account = String(repeating: "A", count: 512)
        input.fields["pinkhaTorahAnnotationCreationAccount"] = valueString(account)
        input.fields["pinkhaTorahAnnotationCreationDestination"] = valueString("Exact.Destination:_-09")
        let observed = try OriginalAnnotationNativeMetadata.decode(input, rootID: "native-root")
        #expect(observed.identity.scope.account == account)
        #expect(observed.identity.scope.destination == "Exact.Destination:_-09")
    }

    @Test func testCommitmentDigestsUseExactLowercaseSHA256Grammar() throws {
        let fields = ["pinkhaTorahAnnotationCreationSourceDigest", "pinkhaTorahAnnotationCreationPayloadDigest",
                      "pinkhaTorahAnnotationAppliedSourceDigest", "pinkhaTorahAnnotationAppliedPayloadDigest"]
        for key in fields {
            for invalid in [String(repeating: "A", count: 64), String(repeating: "g", count: 64),
                            String(repeating: "a", count: 63), String(repeating: "a", count: 65)] {
                var input = fixture(applied: true)
                input.fields[key] = valueString(invalid)
                #expect(throws: TorahAnnotationNativeContractError.invalidCommitment) {
                    try OriginalAnnotationNativeMetadata.decode(input, rootID: "native-root")
                }
            }
        }
    }

    @Test func testForeignCreatorScopeIsPreservedForConflictAssessment() throws {
        var input = fixture()
        input.fields["pinkhaTorahAnnotationCreationDestination"] = valueString("foreign-destination")
        input.fields["pinkhaTorahAnnotationCreationAccount"] = valueString("foreign-account")
        let observed = try OriginalAnnotationNativeMetadata.decode(input, rootID: "native-root")
        #expect(observed.identity.scope.destination == "foreign-destination")
        #expect(observed.identity.scope.account == "foreign-account")
        let scope = try expectedScope()
        let message = try #require(UUID(uuidString: creationMessageID))
        let mutation = try #require(UUID(uuidString: creationMutationID))
        let local = try TorahAnnotationNativeCommitment(
            scope: scope, messageID: message, mutationID: mutation, revision: 17,
            sourceDigest: String(repeating: "c", count: 64), payloadDigest: String(repeating: "d", count: 64)
        )
        #expect(TorahAnnotationCreateRecovery.assessCreation(
            commitment: local, purpose: .annotation, attempt: nil, mapping: nil, candidates: [observed],
            annotationTypeID: "native-annotation-type", ownerIsCurrent: true
        ) == .conflict(.scopeMismatch))
    }

    @Test func testPromotedClassificationRemainsExplicitConflict() throws {
        for writing in [TorahAnnotationPromotedWritingType.chiddush, .article, .research] {
            var input = fixture()
            input.fields["pinkhaTorahAnnotationClassification"] = valueString(writing.rawValue)
            let observed = try OriginalAnnotationNativeMetadata.decode(input, rootID: "native-root")
            #expect(observed.classification == .promotedDocument(writing))
            #expect(observed.classification.isDocument)
            #expect(TorahAnnotationCreateRecovery.assessCreation(
                commitment: observed.creationCommitment, purpose: .annotation, attempt: nil, mapping: nil,
                candidates: [observed], annotationTypeID: "native-annotation-type", ownerIsCurrent: true
            ) == .conflict(.promotionRequiresExplicitResolution))
        }
    }

    @Test func testUnknownClassificationNeverFallsBackToNote() throws {
        for classification in ["note", "document", "Article", "", "annotation "] {
            var input = fixture()
            input.fields["pinkhaTorahAnnotationClassification"] = valueString(classification)
            #expect(throws: OriginalAnnotationMetadataError.unsupportedClassification) {
                try OriginalAnnotationNativeMetadata.decode(input, rootID: "native-root")
            }
        }
    }

    @Test func testNativeStateAbsentDefaultsFalseAndPresentRequiresBool() throws {
        let absent = try OriginalAnnotationNativeMetadata.decode(fixture(), rootID: "native-root")
        #expect(absent.objectState == .present)
        for key in ["isArchived", "isDeleted"] {
            var present = fixture()
            present.fields[key] = valueBool(false)
            #expect(try OriginalAnnotationNativeMetadata.decode(present, rootID: "native-root").objectState == .present)
            for value in [valueString("false"), valueNumber(0), valueNull(), valueList([]),
                          valueObject([:]), Google_Protobuf_Value()] {
                var input = fixture()
                input.fields[key] = value
                #expect(throws: OriginalAnnotationMetadataError.missingOrMalformedField(key)) {
                    try OriginalAnnotationNativeMetadata.decode(input, rootID: "native-root")
                }
            }
        }
    }

    @Test func testArchivedDeletedStateIsRetained() throws {
        let cases: [(Bool, Bool, TorahAnnotationNativeObjectState)] = [
            (false, false, .present), (true, false, .archived), (false, true, .deleted), (true, true, .deleted)
        ]
        for (archived, deleted, expected) in cases {
            var input = fixture()
            input.fields["isArchived"] = valueBool(archived)
            input.fields["isDeleted"] = valueBool(deleted)
            let observed = try OriginalAnnotationNativeMetadata.decode(input, rootID: "native-root")
            #expect(observed.objectState == expected)
            if expected != .present {
                #expect(TorahAnnotationCreateRecovery.assessIdentity(
                    commitment: observed.creationCommitment, expectedIdentity: observed.identity,
                    candidate: observed, annotationTypeID: "native-annotation-type", ownerIsCurrent: true
                ) == .conflict(.nativeObjectUnavailable))
            }
        }
    }

    @Test func testAppliedCommitmentRequiresAllFiveOrNone() throws {
        #expect(try OriginalAnnotationNativeMetadata.decode(fixture(), rootID: "native-root").appliedCommitment == nil)
        #expect(try OriginalAnnotationNativeMetadata.decode(fixture(applied: true), rootID: "native-root").appliedCommitment != nil)
        for mask in 1..<31 {
            var input = fixture(applied: true)
            for (offset, key) in appliedFields.enumerated() where mask & (1 << offset) == 0 {
                input.fields.removeValue(forKey: key)
            }
            #expect(throws: OriginalAnnotationMetadataError.incompleteAppliedCommitment) {
                try OriginalAnnotationNativeMetadata.decode(input, rootID: "native-root")
            }
        }
    }

    @Test func testAppliedCommitmentRejectsMalformedValues() throws {
        for key in appliedFields {
            for value in nonStringValues {
                var input = fixture(applied: true)
                input.fields[key] = value
                #expect(throws: OriginalAnnotationMetadataError.missingOrMalformedField(key)) {
                    try OriginalAnnotationNativeMetadata.decode(input, rootID: "native-root")
                }
            }
        }
    }

    @Test func testCopiedSnapshotMarkersCannotProveAppliedBody() throws {
        var input = fixture()
        for (applied, creation) in zip(appliedFields, creationCommitmentFields) {
            input.fields[applied] = try #require(input.fields[creation])
        }
        for key in ["nativeSnapshotDigest", "pinkhaTorahAnnotationNativeSnapshotDigest",
                    "pinkhaTorahAnnotationAppliedSnapshotDigest"] {
            input.fields[key] = valueString(String(repeating: "a", count: 64))
        }
        let observed = try OriginalAnnotationNativeMetadata.decode(input, rootID: "native-root")
        #expect(observed.appliedCommitment == observed.creationCommitment)
        #expect(observed.nativeSnapshotDigest == nil)
        #expect(TorahAnnotationCreateRecovery.assessApplied(
            commitment: observed.creationCommitment, expectedIdentity: observed.identity,
            candidate: observed, annotationTypeID: "native-annotation-type", ownerIsCurrent: true
        ) == .bodyApplicationUnproven)
    }

    @Test func testDecodePreservesOpaqueBodySourceAndUnknownWireFields() throws {
        var input = fixture(applied: true)
        input.fields["opaqueBody"] = valueString("אבג\u{0000} rich body\n\u{1F4DA} exact retained bytes")
        input.fields["sourceWitness"] = valueObject([
            "future": valueList([valueNumber(3.25), valueNull(), valueBool(true)]),
            "raw": valueString("unchanged source: \\ literal")
        ])
        input.fields["futureMetadata"] = valueObject(["unknown": valueString("retained")])
        var wire = try encoded(input)
        let unknown = Data([0xA0, 0x06, 0x07])
        wire.append(unknown)
        let original = try Google_Protobuf_Struct(serializedBytes: wire)
        #expect(original.unknownFields.data == unknown)
        let before = try encoded(original)
        let beforeFields = original.fields
        _ = try OriginalAnnotationNativeMetadata.decode(original, rootID: "native-root")
        #expect(original.fields == beforeFields)
        #expect(original.unknownFields.data == unknown)
        #expect(try encoded(original) == before)
        #expect(original.fields["opaqueBody"] == input.fields["opaqueBody"])
        #expect(original.fields["sourceWitness"] == input.fields["sourceWitness"])
        #expect(original.fields["futureMetadata"] == input.fields["futureMetadata"])
    }
}

private let annotationUUID = "123E4567-E89B-12D3-A456-426614174000"
private let creationMessageID = "123E4567-E89B-12D3-A456-426614174001"
private let creationMutationID = "123E4567-E89B-12D3-A456-426614174002"
private let appliedMessageID = "123E4567-E89B-12D3-A456-426614174003"
private let appliedMutationID = "123E4567-E89B-12D3-A456-426614174004"

private let requiredMarkers = [
    "pinkhaTorahAnnotationProtocol", "pinkhaTorahAnnotationClassification",
    "pinkhaTorahAnnotationNamespace", "pinkhaTorahAnnotationUUID",
    "pinkhaTorahAnnotationCreationDestination", "pinkhaTorahAnnotationCreationAccount",
    "pinkhaTorahAnnotationCreationSpace", "pinkhaTorahAnnotationCreationMessageID",
    "pinkhaTorahAnnotationCreationMutationID", "pinkhaTorahAnnotationCreationRevision",
    "pinkhaTorahAnnotationCreationSourceDigest", "pinkhaTorahAnnotationCreationPayloadDigest"
]
private let uuidFields = [
    "pinkhaTorahAnnotationUUID", "pinkhaTorahAnnotationCreationMessageID",
    "pinkhaTorahAnnotationCreationMutationID", "pinkhaTorahAnnotationAppliedMessageID",
    "pinkhaTorahAnnotationAppliedMutationID"
]
private let revisionFields = ["pinkhaTorahAnnotationCreationRevision", "pinkhaTorahAnnotationAppliedRevision"]
private let creationCommitmentFields = [
    "pinkhaTorahAnnotationCreationMessageID", "pinkhaTorahAnnotationCreationMutationID",
    "pinkhaTorahAnnotationCreationRevision", "pinkhaTorahAnnotationCreationSourceDigest",
    "pinkhaTorahAnnotationCreationPayloadDigest"
]
private let appliedFields = [
    "pinkhaTorahAnnotationAppliedMessageID", "pinkhaTorahAnnotationAppliedMutationID",
    "pinkhaTorahAnnotationAppliedRevision", "pinkhaTorahAnnotationAppliedSourceDigest",
    "pinkhaTorahAnnotationAppliedPayloadDigest"
]
private var nonStringValues: [Google_Protobuf_Value] {
    [valueNumber(17), valueBool(false), valueNull(), valueList([]), valueObject([:]), Google_Protobuf_Value()]
}

private func fixture(applied: Bool = false) -> Google_Protobuf_Struct {
    var fields: [String: Google_Protobuf_Value] = [
        "id": valueString("native-root"), "spaceId": valueString("native-space"),
        "type": valueList([valueString("native-annotation-type")]),
        "pinkhaTorahAnnotationProtocol": valueString("pinkha.torah.annotation/1"),
        "pinkhaTorahAnnotationClassification": valueString("annotation"),
        "pinkhaTorahAnnotationNamespace": valueString("Torah:Annotations"),
        "pinkhaTorahAnnotationUUID": valueString(annotationUUID),
        "pinkhaTorahAnnotationCreationDestination": valueString("original-anytype"),
        "pinkhaTorahAnnotationCreationAccount": valueString("actual-account"),
        "pinkhaTorahAnnotationCreationSpace": valueString("native-space"),
        "pinkhaTorahAnnotationCreationMessageID": valueString(creationMessageID),
        "pinkhaTorahAnnotationCreationMutationID": valueString(creationMutationID),
        "pinkhaTorahAnnotationCreationRevision": valueString("17"),
        "pinkhaTorahAnnotationCreationSourceDigest": valueString(String(repeating: "c", count: 64)),
        "pinkhaTorahAnnotationCreationPayloadDigest": valueString(String(repeating: "d", count: 64))
    ]
    if applied {
        fields["pinkhaTorahAnnotationAppliedMessageID"] = valueString(appliedMessageID)
        fields["pinkhaTorahAnnotationAppliedMutationID"] = valueString(appliedMutationID)
        fields["pinkhaTorahAnnotationAppliedRevision"] = valueString("18")
        fields["pinkhaTorahAnnotationAppliedSourceDigest"] = valueString(String(repeating: "e", count: 64))
        fields["pinkhaTorahAnnotationAppliedPayloadDigest"] = valueString(String(repeating: "f", count: 64))
    }
    return Google_Protobuf_Struct.with { $0.fields = fields }
}

private func expectedScope() throws -> TorahAnnotationNativeScope {
    let annotation = try #require(UUID(uuidString: annotationUUID))
    return try TorahAnnotationNativeScope(
        destination: "original-anytype", account: "actual-account", space: "native-space",
        namespace: "Torah:Annotations", annotationUUID: annotation
    )
}

private func valueString(_ value: String) -> Google_Protobuf_Value { .with { $0.stringValue = value } }
private func valueNumber(_ value: Double) -> Google_Protobuf_Value { .with { $0.numberValue = value } }
private func valueBool(_ value: Bool) -> Google_Protobuf_Value { .with { $0.boolValue = value } }
private func valueNull() -> Google_Protobuf_Value { .with { $0.nullValue = .nullValue } }
private func valueList(_ values: [Google_Protobuf_Value]) -> Google_Protobuf_Value {
    .with { $0.listValue = .with { $0.values = values } }
}
private func valueObject(_ fields: [String: Google_Protobuf_Value]) -> Google_Protobuf_Value {
    .with { $0.structValue = .with { $0.fields = fields } }
}
private func encoded(_ value: Google_Protobuf_Struct) throws -> Data {
    var options = BinaryEncodingOptions()
    options.useDeterministicOrdering = true
    return try value.serializedData(options: options)
}
