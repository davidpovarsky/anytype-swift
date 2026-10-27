import Testing
import PinkhaKit
import ProtobufMessages
import Services
import SwiftProtobuf
@testable import Anytype

@Suite("Pinkha text-direction persistence", .serialized)
@MainActor
struct PinkhaTextDirectionPersistenceTests {
    @Test("Explicit alignment is committed before metadata and survives metadata failure")
    func explicitAlignmentOrderingAndFailureIsolation() async throws {
        let blockId = "pinkha-explicit-alignment"
        let document = makeDocument(blockId: blockId)
        let service = RecordingBlockService(failFieldWrites: true)
        let bootstrap = BootstrapStub(
            manifest: PinkhaSpaceManifest(
                spaceId: document.spaceId,
                registeredDocumentTypes: ["writing": "pinkha-writing-type"]
            )
        )
        Container.shared.pinkhaBootstrapService.register { bootstrap }
        Container.shared.blockService.register { service }
        defer {
            Container.shared.blockService.reset()
            Container.shared.pinkhaBootstrapService.reset()
        }

        let handler = BlockActionHandler(
            document: document,
            markupChanger: BlockMarkupChangerMock(),
            service: BlockActionServiceMock()
        )
        handler.setAlignment(.right, blockIds: [blockId])

        for _ in 0..<100 {
            if await service.eventCount >= 2 { break }
            try await Task.sleep(nanoseconds: 10_000_000)
        }

        let events = await service.events
        let lastAlignment = await service.lastAlignment
        let lastFields = await service.lastFields
        #expect(events == [.alignment(.right), .fields])
        #expect(lastAlignment == .right)
        #expect(PinkhaTextDirectionPersistence.sessionExplicitAlignment(blockId: blockId) == .right)
        #expect(lastFields?["existing"]?.stringValue == "preserved")
        let marker = try #require(lastFields?[PinkhaSchemaRoles.blockTextDirectionField])
        #expect(PinkhaTextDirectionMarker(storedValue: marker.stringValue) == .explicit(.right))
    }

    @Test("Persisted explicit metadata restores the choice after a simulated reopen")
    func explicitAlignmentColdReopen() async throws {
        let writtenBlockId = "pinkha-persisted-write"
        let document = makeDocument(blockId: writtenBlockId)
        let service = RecordingBlockService()
        let bootstrap = BootstrapStub(
            manifest: PinkhaSpaceManifest(
                spaceId: document.spaceId,
                registeredDocumentTypes: ["writing": "pinkha-writing-type"]
            )
        )
        Container.shared.pinkhaBootstrapService.register { bootstrap }
        defer { Container.shared.pinkhaBootstrapService.reset() }

        try await PinkhaTextDirectionPersistence.markExplicitAlignmentIfNeeded(
            document: document,
            blockIds: [writtenBlockId],
            alignment: .right,
            blockService: service
        )

        let capturedFields = await service.lastFields
        let persistedFields = try #require(capturedFields)
        let reopenedBlockId = "pinkha-reopened-block"
        let reopenedInfo = makeInfo(
            blockId: reopenedBlockId,
            alignment: .right,
            fields: persistedFields
        )
        let reopenedDocument = makeDocument(blockId: reopenedBlockId, info: reopenedInfo)
        let context = try #require(PinkhaTextDirectionUIKitAdapter.context(
            document: reopenedDocument,
            info: reopenedInfo,
            text: "טקסט"
        ))

        #expect(context.persistedAlignment == .right)
        #expect(context.alignmentWasExplicit)
        #expect(context.origin == .existingParagraph)
    }

    @Test("Ready bootstrap state closes the manifest-cache race")
    func readyStateFallbackClosesGateRace() throws {
        let blockId = "pinkha-ready-state-race"
        let document = makeDocument(blockId: blockId)
        let manifest = PinkhaSpaceManifest(
            spaceId: document.spaceId,
            registeredDocumentTypes: ["writing": "pinkha-writing-type"]
        )
        Container.shared.pinkhaBootstrapService.register { EmptyBootstrapCacheStub() }
        Container.shared.pinkhaBootstrapStateManager().setState(.ready(manifest), for: document.spaceId)
        defer { Container.shared.pinkhaBootstrapService.reset() }

        let context = try #require(PinkhaTextDirectionUIKitAdapter.context(
            document: document,
            info: try #require(document.infoContainer.get(id: blockId)),
            text: "שלום"
        ))

        #expect(context.origin == .ambiguousLegacyParagraph)
    }

    @Test("Template blocks in a newly created Pinkha document are proven new")
    func newDocumentTemplateBlockProvenance() throws {
        let blockId = "pinkha-template-block"
        let document = makeDocument(blockId: blockId)
        let bootstrap = BootstrapStub(
            manifest: PinkhaSpaceManifest(
                spaceId: document.spaceId,
                registeredDocumentTypes: ["writing": "pinkha-writing-type"]
            )
        )
        Container.shared.pinkhaBootstrapService.register { bootstrap }
        PinkhaDocumentIdentityStorage.shared.registerCreated(
            objectId: document.objectId,
            spaceId: document.spaceId
        )
        defer { Container.shared.pinkhaBootstrapService.reset() }

        let context = try #require(PinkhaTextDirectionUIKitAdapter.context(
            document: document,
            info: try #require(document.infoContainer.get(id: blockId)),
            text: ""
        ))

        #expect(context.origin == .newParagraph)
    }

    private func makeDocument(
        blockId: String,
        info: BlockInformation? = nil
    ) -> MockBaseDocument {
        let details = ObjectDetails(
            id: "pinkha-document",
            values: [
                BundledPropertyKey.type.rawValue: Google_Protobuf_Value(
                    stringValue: "pinkha-writing-type"
                )
            ]
        )
        let document = MockBaseDocument(objectId: details.id, details: details)
        document.mockSpaceId = "pinkha-test-space"
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

private struct BootstrapStub: PinkhaSpaceBootstrapServiceProtocol {
    let manifest: PinkhaSpaceManifest

    func bootstrapSpace(spaceId: String) async throws -> PinkhaSpaceManifest { manifest }
    func manifest(forSpaceId spaceId: String) -> PinkhaSpaceManifest? {
        spaceId == manifest.spaceId ? manifest : nil
    }
    func isBootstrapped(spaceId: String) -> Bool { spaceId == manifest.spaceId }
}

private struct EmptyBootstrapCacheStub: PinkhaSpaceBootstrapServiceProtocol {
    func bootstrapSpace(spaceId: String) async throws -> PinkhaSpaceManifest {
        throw CancellationError()
    }
    func manifest(forSpaceId spaceId: String) -> PinkhaSpaceManifest? { nil }
    func isBootstrapped(spaceId: String) -> Bool { false }
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
    private(set) var lastAlignment: LayoutAlignment?
    private(set) var lastFields: BlockFields?
    var eventCount: Int { events.count }

    init(failFieldWrites: Bool = false) {
        self.failFieldWrites = failFieldWrites
    }

    func setAlign(objectId: String, blockIds: [String], alignment: LayoutAlignment) async throws {
        lastAlignment = alignment
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
