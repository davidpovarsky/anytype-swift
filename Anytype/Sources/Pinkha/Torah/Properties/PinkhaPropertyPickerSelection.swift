import Foundation
import Observation
import OSLog

/// Serializes a picker selection until the native operation has settled.
/// A failure keeps the original picker available for an explicit retry.
@MainActor
@Observable
final class PinkhaPropertyPickerSelection {
    private(set) var isRunning = false
    private(set) var failed = false

    private static let logger = Logger(subsystem: "com.anytype.pinkha", category: "PropertyPickerSelection")

    func clearFailure() {
        guard !isRunning else { return }
        failed = false
    }

    func perform(
        spaceID: String,
        objectID: String,
        propertyID: String,
        action: @MainActor () async throws -> Void
    ) async -> Bool {
        guard !isRunning, !Task.isCancelled else { return false }
        isRunning = true
        failed = false
        let correlationID = UUID().uuidString
        defer { isRunning = false }

        do {
            try await action()
            return true
        } catch is CancellationError {
            return false
        } catch {
            guard !Task.isCancelled else { return false }
            failed = true
            let failure = error as NSError
            Self.logger.error("Property selection failed correlation=\(correlationID, privacy: .public) space=\(spaceID, privacy: .private(mask: .hash)) object=\(objectID, privacy: .private(mask: .hash)) property=\(propertyID, privacy: .private(mask: .hash)) domain=\(failure.domain, privacy: .public) code=\(failure.code)")
            return false
        }
    }
}

enum PinkhaPropertyPickerSelectionError: Error {
    case propertyUnavailable
}
