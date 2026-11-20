import UIKit
import AnytypeCore
import Services

@MainActor
@Observable
final class UndoRedoViewModel {

    private let objectActionsService: any ObjectActionsServiceProtocol

    private let objectId: String

    var toastData: ToastBarData?
    
    init(
        objectId: String,
        objectActionsService: any ObjectActionsServiceProtocol = Container.shared.objectActionsService()
    ) {
        self.objectId = objectId
        self.objectActionsService = objectActionsService
    }

    func undo() async throws {
        do {
            try await objectActionsService.undo(objectId: objectId)
            AnytypeAnalytics.instance().logUndo(resultType: .true)
        } catch let error as ObjectActionsServiceError {
            toastData = ToastBarData(error.localizedDescription, type: .neutral)
            AnytypeAnalytics.instance().logUndo(resultType: .false)
        }
    }

    func redo() async throws {
        do {
            try await objectActionsService.redo(objectId: objectId)
            AnytypeAnalytics.instance().logRedo(resultType: .true)
        } catch let error as ObjectActionsServiceError {
            toastData = ToastBarData(error.localizedDescription, type: .neutral)
            AnytypeAnalytics.instance().logRedo(resultType: .false)
        }
    }
}
