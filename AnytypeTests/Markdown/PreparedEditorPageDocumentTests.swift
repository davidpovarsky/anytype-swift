import Foundation
import Testing
@testable import Anytype

@MainActor
@Suite
struct PreparedEditorPageDocumentTests {
    @Test
    func acceptsTheSameOpenedDocumentInEachOriginalMode() throws {
        for mode in [DocumentMode.handling, .preview, .version("version-one")] {
            let document = MockBaseDocument(objectId: "original-object")
            document.mockSpaceId = "original-space"
            document.mockMode = mode
            let data = EditorPageObject(objectId: document.objectId, spaceId: document.spaceId, mode: mode)
            try PreparedEditorPageDocument.validate(data: data, document: document)
        }
    }

    @Test
    func rejectsAnotherObjectWithTheSameSpace() {
        expectRejection(.objectMismatch, data: EditorPageObject(objectId: "other", spaceId: "space"))
    }

    @Test
    func rejectsAnotherSpaceWithTheSameObject() {
        expectRejection(.spaceMismatch, data: EditorPageObject(objectId: "object", spaceId: "other"))
    }

    @Test
    func rejectsAnotherModeAndAnotherVersion() {
        expectRejection(.modeMismatch, data: EditorPageObject(objectId: "object", spaceId: "space", mode: .preview))
        expectRejection(
            .modeMismatch,
            data: EditorPageObject(objectId: "object", spaceId: "space", mode: .version("second")),
            mode: .version("first")
        )
    }

    @Test
    func rejectsEmptyIdentitiesWithoutNormalizingDifferentIdentifiers() {
        for value in ["", " ", "\n\t"] {
            expectRejection(.emptyIdentity, data: EditorPageObject(objectId: value, spaceId: "space"))
            expectRejection(.emptyIdentity, data: EditorPageObject(objectId: "object", spaceId: value))
        }
        expectRejection(.objectMismatch, data: EditorPageObject(objectId: " object ", spaceId: "space"))
    }

    @Test
    func rechecksTheActualDocumentAfterItHasClosed() throws {
        let document = MockBaseDocument(objectId: "object")
        document.mockSpaceId = "space"
        let data = EditorPageObject(objectId: "object", spaceId: "space")
        try PreparedEditorPageDocument.validate(data: data, document: document)
        document.mockIsOpened = false
        do {
            try PreparedEditorPageDocument.validate(data: data, document: document)
            Issue.record("A closed prepared document was admitted")
        } catch {
            #expect(error as? PreparedEditorPageDocumentError == .documentNotOpened)
        }
    }

    private func expectRejection(
        _ expected: PreparedEditorPageDocumentError,
        data: EditorPageObject,
        mode: DocumentMode = .handling
    ) {
        let document = MockBaseDocument(objectId: "object")
        document.mockSpaceId = "space"
        document.mockMode = mode
        do {
            try PreparedEditorPageDocument.validate(data: data, document: document)
            Issue.record("Prepared document identity was not rejected")
        } catch {
            #expect(error as? PreparedEditorPageDocumentError == expected)
        }
    }
}
