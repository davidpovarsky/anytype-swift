import Foundation

/// Read-only, noncontent diagnosis for an explicitly scoped Debug UI process.
/// No token, account/object/block identity, text, markup, or error description
/// enters this bounded file. Recording never decides whether a write succeeded.
@MainActor
enum AnyNativeEditorDiagnostics {
    enum Phase: String, Codable {
        case documentAppeared, documentReadinessChanged, documentSceneChanged
        case emptyButtonTapped, menuButtonTapped, addParagraphEntered
        case flushCompleted, mutationReserved, prewriteReadCompleted
        case nativeCreationVerified, mutationReadbackVerified, readbackPublished
        case addParagraphCompleted, addParagraphFailed
    }

    private struct Event: Codable {
        let phase: Phase
        let timestamp: TimeInterval
        let request: UUID?
        let ownerMatches: Bool?
        let mounted: Bool?
        let active: Bool?
        let saving: Bool?
        let errorType: String?
        let canMutate: Bool?
        let canWrite: Bool?
        let navigating: Bool?
        let draftReview: Bool?
        let composing: Bool?
        let foreground: Bool?
    }

    static func record(_ phase: Phase, request: UUID? = nil,
                       ownerMatches: Bool? = nil, mounted: Bool? = nil,
                       active: Bool? = nil, saving: Bool? = nil,
                       errorType: String? = nil,
                       canMutate: Bool? = nil, canWrite: Bool? = nil,
                       navigating: Bool? = nil, draftReview: Bool? = nil,
                       composing: Bool? = nil, foreground: Bool? = nil) {
        #if DEBUG
        let arguments = ProcessInfo.processInfo.arguments
        guard arguments.contains("--native-ui-tests"),
              let index = arguments.firstIndex(of: "--native-ui-test-scope"),
              arguments.indices.contains(index + 1),
              let scope = UUID(uuidString: arguments[index + 1]) else { return }
        let file = FileManager.default.temporaryDirectory.appendingPathComponent(
            "pinkha-editor-ui-diagnostics-" + scope.uuidString + ".json")
        do {
            var events: [Event] = []
            if FileManager.default.fileExists(atPath: file.path) {
                let attributes = try FileManager.default.attributesOfItem(atPath: file.path)
                guard let size = attributes[.size] as? NSNumber, size.intValue <= 131_072,
                      attributes[.type] as? FileAttributeType == .typeRegular else { return }
                events = try JSONDecoder().decode([Event].self, from: Data(contentsOf: file))
            }
            guard events.count < 256 else { return }
            events.append(.init(phase: phase, timestamp: Date().timeIntervalSince1970,
                                request: request, ownerMatches: ownerMatches, mounted: mounted,
                                active: active, saving: saving, errorType: errorType,
                                canMutate: canMutate, canWrite: canWrite, navigating: navigating,
                                draftReview: draftReview, composing: composing, foreground: foreground))
            let data = try JSONEncoder().encode(events)
            guard data.count <= 131_072 else { return }
            try data.write(to: file, options: .atomic)
        } catch {
            // Diagnostics must neither change native writes nor replace their
            // normal visible errors. A missing file remains missing evidence.
        }
        #endif
    }
}
