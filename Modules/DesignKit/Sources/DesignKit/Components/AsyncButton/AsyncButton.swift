import Foundation
import SwiftUI

public struct AsyncButton<Label> : View where Label : View {
    
    let action: @Sendable () async throws -> Void
    let label: Label
    let role: ButtonRole?
    let prepareAction: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))?

    private struct PreparedAction: Sendable {
        let id = UUID()
        let action: @MainActor @Sendable () async throws -> Void
    }
    
    @State private var taskId: UUID?
    @State private var disable = false
    @State private var preparedAction: PreparedAction?
    
    public init(role: ButtonRole? = nil,
                prepareAction: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? = nil,
                action: @Sendable @escaping @MainActor () async throws -> Void, @ViewBuilder label: () -> Label) {
        self.action = action
        self.prepareAction = prepareAction
        self.role = role
        self.label = label()
    }
    
    public var body: some View {
        Button(role: role) {
            if let prepareAction {
                // Capture a per-tap admission before SwiftUI creates its task.
                // Another tap cannot replace an accepted, unstarted action.
                guard taskId == nil else { return }
                let prepared = PreparedAction(action: prepareAction())
                preparedAction = prepared
                taskId = prepared.id
            } else {
                taskId = UUID()
            }
        } label: {
            label
        }
        .throwingTask(id: taskId) {
            guard taskId.isNotNil else { return }
            let prepared = preparedAction
            guard prepareAction == nil || prepared != nil else { return }
            defer {
                if let prepared {
                    if taskId == prepared.id {
                        taskId = nil
                        preparedAction = nil
                    }
                } else {
                    taskId = nil
                }
            }
            do {
                disable = true
                defer { disable = false }
                if let prepared {
                    try await prepared.action()
                } else {
                    try await action()
                }
            } catch {
                throw error
            }
        }
        .disabled(disable)
    }
}

public extension AsyncButton where Label == Text {
    init(_ titleKey: String, role: ButtonRole? = nil, action: @Sendable @escaping @MainActor () async throws -> Void) {
        self = AsyncButton(role: role, action: action, label: {
            Text(titleKey)
        })
    }
}
