import Foundation
#if canImport(UIKit)
import UIKit
#endif

/// The confirmation and localized copy are shared by both engine adapters.
/// This presenter owns no storage, authority, selection, or native operation.
public enum PinkhaSemanticAnchorUI {
    public enum Text: String, Sendable {
        case title = "Text anchor"
        case create = "Create text anchor"
        case confirmTitle = "Create an anchor for this text?"
        case confirmBody = "This adds an anchor to the selected text."
        case cancel = "Cancel"
        case done = "Done"
        case created = "The selected text now has an anchor."
        case reveal = "Go to anchored text"
        case copyLink = "Copy anchor link"
        case sources = "Sources for anchored text"
        case linkSource = "Link to anchored text"
        case sourceLinkUnconfirmed = "The source was saved, but its text anchor could not be confirmed. Reopen this page before linking again."
        case invalidSelection = "Choose a shorter, complete selection without existing links."
        case alreadyLinked = "This selection already contains a link or an anchor."
        case changed = "The page changed. Wait for it to save, then select the text again."
        case unavailablePage = "This page is no longer available for editing."
        case unavailable = "Text anchors are unavailable right now."
        case unconfirmed = "The result could not be confirmed. Reopen this page before trying again."
        case missing = "This text anchor no longer exists in the current page."
        case ambiguous = "This text anchor appears more than once. Choose the intended text again."
        case foreignPage = "This text anchor belongs to a different page or space."
    }

    public static func text(_ value: Text) -> String {
        #if canImport(Darwin)
        String(localized: String.LocalizationValue(value.rawValue),
               table: "PinkhaSemanticAnchors", bundle: .module)
        #else
        NSLocalizedString(value.rawValue, tableName: "PinkhaSemanticAnchors", bundle: .module, comment: "")
        #endif
    }

    #if canImport(UIKit)
    /// Inspect only the currently rendered selection. Opening sources still
    /// resolves the identity against a fresh authorized native document.
    public static func selectedAnchor(in text: NSAttributedString, range: NSRange,
                                      spaceID: String, objectID: String) -> PinkhaSemanticTextAnchor? {
        guard range.location != NSNotFound, range.location >= 0, range.length > 0,
              range.location <= text.length, range.length <= text.length - range.location,
              Range(range, in: text.string) != nil else { return nil }
        var selected: PinkhaSemanticTextAnchor?, covered = 0, invalid = false
        text.enumerateAttribute(.link, in: range) { value, fragment, _ in
            let url = value as? URL ?? (value as? String).flatMap(URL.init(string:))
            guard let url, PinkhaSemanticTextAnchor.isReservedMarkerURL(url),
                  let anchor = try? PinkhaSemanticTextAnchor(markerURL: url),
                  anchor.belongsTo(spaceID: spaceID, objectID: objectID),
                  selected == nil || selected == anchor else { invalid = true; return }
            selected = anchor; covered += fragment.length
        }
        return !invalid && covered == range.length ? selected : nil
    }

    @MainActor
    public static func confirmation(
        selectedText: String,
        cancelled: @escaping @MainActor () -> Void,
        willConfirm: @escaping @MainActor () -> Void,
        confirmed: @escaping @MainActor () -> Void
    ) -> UIAlertController {
        let alert = UIAlertController(title: text(.confirmTitle),
            message: text(.confirmBody) + "\n\n" + String(selectedText.prefix(240)),
            preferredStyle: .alert)
        alert.view.accessibilityIdentifier = "pinkha.semanticAnchor.confirmation"
        alert.addAction(UIAlertAction(title: text(.cancel), style: .cancel) { _ in cancelled() })
        alert.addAction(UIAlertAction(title: text(.create), style: .default) { [weak alert] _ in
            willConfirm()
            guard let alert else { return }
            // The adapter revalidates ownership after the actual alert closes.
            alert.dismiss(animated: true, completion: confirmed)
        })
        return alert
    }

    @MainActor
    public static func outcome(_ message: String,
                               done: @escaping @MainActor () -> Void = {}) -> UIAlertController {
        let alert = UIAlertController(title: text(.title), message: message, preferredStyle: .alert)
        alert.view.accessibilityIdentifier = "pinkha.semanticAnchor.outcome"
        alert.addAction(UIAlertAction(title: text(.done), style: .default) { _ in done() })
        return alert
    }

    #endif

    public static func message(for error: PinkhaSemanticTextAnchorError) -> String {
        switch error {
        case .selectionAlreadyLinked, .overlappingMarkers: text(.alreadyLinked)
        case .changedText: text(.changed)
        case .wrongDocument: text(.foreignPage)
        case .invalidIdentity, .invalidMarker, .unsupportedVersion: text(.unavailable)
        case .invalidRange, .limitExceeded: text(.invalidSelection)
        }
    }
}
