#if DEBUG && targetEnvironment(simulator)
import Foundation

/// Written only by the real disposable native preparation test. No credentials.
struct PinkhaHanlinNativeAcceptanceFixture: Codable, Sendable {
    static let fileName = "pinkha-hanlin-native-fixture.json"
    static let resultFileName = "pinkha-hanlin-native-result.json"

    let fixtureID: UUID
    let createdAt: Date
    let sourceSHA: String
    let runID: String
    let runAttempt: String
    let accountID: String
    let spaceID: String
    let alternateSpaceID: String
    let sourceObjectID: String
    let sourceTitle: String
    let sourceBlockID: String
    let sourceText: String
    let createdTitle: String
    let cancelledTitle: String

    static func fileURL(_ name: String) throws -> URL {
        try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask,
                                    appropriateFor: nil, create: true).appendingPathComponent(name)
    }

    func save() throws {
        try JSONEncoder().encode(self).write(to: Self.fileURL(Self.fileName), options: .withoutOverwriting)
    }

    static func loadForUI() throws -> Self {
        let environment = ProcessInfo.processInfo.environment
        guard environment["PINKHA_HANLIN_NATIVE_UI"] == "1",
              environment["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1" else {
            throw HanlinNativeAcceptanceError.invalidFixture
        }
        let bytes = try Data(contentsOf: fileURL(fileName))
        guard bytes.count <= 16_384 else { throw HanlinNativeAcceptanceError.invalidFixture }
        let fixture = try JSONDecoder().decode(Self.self, from: bytes)
        guard environment["PINKHA_HANLIN_NATIVE_FIXTURE_ID"] == fixture.fixtureID.uuidString,
              environment["PINKHA_HANLIN_NATIVE_SOURCE_SHA"] == fixture.sourceSHA,
              environment["PINKHA_HANLIN_NATIVE_RUN_ID"] == fixture.runID,
              environment["PINKHA_HANLIN_NATIVE_RUN_ATTEMPT"] == fixture.runAttempt,
              fixture.sourceSHA.count == 40 && fixture.sourceSHA.allSatisfy(\.isHexDigit),
              UInt64(fixture.runID).map({ $0 > 0 }) == true,
              UInt64(fixture.runAttempt).map({ $0 > 0 }) == true,
              Date().timeIntervalSince(fixture.createdAt) >= 0,
              Date().timeIntervalSince(fixture.createdAt) < 3_600,
              fixture.spaceID != fixture.alternateSpaceID,
              [fixture.accountID, fixture.spaceID, fixture.alternateSpaceID,
               fixture.sourceObjectID, fixture.sourceBlockID].allSatisfy({ !$0.isEmpty && $0.utf8.count <= 256 }),
              fixture.sourceText == "Hanlin native body " + fixture.fixtureID.uuidString,
              !fixture.sourceTitle.isEmpty && fixture.sourceTitle.utf8.count <= 512,
              fixture.createdTitle == "Hanlin native created " + fixture.fixtureID.uuidString,
              fixture.cancelledTitle == "Hanlin native cancelled " + fixture.fixtureID.uuidString,
              !FileManager.default.fileExists(atPath: try fileURL(resultFileName).path) else {
            throw HanlinNativeAcceptanceError.invalidFixture
        }
        return fixture
    }
}

enum HanlinNativeAcceptanceError: Error {
    case invalidFixture
    case failed(String)
}
#endif
