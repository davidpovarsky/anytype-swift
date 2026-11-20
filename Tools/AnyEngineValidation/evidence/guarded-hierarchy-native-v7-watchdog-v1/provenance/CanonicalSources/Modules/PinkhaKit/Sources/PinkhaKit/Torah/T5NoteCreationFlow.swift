import Foundation

public struct T5NoteCreationOutcome: Sendable {
    public let objectID: String
    public let recoveryError: (any Error)?
}

@MainActor
public final class T5NoteCreationFlow {
    public typealias Authorize = @MainActor () throws -> Void
    public typealias Create = @MainActor () async throws -> String
    public typealias Write = @MainActor (String) async throws -> Void

    private struct PendingNote {
        let objectID: String
        var sourceLineAttempted = false
    }

    private var pending: [T5SourceIdentity: PendingNote] = [:]

    public init() {}

    public func create(
        source: T5SourceIdentity, authorize: Authorize, createObject: Create,
        linkSource: Write, addSourceLine: Write, linkOrigin: Write
    ) async throws -> T5NoteCreationOutcome {
        guard !source.providerID.isEmpty, !source.canonicalReference.isEmpty else {
            throw T5SpaceRelatedDocumentsError.invalidIdentity
        }
        let objectID: String
        if let existing = pending[source] {
            objectID = existing.objectID
        } else {
            try Task.checkCancellation()
            try authorize()
            objectID = try await createObject()
            pending[source] = PendingNote(objectID: objectID)
        }
        do {
            try Task.checkCancellation()
            try authorize()
            try await linkSource(objectID)
            try Task.checkCancellation()
            if pending[source]?.sourceLineAttempted == false {
                try authorize()
                pending[source]?.sourceLineAttempted = true
                try await addSourceLine(objectID)
            }
            try Task.checkCancellation()
            try authorize()
            try await linkOrigin(objectID)
            pending.removeValue(forKey: source)
            return .init(objectID: objectID, recoveryError: nil)
        } catch {
            return .init(objectID: objectID, recoveryError: error)
        }
    }
}
