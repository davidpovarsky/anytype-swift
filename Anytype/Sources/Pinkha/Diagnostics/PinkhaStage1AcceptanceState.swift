import Foundation

/// Test-only rendezvous state shared by the app-hosted middleware preparation test and the
/// subsequently launched real application. It is inert unless the acceptance environment
/// variable is present and always points at a disposable local-only account and Space.
struct PinkhaStage1AcceptanceState: Codable, Equatable, Sendable {
    static let environmentKey = "PINKHA_STAGE1_ACCEPTANCE"
    static let documentTitle = "בדיקת RTL Stage 1"
    static let spaceName = "Pinkha Stage 1 RTL Acceptance"

    let spaceId: String
    let objectId: String

    static var isEnabled: Bool {
        ProcessInfo.processInfo.environment[environmentKey] == "1"
    }

    static func load() throws -> PinkhaStage1AcceptanceState {
        try JSONDecoder().decode(
            PinkhaStage1AcceptanceState.self,
            from: Data(contentsOf: fileURL())
        )
    }

    func save() throws {
        let url = try Self.fileURL(createDirectory: true)
        try JSONEncoder().encode(self).write(to: url, options: .atomic)
    }

    private static func fileURL(createDirectory: Bool = false) throws -> URL {
        let base = try FileManager.default.url(
            for: .applicationSupportDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: createDirectory
        )
        return base.appendingPathComponent("pinkha-stage1-acceptance-state.json")
    }
}
