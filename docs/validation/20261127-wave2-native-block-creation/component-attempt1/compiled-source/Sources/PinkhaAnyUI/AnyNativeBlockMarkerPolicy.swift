import Foundation
import PinkhaAnyEngine
import PinkhaAnyHost

/// Matches the pinned native editor's checked/ordered/number fields without
/// normalizing, deleting or rewriting any of the received style metadata.
public enum AnyNativeBlockMarkerPolicy {
    public static func marker(for block: AnyEditorBlock) -> String {
        switch block.type {
        case "quote": return "❝"
        case "check_list_item": return block.native["style"]?["checked"]?.bool == true ? "☑" : "☐"
        case "list_item":
            guard block.native["style"]?["ordered"]?.bool == true else { return "•" }
            let raw = block.native["style"]?["number"]
            let integer: Int64?
            if let raw, case .number(let number) = raw {
                integer = Int64(exactly: number.rounded(.towardZero))
            } else { integer = raw?.integer }
            let value = integer.flatMap { (0...999_999_999).contains($0) ? $0 : nil } ?? 1
            return "\(value)."
        default: return ""
        }
    }
}
