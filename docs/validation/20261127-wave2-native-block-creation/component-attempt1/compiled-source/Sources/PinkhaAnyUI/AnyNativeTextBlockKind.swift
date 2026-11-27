import PinkhaAnyEngine
import PinkhaAnyHost

/// The text-block choices already supported by the native creation intent.
/// This catalog supplies new content only; it never changes an existing block's
/// type, identity, parent, position or history.
public enum AnyNativeTextBlockKind: String, CaseIterable, Hashable, Sendable {
    case paragraph
    case heading1 = "heading-1"
    case heading2 = "heading-2"
    case heading3 = "heading-3"
    case bulletedList = "bulleted-list"
    case numberedList = "numbered-list"
    case checklist
    case quote
    case code

    var nativeType: String {
        switch self {
        case .heading1, .heading2, .heading3: return "heading"
        case .bulletedList, .numberedList: return "list_item"
        case .checklist: return "check_list_item"
        case .paragraph: return "paragraph"
        case .quote: return "quote"
        case .code: return "code"
        }
    }

    func initialNativeStyle(direction: AnyWritingDirection) -> AnyJSON {
        var style: [String: AnyJSON] = [
            "pinkhaWritingDirection": .string(direction.rawValue),
            "pinkhaTextAlignment": .string("natural")
        ]
        // These are the existing native type fields, also used by the retained
        // Heart text-block import plan. A new numbered list starts at one.
        switch self {
        case .heading1: style["level"] = .integer(1)
        case .heading2: style["level"] = .integer(2)
        case .heading3: style["level"] = .integer(3)
        case .bulletedList: style["ordered"] = .bool(false)
        case .numberedList:
            style["ordered"] = .bool(true)
            style["number"] = .integer(1)
        case .checklist: style["checked"] = .bool(false)
        case .paragraph, .quote, .code: break
        }
        return .object(style)
    }
}
