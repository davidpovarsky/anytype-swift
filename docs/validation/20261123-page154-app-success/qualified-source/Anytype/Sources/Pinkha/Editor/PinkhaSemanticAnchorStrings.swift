#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 && PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1
import Foundation
import ProtobufMessages

enum PinkhaSemanticAnchorStrings {
    private static func text(_ key: String.LocalizationValue) -> String {
        String(localized: key, table: "PinkhaSemanticAnchors", bundle: .main)
    }
    static var title: String { text("Text anchor") }
    static var create: String { text("Create text anchor") }
    static var confirmTitle: String { text("Create an anchor for this text?") }
    static var confirmBody: String { text("This adds an anchor to the selected text.") }
    static var cancel: String { text("Cancel") }
    static var done: String { text("Done") }
    static var created: String { text("The selected text now has an anchor.") }

    static func message(for error: Error) -> String {
        guard let value = error as? PinkhaHeartSemanticAnchorError else {
            return text("Text anchors are unavailable right now.")
        }
        switch value {
        case .invalidRequest, .limitExceeded, .nativeRefusal(.invalid), .nativeRefusal(.limit):
            return text("Choose a shorter, complete selection without existing links.")
        case .selectionAlreadyLinked, .nativeRefusal(.alreadyLinked):
            return text("This selection already contains a link or an anchor.")
        case .changedDocument, .nativeRefusal(.changed), .nativeRefusal(.pendingEdit):
            return text("The page changed. Wait for it to save, then select the text again.")
        case .retiredOwner, .nativeRefusal(.permissionDenied):
            return text("This page is no longer available for editing.")
        case .unsupportedRuntime, .unavailablePublication,
             .nativeRefusal(.unsupportedVersion), .nativeRefusal(.unavailable):
            return text("Text anchors are unavailable right now.")
        case .uncertain, .invalidReply, .nativeRefusal(.uncertain), .nativeRefusal(.applied):
            return text("The result could not be confirmed. Reopen this page before trying again.")
        }
    }
}
#endif
