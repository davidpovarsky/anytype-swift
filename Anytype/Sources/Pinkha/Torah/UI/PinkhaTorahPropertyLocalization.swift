import Foundation
import Loc
import PinkhaKit

extension Loc.Pinkha.Torah {
    static func propertyName(for kind: TorahAssociationKind, locale: Locale) -> String {
        switch kind {
        case .ref: String(localized: "Source(s)", table: "PinkhaTorahProperties", bundle: .main, locale: locale)
        case .topic: String(localized: "Topic(s)", table: "PinkhaTorahProperties", bundle: .main, locale: locale)
        case .word: String(localized: "Word / entry", table: "PinkhaTorahProperties", bundle: .main, locale: locale)
        }
    }
}
