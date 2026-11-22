import SwiftUI
import DesignKit

@MainActor
struct ChatDeleteChatAlert: View {

    @Environment(\.dismiss) private var dismiss
    private let onDelete: () async throws -> Void
    private let prepareAction: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))?
    private let publish: (@MainActor (@MainActor () -> Void) throws -> Void)?

    init(
        prepareAction: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? = nil,
        publish: (@MainActor (@MainActor () -> Void) throws -> Void)? = nil,
        onDelete: @escaping () async throws -> Void
    ) {
        self.prepareAction = prepareAction
        self.publish = publish
        self.onDelete = onDelete
    }

    var body: some View {
        BottomAlertView(
            title: Loc.Chat.DeleteChat.title,
            message: Loc.Chat.DeleteChat.description,
            icon: .Dialog.question
        ) {
            BottomAlertButton(text: Loc.cancel, style: .secondary) {
                dismiss()
            }

            BottomAlertButton(text: Loc.moveToBin, style: .warning, prepareAction: preparedDelete) {
                try await onDelete()
                try dismissCurrentSource()
            }
        }
    }

    private var preparedDelete: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? {
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
