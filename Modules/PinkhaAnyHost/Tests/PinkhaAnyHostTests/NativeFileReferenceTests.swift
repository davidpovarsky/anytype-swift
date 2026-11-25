import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyHost

final class NativeFileReferenceTests: XCTestCase {
    func testCanonicalFileNamespaceRetainsExactSpaceAndFileIdentity() throws {
        let value = try AnyNativeFileReference(spaceID: "space-123.1", fileID: "file_ABC~9")
        XCTAssertEqual(value.uri, "any://f/space-123.1/file_ABC~9")
        XCTAssertEqual(try AnyNativeFileReference(uri: value.uri), value)
        XCTAssertEqual(try JSONDecoder().decode(AnyNativeFileReference.self, from: JSONEncoder().encode(value)), value)
        XCTAssertNotEqual(value.uri, "any://file_ABC~9")
        XCTAssertNotEqual(try AnyNativeFileReference(spaceID: "other", fileID: value.fileID).uri, value.uri)
    }

    func testFileIdentityRejectsCredentialsVariantsEscapesAndForeignNamespaces() throws {
        for uri in [
            "any://file", "any://o/space/file", "any://F/space/file", "ANY://f/space/file",
            "https://127.0.0.1/space/file", "any://f/space/file?variant=thumb", "any://f/space/file?token=secret",
            "any://f/space/file#fragment", "any://f/space/%66ile", "any://f/space/../file", "any://f//file",
            "any://f/space/", "any://f/space/file/", "any://f/space\\other/file", "any://f/sp ace/file",
            "any://f/space/file%2Fextra", "any://f/space/..", "any://f/space/.", "any://f/space/שלום"
        ] { XCTAssertThrowsError(try AnyNativeFileReference(uri: uri), uri) }
        XCTAssertThrowsError(try AnyNativeFileReference(spaceID: "space", fileID: String(repeating: "a", count: 1_025)))
        XCTAssertThrowsError(try JSONDecoder().decode(AnyNativeFileReference.self,
            from: Data(#"{"spaceID":"space","fileID":"file?token=secret"}"#.utf8)))
    }

    func testFilePropertyDescriptorKeepsNativeArrayAndRejectsWrongValueKinds() throws {
        var fields: [String: AnyJSON] = ["id": .string("file-property"), "kind": .string("array"), "scope": .string("synced"),
            "xFormat": .object(AnyNativeFilePropertyFormat.descriptor(multiple: false))]
        let definition = try AnyNativePropertyDefinition(ownerID: "owner", raw: .object(fields))
        let format = try XCTUnwrap(definition.fileFormat)
        XCTAssertFalse(format.multiple)
        let uri = "any://f/space/file"
        XCTAssertEqual(try format.references(in: .array([.string(uri)])).map(\.uri), [uri])
        XCTAssertTrue(definition.accepts(.array([])))
        XCTAssertTrue(definition.accepts(.null), "Native null remains unset, distinct from an empty file array")
        XCTAssertFalse(definition.accepts(.array([.string(uri), .string(uri)])))
        XCTAssertFalse(definition.accepts(.array([.string("any://object")])))
        XCTAssertFalse(definition.accepts(.array([.integer(1)])))
        fields["kind"] = .string("string")
        XCTAssertThrowsError(try AnyNativePropertyDefinition(ownerID: "owner", raw: .object(fields)))
        fields["kind"] = .string("array")
        for invalid in [
            AnyJSON.object(["type": .string("pinkha-file"), "links": .string("links")]),
            .object(["type": .string("relation"), "links": .string("links"), "config": .object(["multiple": .bool(false)]),
                     "pinkhaFile": .object(["contract": .string(AnyNativeFilePropertyFormat.contract)])]),
            .object(["type": .string("pinkha-file"), "links": .string("none"), "config": .object(["multiple": .bool(false)]),
                     "pinkhaFile": .object(["contract": .string(AnyNativeFilePropertyFormat.contract)])])
        ] {
            fields["xFormat"] = invalid
            XCTAssertThrowsError(try AnyNativePropertyDefinition(ownerID: "owner", raw: .object(fields)))
        }
    }

    func testFileReferencesRequireFileSlotsAndObjectReferencesRequireObjects() throws {
        let valid: AnyDestinationReference = .mapped(sourceKey: "file", slot: .fileID, encoding: .fileURI)
        XCTAssertNoThrow(try AnyDestinationPlanChecks.reference(valid))
        XCTAssertTrue(try AnyDestinationPlanChecks.placeholder(valid).hasPrefix("any://f/validation-space/"))
        let invalid: [AnyDestinationReference] = [
            .mapped(sourceKey: "file", slot: .fileID, encoding: .anyURI),
            .mapped(sourceKey: "object", slot: .objectID, encoding: .fileURI),
            .mapped(sourceKey: "record", slot: .record(index: 0), encoding: .fileURI),
            .mapped(sourceKey: "record", slot: .record(index: 0), encoding: .anyURI)
        ]
        for reference in invalid { XCTAssertThrowsError(try AnyDestinationPlanChecks.reference(reference)) }
        let slots: [AnyDestinationReference.Slot] = [.objectID, .fileID, .record(index: 0)]
        for slot in slots {
            XCTAssertNoThrow(try AnyDestinationPlanChecks.reference(.mapped(sourceKey: "known", slot: slot, encoding: .rawID)))
        }
    }
}
