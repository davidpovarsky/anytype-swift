import Foundation
import SwiftUI
import UIKit

@MainActor
protocol PublishToWebModuleOutput: AnyObject {
    func onShowMembership()
    func onSharePreview(url: URL)
    func onOpenPreview(url: URL)
}

@MainActor
final class PublishToWebCoordinatorModel: ObservableObject, PublishToWebModuleOutput {
    
    @Published var showMembership = false
    @Published var sharedUrl: URL?
    @Published var safariUrl: URL?
    
    let data: PublishToWebViewData
    let preparedSession: PreparedEditorPageSession?
    
    init(data: PublishToWebViewData, preparedSession: PreparedEditorPageSession? = nil) {
        self.data = data
        self.preparedSession = preparedSession
    }

    private func publish(_ operation: () throws -> Void) {
        guard let preparedSession else { try? operation(); return }
        try? preparedSession.owner.performSynchronousOperation(
            contextId: data.objectId, spaceId: data.spaceId, requiresEditing: false
        ) {
            try preparedSession.owner.validateDocument(preparedSession.document)
            try operation()
        }
    }
    
    // MARK: - PublishToWebModuleOutput
    
    func onShowMembership() {
        publish {
            // Account membership is a separate original account route; a page
            // source does not grant purchase or account-management authority.
            guard preparedSession == nil else {
                throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
            }
            showMembership = true
        }
    }
    
    func onSharePreview(url: URL) {
        publish { sharedUrl = url }
    }
    
    func onOpenPreview(url: URL) {
        publish { safariUrl = url }
    }
}
