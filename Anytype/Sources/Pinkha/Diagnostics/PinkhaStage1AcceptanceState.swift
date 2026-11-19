import Foundation
import PinkhaKit
import SwiftUI
import UIKit

/// Test-only state used after the real application completes its local-only onboarding flow.
/// It is inert unless the acceptance environment variable is present and always points at a
/// disposable local-only account and Space created inside the UI-test application container.
struct PinkhaStage1AcceptanceState: Codable, Equatable, Sendable {
    enum DocumentKind: String, CaseIterable, Codable, Sendable {
        case pinkha
        case note
        case page
    }

    static let environmentKey = "PINKHA_STAGE1_ACCEPTANCE"
    static let documentKindEnvironmentKey = "PINKHA_ACCEPTANCE_DOCUMENT_KIND"
    static let deviceLanguageEnvironmentKey = "PINKHA_ACCEPTANCE_DEVICE_LANGUAGE"
    static let pinkhaDocumentTitle = "בדיקת RTL Stage 1"
    static let noteDocumentTitle = "RTL Acceptance Ordinary Note"
    static let pageDocumentTitle = "RTL Acceptance Ordinary Page"
    static let spaceName = "Pinkha Stage 1 RTL Acceptance"

    let spaceId: String
    let pinkhaObjectId: String
    let noteObjectId: String
    let pageObjectId: String

    static var isEnabled: Bool {
        ProcessInfo.processInfo.environment[environmentKey] == "1"
    }

    static var requestedDocumentKind: DocumentKind {
        guard let rawValue = ProcessInfo.processInfo.environment[documentKindEnvironmentKey],
              let kind = DocumentKind(rawValue: rawValue) else {
            return .pinkha
        }
        return kind
    }

    func objectId(for kind: DocumentKind) -> String {
        switch kind {
        case .pinkha: pinkhaObjectId
        case .note: noteObjectId
        case .page: pageObjectId
        }
    }

    static func load() throws -> PinkhaStage1AcceptanceState {
        try JSONDecoder().decode(
            PinkhaStage1AcceptanceState.self,
            from: Data(contentsOf: fileURL())
        )
    }

    func save() throws {
        let url = try Self.fileURL(createDirectory: true)
        try JSONEncoder().encode(self).write(to: url, options: .atomic)
    }

    private static func fileURL(createDirectory: Bool = false) throws -> URL {
        let base = try FileManager.default.url(
            for: .applicationSupportDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: createDirectory
        )
        return base.appendingPathComponent("pinkha-stage1-acceptance-state.json")
    }
}

/// Same-process evidence bridge used only by the real-app acceptance target. Production UI
/// behavior does not read this state.
@MainActor
enum PinkhaStage1AcceptanceDiagnostics {
    private static var swiftUILayoutDirection: LayoutDirection?
    private static var navigationLayoutDirection: UIUserInterfaceLayoutDirection?
    private static let acceptedInsertions = NSMapTable<UITextView, NSString>.weakToStrongObjects()
    private static var focusObservationOwner: UUID?
    private static let focusRecords = NSMapTable<UITextView, FocusRecord>.weakToStrongObjects()

    enum FocusEvent: String, CaseIterable, Hashable {
        case initialRequested, publisherRequested, retained, scheduled
        case cancelledState, cancelledLifetime, cancelledSuperseded
        case consumed, nativeAttempted, nativeAcquired, nativeRefused, nativeBegan
    }

    enum NativeFocusEvent: String, CaseIterable, Hashable {
        case setFocusAlreadyFirst, setFocusEligible, setFocusIneligible
        case becomeInvoked, becomeReturnedTrue, becomeReturnedFalse
        case shouldBeginEntered, shouldBeginAllowed, delegateDidBegin, delegateDidEnd
    }

    private final class FocusRecord: NSObject {
        var counts: [FocusEvent: Int] = [:]
        var requestID: UUID?
        var ownerID: UUID?
        var ownerMatchedAtLastEvent = false
        var lastEvent: FocusEvent?
        var lockedAtLastEvent = false
        var interactionAtLastEvent = false
        var nativeCounts: [NativeFocusEvent: Int] = [:]
        var nativeTrace = [String]()
        var nativeTraceTruncated = false
    }

    /// Explicitly scoped by the native preparation test. No application flow enables it,
    /// and these observations never participate in the editor's focus decisions.
    static func beginFocusObservation() -> UUID {
        let owner = UUID()
        focusObservationOwner = owner
        focusRecords.removeAllObjects()
        return owner
    }

    static func endFocusObservation(_ owner: UUID) {
        guard focusObservationOwner == owner else { return }
        focusObservationOwner = nil
        focusRecords.removeAllObjects()
    }

    static func recordFocus(
        _ event: FocusEvent, in textView: UITextView, requestID: UUID?, ownerID: UUID?, ownerMatches: Bool
    ) {
        guard focusObservationOwner != nil else { return }
        let record = focusRecords.object(forKey: textView) ?? FocusRecord()
        record.counts[event] = min((record.counts[event] ?? 0) + 1, 999)
        record.requestID = requestID
        record.ownerID = ownerID
        record.ownerMatchedAtLastEvent = ownerMatches
        record.lastEvent = event
        record.lockedAtLastEvent = (textView as? TextViewWithPlaceholder)?.isLockedForEditing == true
        record.interactionAtLastEvent = textView.isUserInteractionEnabled
        focusRecords.setObject(record, forKey: textView)
    }

    /// Observes the original guard, single UIKit call and delegate callbacks. It never asks
    /// for focus, calls canBecomeFirstResponder again, changes a return value or retries.
    static func recordNativeFocus(_ event: NativeFocusEvent, in textView: UITextView) {
        guard focusObservationOwner != nil else { return }
        let record = focusRecords.object(forKey: textView) ?? FocusRecord()
        record.nativeCounts[event] = min((record.nativeCounts[event] ?? 0) + 1, 999)
        if record.nativeTrace.count < 32 {
            record.nativeTrace.append("\(event.rawValue){\(nativeFocusState(in: textView))}")
        } else {
            record.nativeTraceTruncated = true
        }
        // Native callbacks must not overwrite the request/owner evidence from the row.
        focusRecords.setObject(record, forKey: textView)
    }

    private static func nativeFocusState(in textView: UITextView) -> String {
        var ancestor: UIView? = textView
        var depth = 0
        var hidden = 0
        var transparent = 0
        var noninteractive = 0
        var emptyBounds = 0
        var animating = 0
        while let view = ancestor, depth < 64 {
            depth += 1
            hidden += view.isHidden ? 1 : 0
            transparent += view.alpha <= 0.01 ? 1 : 0
            noninteractive += view.isUserInteractionEnabled ? 0 : 1
            emptyBounds += view.bounds.width > 0 && view.bounds.height > 0 ? 0 : 1
            animating += view.layer.animationKeys()?.isEmpty == false ? 1 : 0
            ancestor = view.superview
        }
        let window = textView.window
        let intersectsWindow = window.map { textView.convert(textView.bounds, to: $0).intersects($0.bounds) } ?? false
        return [
            "attached:\(window != nil)", "key:\(window?.isKeyWindow == true)",
            "sceneActive:\(window?.windowScene?.activationState == .foregroundActive)",
            "appActive:\(UIApplication.shared.applicationState == .active)",
            "editable:\(textView.isEditable)", "selectable:\(textView.isSelectable)",
            "locked:\((textView as? TextViewWithPlaceholder)?.isLockedForEditing == true)",
            "first:\(textView.isFirstResponder)", "intersectsWindow:\(intersectsWindow)",
            "depth:\(depth)", "hidden:\(hidden)", "transparent:\(transparent)",
            "noninteractive:\(noninteractive)", "emptyBounds:\(emptyBounds)", "animating:\(animating)",
            "customDelegate:\(textView.delegate is CustomTextView)",
            "accessory:\(textView.inputAccessoryView != nil)",
            "sceneResponders:\(nativeSceneResponders(in: window?.windowScene))"
        ].joined(separator: ",")
    }

    /// Only responder categories and a resignability flag are retained. The bounded walk
    /// does not load controllers, request layout or perform any responder-chain action.
    private static func nativeSceneResponders(in scene: UIWindowScene?) -> String {
        let viewBudget = 512
        let windows = scene?.windows ?? []
        var pending: [UIView] = windows.prefix(viewBudget).map { $0 as UIView }
        var traversalTruncated = windows.count > viewBudget
        var seen = Set<ObjectIdentifier>()
        var first = [String]()
        var firstTruncated = false
        var visited = 0
        while visited < viewBudget, let view = pending.popLast() {
            visited += 1
            let children = view.subviews
            let room = max(0, viewBudget - visited - pending.count)
            traversalTruncated = traversalTruncated || children.count > room
            pending.append(contentsOf: children.prefix(room))
            var next: UIResponder? = view
            while let responder = next, seen.count < 1024, seen.insert(ObjectIdentifier(responder)).inserted {
                if responder.isFirstResponder {
                    let category: String
                    switch responder {
                    case is UITextView: category = "textView"
                    case is UITextField: category = "textField"
                    case is UIViewController: category = "controller"
                    case is UIWindow: category = "window"
                    case is UIView: category = "view"
                    case is UIApplication: category = "application"
                    default: category = "other"
                    }
                    if first.count < 8 {
                        first.append("\(category)-canResign-\(responder.canResignFirstResponder)")
                    } else {
                        firstTruncated = true
                    }
                }
                next = responder.next
            }
        }
        let truncated = traversalTruncated || firstTruncated || !pending.isEmpty || seen.count >= 1024
        return "\(first.isEmpty ? "none" : first.joined(separator: "+"))-truncated-\(truncated)"
    }

    /// Fixed names, bounded counts, an ephemeral request UUID and UIKit state only.
    /// No document ID, user text, attribute payload or arbitrary error message is copied.
    static func focusObservation(in textView: UITextView) -> String {
        let record = focusRecords.object(forKey: textView)
        let events = FocusEvent.allCases.map { "\($0.rawValue)=\(record?.counts[$0] ?? 0)" }
        let nativeEvents = NativeFocusEvent.allCases.map { "\($0.rawValue)=\(record?.nativeCounts[$0] ?? 0)" }
        return (events + nativeEvents + [
            "recorded=\(record != nil)",
            "request=\(record?.requestID?.uuidString ?? "none")",
            "owner=\(record?.ownerID?.uuidString ?? "none")",
            "ownerMatchedAtLastEvent=\(record?.ownerMatchedAtLastEvent == true)",
            "lastEvent=\(record?.lastEvent?.rawValue ?? "unrecorded")",
            "lockedAtLastEvent=\(record?.lockedAtLastEvent == true)",
            "interactionAtLastEvent=\(record?.interactionAtLastEvent == true)",
            "attached=\(textView.window != nil)",
            "keyWindow=\(textView.window?.isKeyWindow == true)",
            "sceneActive=\(textView.window?.windowScene?.activationState == .foregroundActive)",
            "editable=\(textView.isEditable)",
            "interaction=\(textView.isUserInteractionEnabled)",
            "locked=\((textView as? TextViewWithPlaceholder)?.isLockedForEditing == true)",
            "firstResponder=\(textView.isFirstResponder)",
            "nativeTraceTruncated=\(record?.nativeTraceTruncated == true)",
            "nativeTrace=\(record?.nativeTrace.joined(separator: "|") ?? "none")"
        ]).joined(separator: " ")
    }

    static func resetInsertionEvidence(in textView: UITextView) {
        acceptedInsertions.removeObject(forKey: textView)
    }

    /// Observation only, called after the original host accepts a real empty replacement.
    static func recordAcceptedInsertion(in textView: UITextView, range: NSRange, replacement: String) {
        guard PinkhaStage1AcceptanceState.isEnabled, textView.isFirstResponder,
              textView.textStorage.length == 0, range == NSRange(location: 0, length: 0),
              !replacement.isEmpty else { return }
        let name: String
        switch (textView.typingAttributes[.paragraphStyle] as? NSParagraphStyle)?.baseWritingDirection {
        case .rightToLeft: name = "rtl"
        case .leftToRight: name = "ltr"
        default: name = "natural-or-missing"
        }
        acceptedInsertions.setObject(name as NSString, forKey: textView)
    }

    static func record(
        layoutDirection: LayoutDirection,
        navigationView: UIView
    ) {
        guard PinkhaStage1AcceptanceState.isEnabled else { return }
        swiftUILayoutDirection = layoutDirection
        navigationLayoutDirection = navigationView.effectiveUserInterfaceLayoutDirection
    }

    static func textViewLabel(
        decision: PinkhaWritingDirectionDecision,
        origin: PinkhaParagraphOrigin,
        textView: UITextView
    ) -> String {
        let appLanguage = Bundle.main.preferredLocalizations.first ?? "und"
        let deviceLanguage = ProcessInfo.processInfo.environment[
            PinkhaStage1AcceptanceState.deviceLanguageEnvironmentKey
        ] ?? "unrecorded"
        let documentKind = PinkhaStage1AcceptanceState.requestedDocumentKind.rawValue
        let typingStyle = textView.typingAttributes[.paragraphStyle] as? NSParagraphStyle
        let typingDirection: String
        switch typingStyle?.baseWritingDirection {
        case .rightToLeft: typingDirection = "rtl"
        case .leftToRight: typingDirection = "ltr"
        default: typingDirection = "natural-or-missing"
        }
        let caretSide: String
        if let range = textView.selectedTextRange, range.isEmpty, textView.isFirstResponder {
            let caret = textView.caretRect(for: range.start)
            let midpoint = textView.bounds.midX
            caretSide = caret.midX >= midpoint ? "right" : "left"
        } else {
            caretSide = "unavailable"
        }
        return [
            "Pinkha Stage 1",
            "document-\(documentKind)",
            "app-language-\(appLanguage)",
            "device-language-requested-\(deviceLanguage)",
            "swiftui-\(swiftUILayoutDirection.acceptanceName)",
            "navigation-\(navigationLayoutDirection.acceptanceName)",
            "uikit-\(textView.effectiveUserInterfaceLayoutDirection.acceptanceName)",
            decision.baseWritingDirection == .rightToLeft ? "content-rtl" : "content-ltr",
            "alignment-\(decision.alignment.acceptanceName)",
            "origin-\(origin.acceptanceName)",
            "typing-direction-\(typingDirection)",
            "caret-side-\(caretSide)",
            "text-empty-\(textView.textStorage.length == 0)",
            "first-responder-\(textView.isFirstResponder)",
            "accepted-first-insertion-\(acceptedInsertions.object(forKey: textView).map { $0 as String } ?? "unrecorded")"
        ].joined(separator: ";")
    }
}

private extension Optional where Wrapped == LayoutDirection {
    var acceptanceName: String {
        guard let direction = self else { return "missing" }
        return direction == .rightToLeft ? "rtl" : "ltr"
    }
}

private extension Optional where Wrapped == UIUserInterfaceLayoutDirection {
    var acceptanceName: String {
        guard let direction = self else { return "missing" }
        return direction.acceptanceName
    }
}

private extension UIUserInterfaceLayoutDirection {
    var acceptanceName: String {
        switch self {
        case .rightToLeft: "rtl"
        case .leftToRight: "ltr"
        @unknown default: "unknown"
        }
    }
}

private extension PinkhaParagraphAlignment {
    var acceptanceName: String {
        switch self {
        case .left: "left"
        case .center: "center"
        case .right: "right"
        case .justified: "justified"
        case .natural: "natural"
        }
    }
}

private extension PinkhaParagraphOrigin {
    var acceptanceName: String {
        switch self {
        case .newParagraph: "new"
        case .existingParagraph: "existing"
        case .ambiguousLegacyParagraph: "legacy-display-only"
        }
    }
}
