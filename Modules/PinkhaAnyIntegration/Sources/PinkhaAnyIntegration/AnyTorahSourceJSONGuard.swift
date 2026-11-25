import Foundation
import PinkhaKit

public enum AnyTorahMigrationError: Error, Sendable, Equatable {
    case numericPrecisionWouldChange(path: String)
    case duplicateJSONKey(path: String)
    case unmappedReferencedObject(String)
    case malformedInternalNoteLink(itemID: String)
}

/// Compatibility surface for the shared exact-number and duplicate-key guard.
/// Both engines use PinkhaKit's parser; existing Any callers keep their errors.
public enum AnyTorahSourceJSONGuard {
    static func validateCanonicalPayload(_ bytes: Data,
                                         decoded: TorahCanonicalAssociationsPayload) throws {
        try preservingMigrationErrors {
            try TorahSourceJSONGuard.validateCanonicalPayload(bytes, decoded: decoded)
        }
    }

    public static func validateRoundTrip(original: Data, encoded: Data) throws {
        try preservingMigrationErrors {
            try TorahSourceJSONGuard.validateRoundTrip(original: original, encoded: encoded)
        }
    }

    private static func preservingMigrationErrors(_ operation: () throws -> Void) throws {
        do {
            try operation()
        } catch let error as TorahSourceJSONGuardError {
            switch error {
            case .numericPrecisionWouldChange(let path):
                throw AnyTorahMigrationError.numericPrecisionWouldChange(path: path)
            case .duplicateJSONKey(let path):
                throw AnyTorahMigrationError.duplicateJSONKey(path: path)
            }
        }
    }
}
