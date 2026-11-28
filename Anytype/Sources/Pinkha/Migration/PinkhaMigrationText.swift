#if PINKHA_DUAL_ENGINE_RUNTIME
import Foundation

/// Shared engine/migration copy follows the app bundle's selected language.
/// It does not select copy from a device-region setting or an engine account.
enum PinkhaMigrationText {
    static func text(_ key: String.LocalizationValue) -> String {
        let language = Bundle.main.preferredLocalizations.first ?? "en"
        return String(localized: key, table: "PinkhaMigration", bundle: .main,
            locale: Locale(identifier: language))
    }
}
#endif
