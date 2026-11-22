import Foundation

// Fixture only: observes timing at the extracted property/type boundary.
// No SwiftUI, native owner, RPC, original AsyncButton body or UI is executed.
@MainActor
private final class PreparationModelProbe {
    var hasDocumentWriteOwner = false
    var preparedUndo = 0
    var preparedRedo = 0
    var executedUndo = 0
    var executedRedo = 0
    func prepareUndo() -> @MainActor @Sendable () async throws -> Void {
        preparedUndo += 1
        return { self.executedUndo += 1 }
    }
    func prepareRedo() -> @MainActor @Sendable () async throws -> Void {
        preparedRedo += 1
        return { self.executedRedo += 1 }
    }
}

@MainActor
private struct ExtractedPreparationProbe {
    let model: PreparationModelProbe
    private var undoPreparation: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? {
        guard model.hasDocumentWriteOwner else { return nil }
        return { model.prepareUndo() }
    }

    private var redoPreparation: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? {
        guard model.hasDocumentWriteOwner else { return nil }
        return { model.prepareRedo() }
    }


    // Exact original AsyncButton.prepareAction stored type.
    private func acceptedPreparation(_ value: (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))?) -> (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? {
        value
    }

    func observe() async throws {
        precondition(acceptedPreparation(undoPreparation) == nil)
        precondition(acceptedPreparation(redoPreparation) == nil)
        precondition(model.preparedUndo == 0 && model.preparedRedo == 0)
        print("PASS legacy owner absence returns nil without preparation")

        model.hasDocumentWriteOwner = true
        let undo = acceptedPreparation(undoPreparation)
        let redo = acceptedPreparation(redoPreparation)
        precondition(undo != nil && redo != nil)
        precondition(model.preparedUndo == 0 && model.preparedRedo == 0)
        precondition(model.executedUndo == 0 && model.executedRedo == 0)
        print("PASS obtaining typed properties defers preparation and operation")

        let preparedUndo = undo!()
        let preparedRedo = redo!()
        precondition(model.preparedUndo == 1 && model.preparedRedo == 1)
        precondition(model.executedUndo == 0 && model.executedRedo == 0)
        print("PASS invoking original-shaped preparation performs only synchronous preparation")

        try await preparedUndo()
        try await preparedRedo()
        precondition(model.preparedUndo == 1 && model.preparedRedo == 1)
        precondition(model.executedUndo == 1 && model.executedRedo == 1)
        print("PASS awaiting returned actions reaches deferred operations")
    }
}
@main
private struct ProbeMain {
    @MainActor static func main() async throws {
        try await ExtractedPreparationProbe(model: PreparationModelProbe()).observe()
    }
}
