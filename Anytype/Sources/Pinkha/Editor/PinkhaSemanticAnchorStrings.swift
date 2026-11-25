#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 && PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1
import Foundation
import ProtobufMessages
import PinkhaKit
import PinkhaTorahPresentation

enum PinkhaSemanticAnchorStrings {
    private static func text(_ key: PinkhaSemanticAnchorUI.Text) -> String {
        PinkhaSemanticAnchorUI.text(key)
    }
    static var title: String { text(.title) }
    static var create: String { text(.create) }
    static var confirmTitle: String { text(.confirmTitle) }
    static var confirmBody: String { text(.confirmBody) }
    static var cancel: String { text(.cancel) }
    static var done: String { text(.done) }
    static var created: String { text(.created) }

    static func message(for error: Error) -> String {
        if let semantic = error as? PinkhaSemanticTextAnchorError {
            return PinkhaSemanticAnchorUI.message(for: semantic)
        }
        if let semantic = error as? TorahSemanticAnchorResolutionError {
            return semantic.localizedDescription
        }
        guard let value = error as? PinkhaHeartSemanticAnchorError else {
            return text(.unavailable)
        }
        switch value {
        case .invalidRequest, .limitExceeded, .nativeRefusal(.invalid), .nativeRefusal(.limit):
            return text(.invalidSelection)
        case .selectionAlreadyLinked, .nativeRefusal(.alreadyLinked):
            return text(.alreadyLinked)
        case .changedDocument, .nativeRefusal(.changed), .nativeRefusal(.pendingEdit):
            return text(.changed)
        case .retiredOwner, .nativeRefusal(.permissionDenied):
            return text(.unavailablePage)
        case .unsupportedRuntime, .unavailablePublication,
             .nativeRefusal(.unsupportedVersion), .nativeRefusal(.unavailable):
            return text(.unavailable)
        case .uncertain, .invalidReply, .nativeRefusal(.uncertain), .nativeRefusal(.applied):
            return text(.unconfirmed)
        }
    }
}
#endif
