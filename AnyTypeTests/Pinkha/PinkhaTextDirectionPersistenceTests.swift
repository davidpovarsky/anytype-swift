import PinkhaKit
import ProtobufMessages
import Services
import SwiftProtobuf
import Testing
import UIKit
@testable import Anytype

@Suite("App-wide text-direction persistence", .serialized)
@MainActor
struct PinkhaTextDirectionPersistenceTests {
    @Test("Explicit alignment is committed before metadata in an ordinary Page")
    func explicitAlignmentOrderingAndFailureIsolation() async throws {
        PinkhaTextDirectionPersistence.resetForTesting()
        let blockId = "ordinary-explicit-alignment"
        let document = makeDocument(blockId: blockId, typeId: "ordinary-page-type")
        let service = RecordingBlockService(failFieldWrites: true)
        Container.shared.blockService.register { service }
        defer {
            Container.shared.blockService.reset()
            PinkhaTextDirectionPersistence.resetForTesting()
        }

        let handler = BlockActionHandler(
            document: document,
            markupChanger: BlockMarkupChangerMock(),
            service: BlockActionServiceMock()
        )
        handler.setAlignment(.right, blockIds: [blockId])

        for _ in 0..<100 {
            if await service.eventCount >= 2 { break }
            try await Task.sleep(for: .milliseconds(10))
        }

        let events = await service.events
        let lastFields = await service.lastFields
        #expect(events == [.alignment(.right), .fields])
        #expect(PinkhaTextDirectionPersistence.sessionExplicitAlignment(blockId: blockId) == .right)
        #expect(lastFields?["existing"]?.stringValue == "preserved")
        let marker = try #require(lastFields?[PinkhaSchemaRoles.blockTextDirectionField])
        #expect(PinkhaTextDirectionMarker(storedValue: marker.stringValue) == .explicit(.right))
    }

    @Test("Explicit metadata restores the choice in an ordinary Note")
    func explicitAlignmentColdReopen() async throws {
        PinkhaTextDirectionPersistence.resetForTesting()
        let blockId = "ordinary-note-write"
        let document = makeDocument(blockId: blockId, typeId: "ordinary-note-type")
        let service = RecordingBlockService()

        try await PinkhaTextDirectionPersistence.markExplicitAlignmentIfNeeded(
            document: document,
            blockIds: [blockId],
            alignment: .right,
            blockService: service
        )

        let capturedFields = await service.lastFields
        let persistedFields = try #require(capturedFields)
        PinkhaTextDirectionPersistence.resetForTesting()
        let reopenedInfo = makeInfo(
            blockId: "ordinary-note-reopened",
            alignment: .right,
            fields: persistedFields
        )
        let reopenedDocument = makeDocument(
            blockId: reopenedInfo.id,
            typeId: "ordinary-note-type",
            info: reopenedInfo
        )
        let context = try #require(PinkhaTextDirectionUIKitAdapter.context(
            document: reopenedDocument,
            info: reopenedInfo,
            text: "טקסט"
        ))

        #expect(context.persistedAlignment == .right)
        #expect(context.alignmentWasExplicit)
        #expect(context.origin == .existingParagraph)
    }

    @Test("Language rendering queues no block service writes")
    func languageRenderingProducesZeroWrites() async throws {
        PinkhaTextDirectionPersistence.resetForTesting()
        let blockId = "ordinary-no-auto-write"
        let info = makeInfo(blockId: blockId)
        let document = makeDocument(
            blockId: blockId,
            typeId: "ordinary-page-type",
            info: info
        )
        let service = RecordingBlockService()
        Container.shared.blockService.register { service }
        defer {
            Container.shared.blockService.reset()
            PinkhaTextDirectionPersistence.resetForTesting()
        }
        let context = try #require(PinkhaTextDirectionUIKitAdapter.context(
            document: document,
            info: info,
            text: "שלום"
        ))
        let textView = UITextView()
        textView.semanticContentAttribute = .forceRightToLeft
        textView.attributedText = NSAttributedString(string: "שלום")

        PinkhaTextDirectionUIKitAdapter.apply(context: context, to: textView)
        try await Task.sleep(for: .milliseconds(350))

        let events = await service.events
        #expect(events.isEmpty)
        #expect(PinkhaTextDirectionPersistence.sessionExplicitAlignment(blockId: blockId) == nil)
    }

    @Test("Document type, manifest and creation provenance are absent from context eligibility")
    func contextHasNoIdentityGate() throws {
        for typeId in ["note", "page", "task", "unknown-custom-type"] {
            let blockId = "block-\(typeId)"
            let info = makeInfo(blockId: blockId)
            let document = makeDocument(blockId: blockId, typeId: typeId, info: info)
            let context = PinkhaTextDirectionUIKitAdapter.context(
                document: document,
                info: info,
                text: "ordinary"
            )
            #expect(context != nil)
        }
    }

    private func makeDocument(
        blockId: String,
        typeId: String,
        info: BlockInformation? = nil
    ) -> MockBaseDocument {
        let details = ObjectDetails(
            id: "document-\(typeId)",
            values: [
                BundledPropertyKey.type.rawValue: Google_Protobuf_Value(stringValue: typeId)
            ]
        )
        let document = MockBaseDocument(objectId: details.id, details: details)
        document.mockSpaceId = "ordinary-test-space"
        let container = InfoContainerMock()
        container.getReturnInfo[blockId] = info ?? makeInfo(blockId: blockId)
        document.mockInfoContainer = container
        return document
    }

    private func makeInfo(
        blockId: String,
        alignment: LayoutAlignment = .left,
        fields: BlockFields = [
            "existing": Google_Protobuf_Value(stringValue: "preserved")
        ]
    ) -> BlockInformation {
        BlockInformation(
            id: blockId,
            content: .text(.plain("טקסט", contentType: .text)),
            backgroundColor: nil,
            horizontalAlignment: alignment,
            childrenIds: [],
            configurationData: BlockInformationMetadata(backgroundColor: .default),
            fields: fields
        )
    }
}

private actor RecordingBlockService: BlockServiceProtocol {
    enum Event: Equatable {
        case alignment(LayoutAlignment)
        case fields
    }

    enum StubError: Error {
        case metadataWriteFailed
        case unexpectedCall
    }

    private let failFieldWrites: Bool
    private(set) var events = [Event]()
    private(set) var lastFields: BlockFields?
    var eventCount: Int { events.count }

    init(failFieldWrites: Bool = false) {
        self.failFieldWrites = failFieldWrites
    }

    func setAlign(objectId: String, blockIds: [String], alignment: LayoutAlignment) async throws {
        events.append(.alignment(alignment))
    }

    func setFields(objectId: String, blockId: String, fields: BlockFields) async throws {
        lastFields = fields
        events.append(.fields)
        if failFieldWrites { throw StubError.metadataWriteFailed }
    }

    func add(contextId: String, targetId: String, info: BlockInformation, position: BlockPosition) async throws -> String { throw StubError.unexpectedCall }
    func addFirstBlock(contextId: String, info: BlockInformation) async throws -> String { throw StubError.unexpectedCall }
    func delete(contextId: String, blockIds: [String]) async throws { throw StubError.unexpectedCall }
    func duplicate(contextId: String, targetId: String, blockIds: [String], position: BlockPosition) async throws { throw StubError.unexpectedCall }
    func move(contextId: String, blockIds: [String], targetContextID: String, dropTargetID: String, position: BlockPosition) async throws { throw StubError.unexpectedCall }
    func setBackgroundColor(objectId: String, blockIds: [String], color: MiddlewareColor) async throws { throw StubError.unexpectedCall }
    func setBlockColor(objectId: String, blockIds: [String], color: MiddlewareColor) async throws { throw StubError.unexpectedCall }
    func replace(objectId: String, blockIds: [String], targetId: String) async throws { throw StubError.unexpectedCall }
    func replaceBlock(contextId: String, blockId: String, info: BlockInformation) async throws -> String { throw StubError.unexpectedCall }
    func move(objectId: String, blockId: String, targetId: String, position: Anytype_Model_Block.Position) async throws { throw StubError.unexpectedCall }
    func moveToPage(objectId: String, blockIds: [String], pageId: String) async throws { throw StubError.unexpectedCall }
    func setLinkAppearance(objectId: String, blockIds: [String], appearance: BlockLink.Appearance) async throws { throw StubError.unexpectedCall }
    func changeMarkup(objectId: String, blockIds: [String], markType: MarkupType) async throws { throw StubError.unexpectedCall }
    func lastBlockId(from objectId: String, spaceId: String) async throws -> String { throw StubError.unexpectedCall }
    func convertChildrenToObjects(contextId: String, blocksIds: [String], typeUniqueKey: ObjectTypeUniqueKey, templateId: String) async throws -> [String] { throw StubError.unexpectedCall }
    func createBlockLink(contextId: String, targetId: String, spaceId: String, details: [BundledDetails], typeUniqueKey: ObjectTypeUniqueKey, position: BlockPosition, templateId: String) async throws -> String { throw StubError.unexpectedCall }
}
