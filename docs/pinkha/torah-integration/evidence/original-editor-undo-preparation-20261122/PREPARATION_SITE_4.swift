import SwiftUI

@MainActor
struct ObjectSettingsResolveConflictAlert: View {
    
    @Environment(\.dismiss) private var dismiss
    private let onResolve: () async throws -> Void
    private let prepareAction: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))?
    private let publish: (@MainActor (@MainActor () -> Void) throws -> Void)?
    
    init(
        prepareAction: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? = nil,
        publish: (@MainActor (@MainActor () -> Void) throws -> Void)? = nil,
        onResolve: @escaping () async throws -> Void
    ) {
        self.prepareAction = prepareAction
        self.publish = publish
        self.onResolve = onResolve
    }
    
    var body: some View {
        BottomAlertView(
            title: Loc.resolveLayoutConflict,
            message: Loc.Primitives.LayoutConflict.description,
            buttons: {
                BottomAlertButton(
                    text: Loc.resetToDefault,
                    style: .primary,
                    prepareAction: preparedResolve
                ) {
                    try await onResolve()
                    try dismissCurrentSource()
                }
                
                BottomAlertButton(
                    text: Loc.cancel,
                    style: .secondary
                ) {
                    dismiss()
                }
            }
        )
    }

    private var preparedResolve: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? {
        guard let prepareAction else { return nil }
        return {
            let action = prepareAction()
            return {
                try await action()
                try dismissCurrentSource()
            }
        }
    }

    private func dismissCurrentSource() throws {
        if let publish { try publish { dismiss() } }
        else { dismiss() }
    }
}
