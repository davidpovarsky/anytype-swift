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

    static func nativePropertiesUnavailable(locale: Locale) -> String {
        String(localized: "Torah properties could not be loaded.", table: "PinkhaTorahProperties", bundle: .main, locale: locale)
    }

    static func existingPropertiesUnavailable(locale: Locale) -> String {
        String(localized: "Existing properties could not be loaded.", table: "PinkhaTorahProperties", bundle: .main, locale: locale)
    }
}
