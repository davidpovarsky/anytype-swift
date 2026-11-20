import Foundation
import Combine
import UIKit

// TODO: Refactoring editor view controller
final class EditorPageViewState: ObservableObject {
    
    private var cancellable : AnyCancellable? = nil
    
    let viewController: EditorPageController
    var model: EditorPageViewModel
    private(set) var preparedSession: PreparedEditorPageSession?
 
    @MainActor
    func bindPreparedSession(_ session: PreparedEditorPageSession) throws {
        guard preparedSession == nil else {
            throw EditorDocumentWriteError.rejected(.invalidLease)
        }
        try session.bind(controller: viewController)
        preparedSession = session
    }

    init(viewController: EditorPageController, model: EditorPageViewModel) {
        self.viewController = viewController
        self.model = model
        self.cancellable = model.objectWillChange.receiveOnMain().sink { [weak self] in
            self?.objectWillChange.send()
        }
    }
    
}
