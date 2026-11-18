#if DEBUG && targetEnvironment(simulator)
import Foundation
import AnytypeCore
import ProtobufMessages
import Services
import Testing
@testable import Anytype

@Suite("Hanlin selected-block native disposable fixture", .serialized,
       .enabled(if: ProcessInfo.processInfo.environment["PINKHA_PREPARE_HANLIN_SELECTION_UI"] == "1"))
@MainActor
struct HanlinSelectionAcceptancePreparationTests {
    @Test("Prepare two native paragraphs for an independent selected-block UI run")
    func prepareSelectedBlockFixture() async throws {
        let environment = ProcessInfo.processInfo.environment
        try #require(environment["PINKHA_PREPARE_HANLIN_SELECTION_UI"] == "1")
        for suffix in ["SOURCE_SHA", "RUN_ID", "RUN_ATTEMPT"] {
            let selected = try #require(environment["PINKHA_HANLIN_SELECTION_" + suffix])
            try #require(selected == environment["PINKHA_HANLIN_NATIVE_" + suffix])
        }
        try #require(ProcessInfo.processInfo.environment["PINKHA_HANLIN_NATIVE_UI"] != "1")
        for name in [PinkhaHanlinSelectionAcceptanceFixture.fileName, PinkhaHanlinSelectionAcceptanceFixture.resultFileName] {
            try #require(!FileManager.default.fileExists(atPath: try PinkhaHanlinNativeAcceptanceFixture.fileURL(name).path))
        }
        // Reuse the real account/Space/page preparation, including its empty-account,
        // local-only and logging guards. This is one selected XCTest, not a second UI lane.
        try await HanlinNativeAcceptancePreparationTests().prepareRealHostFixture()
        let originalURL = try PinkhaHanlinNativeAcceptanceFixture.fileURL(PinkhaHanlinNativeAcceptanceFixture.fileName)
        let base = try JSONDecoder().decode(PinkhaHanlinNativeAcceptanceFixture.self, from: Data(contentsOf: originalURL))
        let excludedText = "Hanlin unselected body " + base.fixtureID.uuidString
        let document = Container.shared.openedDocumentProvider().document(objectId: base.sourceObjectID, spaceId: base.spaceID)
        try await document.open()
        let excludedID = try await Container.shared.blockService().addFirstBlock(
            contextId: base.sourceObjectID, info: .empty(id: "", content: .text(.plain(excludedText, contentType: .text))))
        try #require(!excludedID.isEmpty && !excludedID.utf8.elementsEqual(base.sourceBlockID.utf8))
        let view = try await Container.shared.objectLifecycleService().openForPreview(
            contextId: base.sourceObjectID, spaceId: base.spaceID)
        try #require(view.rootID == base.sourceObjectID)
        for (identifier, text) in [(base.sourceBlockID, base.sourceText), (excludedID, excludedText)] {
            try #require(view.blocks.contains { block in
                guard block.id == identifier, let converted = BlockInformationConverter.convert(block: block),
                      case .text(let content) = converted.content else { return false }
                return content.text == text
            })
        }
        try await document.close()
        let fixture = PinkhaHanlinSelectionAcceptanceFixture(base: base, excludedBlockID: excludedID, excludedText: excludedText)
        try fixture.save()
        print("PINKHA_HANLIN_SELECTION_FIXTURE_READY fixture=\(base.fixtureID.uuidString) source=\(base.sourceSHA) run=\(base.runID)")
    }
}
#endif
