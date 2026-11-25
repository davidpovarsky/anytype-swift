#if PINKHA_DUAL_ENGINE_RUNTIME
import Foundation
import Lib

public enum PinkhaLoadedAccountSourceNativeError: Error, Sendable {
    case missingNativeDescriptor
    case nativeValidationFailed
}

/// The sole Lib owner exposes a small synchronous boundary. The original app
/// obtains a real native Full session and runs these calls off its main actor.
/// Tokens and private source descriptors never enter Invocation body logging.
public enum PinkhaLoadedAccountSourceNative {
    public static func capture(sessionToken: String, accountID: String, spaceID: String,
                               privateDirectory: String, requestID: String) throws -> Data {
        var nativeError: NSError?
        let bytes: Data? = Lib.ServicePinkhaCaptureLoadedAccountSource(
            sessionToken, accountID, spaceID, privateDirectory, requestID, &nativeError)
        if let nativeError { throw nativeError }
        guard let bytes, !bytes.isEmpty else {
            throw PinkhaLoadedAccountSourceNativeError.missingNativeDescriptor
        }
        return bytes
    }

    public static func validate(sessionToken: String, requestID: String, manifestSHA256: String) throws {
        var nativeError: NSError?
        let valid = Lib.ServicePinkhaValidateLoadedAccountSourceCapture(
            sessionToken, requestID, manifestSHA256, &nativeError)
        if let nativeError { throw nativeError }
        guard valid else { throw PinkhaLoadedAccountSourceNativeError.nativeValidationFailed }
    }

    public static func cancel(sessionToken: String, requestID: String) -> Bool {
        Lib.ServicePinkhaCancelLoadedAccountSourceCapture(sessionToken, requestID)
    }

    public static func release(sessionToken: String, requestID: String) -> Bool {
        Lib.ServicePinkhaReleaseLoadedAccountSourceCapture(sessionToken, requestID)
    }
}
#endif
