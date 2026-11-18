#if DEBUG && targetEnvironment(simulator)
import Foundation

/// Separate companion fixture. The document-only SDK acceptance schema is unchanged.
struct PinkhaHanlinSelectionAcceptanceFixture: Codable, Sendable {
    static let fileName = "pinkha-hanlin-selection-fixture.json"
    static let resultFileName = "pinkha-hanlin-selection-result.json"
    let base: PinkhaHanlinNativeAcceptanceFixture
    let excludedBlockID: String
    let excludedText: String

    func save() throws {
        try JSONEncoder().encode(self).write(to: PinkhaHanlinNativeAcceptanceFixture.fileURL(Self.fileName),
                                             options: .withoutOverwriting)
    }

    static func loadForUI() throws -> Self {
        let environment = ProcessInfo.processInfo.environment
        guard environment["PINKHA_HANLIN_SELECTION_UI"] == "1",
              environment["PINKHA_HANLIN_NATIVE_UI"] != "1",
              environment["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1" else {
            throw HanlinNativeAcceptanceError.invalidFixture
        }
        let bytes = try Data(contentsOf: PinkhaHanlinNativeAcceptanceFixture.fileURL(fileName))
        guard bytes.count <= 16_384 else { throw HanlinNativeAcceptanceError.invalidFixture }
        let fixture = try JSONDecoder().decode(Self.self, from: bytes)
        let base = fixture.base
        guard environment["PINKHA_HANLIN_SELECTION_FIXTURE_ID"] == base.fixtureID.uuidString,
              environment["PINKHA_HANLIN_SELECTION_SOURCE_SHA"] == base.sourceSHA,
              environment["PINKHA_HANLIN_SELECTION_RUN_ID"] == base.runID,
              environment["PINKHA_HANLIN_SELECTION_RUN_ATTEMPT"] == base.runAttempt,
              base.sourceSHA.count == 40 && base.sourceSHA.allSatisfy(\.isHexDigit),
              UInt64(base.runID).map({ $0 > 0 }) == true,
              UInt64(base.runAttempt).map({ $0 > 0 }) == true,
              Date().timeIntervalSince(base.createdAt) >= 0,
              Date().timeIntervalSince(base.createdAt) < 3_600,
              base.spaceID != base.alternateSpaceID,
              [base.accountID, base.spaceID, base.alternateSpaceID, base.sourceObjectID,
               base.sourceBlockID, fixture.excludedBlockID].allSatisfy({ !$0.isEmpty && $0.utf8.count <= 256 }),
              !base.sourceBlockID.utf8.elementsEqual(fixture.excludedBlockID.utf8),
              base.sourceText == "Hanlin native body " + base.fixtureID.uuidString,
              fixture.excludedText == "Hanlin unselected body " + base.fixtureID.uuidString,
              !base.sourceTitle.isEmpty && base.sourceTitle.utf8.count <= 512,
              base.createdTitle == "Hanlin native created " + base.fixtureID.uuidString,
              base.cancelledTitle == "Hanlin native cancelled " + base.fixtureID.uuidString,
              !FileManager.default.fileExists(atPath: try PinkhaHanlinNativeAcceptanceFixture.fileURL(resultFileName).path) else {
            throw HanlinNativeAcceptanceError.invalidFixture
        }
        return fixture
    }
}
#endif
