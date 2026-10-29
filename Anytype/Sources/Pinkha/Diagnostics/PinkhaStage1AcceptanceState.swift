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
        return [
            "Pinkha Stage 1",
            "document-\(documentKind)",
            "app-language-\(appLanguage)",
            "device-language-\(deviceLanguage)",
            "swiftui-\(swiftUILayoutDirection.acceptanceName)",
            "navigation-\(navigationLayoutDirection.acceptanceName)",
            "uikit-\(textView.effectiveUserInterfaceLayoutDirection.acceptanceName)",
            decision.baseWritingDirection == .rightToLeft ? "content-rtl" : "content-ltr",
            "alignment-\(decision.alignment.acceptanceName)",
            "origin-\(origin.acceptanceName)"
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
