import Foundation
import SwiftUI
import Services
import AnytypeCore
import ProtobufMessages

enum PublishToWebViewModelState: Equatable {
    case initial
    case error(String)
    case loaded(PublishToWebViewInternalData)
}

@MainActor
@Observable
final class PublishToWebViewModel {
    var state = PublishToWebViewModelState.initial

    @ObservationIgnored
    @Injected(\.publishingService)
    private var publishingService: any PublishingServiceProtocol
    @ObservationIgnored
    @Injected(\.participantsStorage)
    private var participantStorage: any ParticipantsStorageProtocol
    @ObservationIgnored
    @Injected(\.documentsProvider)
    private var documentsProvider: any DocumentsProviderProtocol
    @ObservationIgnored
    @Injected(\.spaceViewsStorage)
    private var activeWorkspaceStorage: any SpaceViewsStorageProtocol

    private let spaceId: String
    private let objectId: String
    let preparedSession: PreparedEditorPageSession?
    
    init(data: PublishToWebViewData, preparedSession: PreparedEditorPageSession? = nil) {
        spaceId = data.spaceId
        objectId = data.objectId
        self.preparedSession = preparedSession
    }
    
    func onAppear() async {
        if preparedSession != nil {
            await loadPreparedObject()
            return
        }
        guard let domain = participantStorage.participants.first?.publishingDomain else {
            anytypeAssertionFailure("No participants found for account")
            state = .error(Loc.Publishing.Error.noDomain)
            return
        }
        
        let document = documentsProvider.document(objectId: objectId, spaceId: spaceId)
        
        // Open the document to ensure data exists
        try? await document.open()
        
        guard let objectDetails = document.details else {
            anytypeAssertionFailure("No details found object")
            state = .error(Loc.Publishing.Error.noObjectData)
            return
        }
        
        let spaceView = activeWorkspaceStorage.spaceView(spaceId: spaceId)
        let spaceName = spaceView?.title ?? ""
        let spaceType = spaceView?.spaceType ?? .regular

        do {
            let status: PublishState?
            if let newStatus = try await publishingService.getStatus(spaceId: spaceId, objectId: objectId) {
                status = newStatus
            } else {
                status = nil
            }
            
            state = .loaded(PublishToWebViewInternalData(
                objectId: objectId,
                spaceId: spaceId,
                domain: domain,
                status: status,
                objectDetails: objectDetails,
                spaceName: spaceName,
                spaceType: spaceType
            ))
        } catch {
            state = .error(error.localizedDescription)
        }
    }

    private func withCurrentSource<Value>(_ operation: () throws -> Value) throws -> Value {
        guard let preparedSession else { return try operation() }
        return try preparedSession.owner.performSynchronousOperation(
            contextId: objectId, spaceId: spaceId, requiresEditing: false
        ) {
            try preparedSession.owner.validateDocument(preparedSession.document)
            guard preparedSession.document.permissions.canPublish else {
                throw EditorDocumentWriteError.rejected(.notEditable)
            }
            return try operation()
        }
    }

    /// The prepared route reuses the exact already-open original document. It
    /// never reacquires a raw document or changes its captured account binding.
    private func loadPreparedObject() async {
        guard let preparedSession else { return }
        do {
            let initial: PublishToWebViewInternalData? = try withCurrentSource {
                guard let domain = participantStorage.participants.first?.publishingDomain else {
                    anytypeAssertionFailure("No participants found for account")
                    state = .error(Loc.Publishing.Error.noDomain)
                    return nil
                }
                guard let details = preparedSession.document.details else {
                    anytypeAssertionFailure("No details found object")
                    state = .error(Loc.Publishing.Error.noObjectData)
                    return nil
                }
                let spaceView = activeWorkspaceStorage.spaceView(spaceId: spaceId)
                return PublishToWebViewInternalData(
                    objectId: objectId, spaceId: spaceId, domain: domain, status: nil,
                    objectDetails: details, spaceName: spaceView?.title ?? "",
                    spaceType: spaceView?.spaceType ?? .regular
                )
            }
            guard let initial else { return }
            // PublishingService is the original public final implementation.
            // Keep the injected instance; a substitute cannot bypass Invocation.
            guard let original = publishingService as? PublishingService else {
                throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
            }
            let status = try await preparedSession.owner.performRead(
                contextId: objectId, spaceId: spaceId, rpcNames: ["PublishingGetStatus"]
            ) { [objectId, spaceId] in
                try await original.getStatusForOriginalEditor(spaceId: spaceId, objectId: objectId)
            }
            try withCurrentSource {
                if let status {
                    guard status.objectId.utf8.elementsEqual(objectId.utf8),
                          status.spaceId.utf8.elementsEqual(spaceId.utf8) else {
                        throw EditorDocumentWriteError.rejected(.wrongContext)
                    }
                }
                state = .loaded(PublishToWebViewInternalData(
                    objectId: initial.objectId, spaceId: initial.spaceId, domain: initial.domain,
                    status: status, objectDetails: initial.objectDetails,
                    spaceName: initial.spaceName, spaceType: initial.spaceType
                ))
            }
        } catch {
            try? withCurrentSource { state = .error(error.localizedDescription) }
        }
    }
}
