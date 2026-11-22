import Foundation
import SwiftUI
import Services
import AnytypeCore
import ProtobufMessages

enum PublishAction: Sendable {
    case create
    case update
}

@MainActor
@Observable
final class PublishToWebInternalViewModel: PublishingPreviewOutput {

    var customPath: String = ""
    var showJoinSpaceButton: Bool = true
    var status: PublishState?

    var previewData: PublishingPreviewData = .empty
    var toastBarData: ToastBarData?

    let domain: DomainType
    let objectDetails: ObjectDetails
    let spaceType: SpaceType

    @ObservationIgnored
    private weak var output: (any PublishToWebModuleOutput)?

    @ObservationIgnored
    @Injected(\.publishingService)
    private var publishingService: any PublishingServiceProtocol
    @ObservationIgnored
    @Injected(\.publishingPreviewBuilder)
    private var previewBuilder: any PublishingPreviewBuilderProtocol
    @ObservationIgnored
    @Injected(\.publishedUrlBuilder)
    private var urlBuilder: any PublishedUrlBuilderProtocol

    @ObservationIgnored
    private let spaceId: String
    @ObservationIgnored
    private let objectId: String
    @ObservationIgnored
    private let preparedSession: PreparedEditorPageSession?
    
    private var analyticsObjectType: AnalyticsObjectType {
        return objectDetails.objectType.analyticsType
    }
    
    init(data: PublishToWebViewInternalData, output: (any PublishToWebModuleOutput)?,
         preparedSession: PreparedEditorPageSession? = nil) {
        spaceId = data.spaceId
        objectId = data.objectId
        domain = data.domain
        status = data.status
        objectDetails = data.objectDetails
        spaceType = data.spaceType
        self.output = output
        self.preparedSession = preparedSession
        
        customPath = data.status?.uri ?? data.objectDetails.name
        showJoinSpaceButton = data.status?.joinSpace ?? true
        
        try? withCurrentSource {
            previewData = previewBuilder.buildPreviewData(
                from: data.objectDetails,
                spaceName: data.spaceName,
                showJoinButton: showJoinSpaceButton
            )
        }
    }

    var hasPreparedSource: Bool { preparedSession != nil }

    private func withCurrentSource<Value>(_ operation: () throws -> Value) throws -> Value {
        guard let preparedSession else { return try operation() }
        return try preparedSession.owner.performSynchronousOperation(
            contextId: objectId, spaceId: spaceId, requiresEditing: false
        ) {
            try preparedSession.owner.validateDocument(preparedSession.document)
            guard objectDetails.id.utf8.elementsEqual(objectId.utf8),
                  objectDetails.spaceId.utf8.elementsEqual(spaceId.utf8) else {
                throw EditorDocumentWriteError.rejected(.wrongContext)
            }
            guard preparedSession.document.permissions.canPublish else {
                throw EditorDocumentWriteError.rejected(.notEditable)
            }
            return try operation()
        }
    }

    private func originalPublishingService() throws -> any PublishingServiceProtocol {
        guard preparedSession != nil else { return publishingService }
        guard let original = publishingService as? PublishingService else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        return original
    }

    private func getStatus(from service: any PublishingServiceProtocol) async throws -> PublishState? {
        guard preparedSession != nil else {
            return try await service.getStatus(spaceId: spaceId, objectId: objectId)
        }
        guard let original = service as? PublishingService else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        return try await original.getStatusForOriginalEditor(spaceId: spaceId, objectId: objectId)
    }

    private func validateStatusIdentity(_ value: PublishState?) throws {
        guard preparedSession != nil, let value else { return }
        guard value.objectId.utf8.elementsEqual(objectId.utf8),
              value.spaceId.utf8.elementsEqual(spaceId.utf8) else {
            throw EditorDocumentWriteError.rejected(.wrongContext)
        }
    }

    func preparePublish(action: PublishAction) -> @MainActor @Sendable () async throws -> Void {
        prepareAction { [self] in try await onPublishTap(action: action) }
    }

    func prepareUnpublish() -> @MainActor @Sendable () async throws -> Void {
        prepareAction { [self] in try await onUnpublishTap() }
    }

    private func prepareAction(
        operation: @escaping @MainActor @Sendable () async throws -> Void
    ) -> @MainActor @Sendable () async throws -> Void {
        guard let preparedSession else { return operation }
        do {
            let scheduled = try preparedSession.owner.scheduleDocumentAction(
                contextId: objectId, requiredPermissions: [.publish]
            )
            return { try await scheduled.run(operation: operation) }
        } catch {
            return { throw error }
        }
    }

    private func performAction(
        operation: @MainActor @Sendable () async throws -> Void
    ) async throws {
        guard let preparedSession else { try await operation(); return }
        try await preparedSession.owner.performDocumentAction(
            contextId: objectId, requiredPermissions: [.publish]
        ) { @MainActor [self] in
            try withCurrentSource {}
            try await operation()
        }
    }
    
    func onPublishTap(action: PublishAction) async throws {
        try await performAction { [self] in
            switch action {
            case .create:
                AnytypeAnalytics.instance().logClickShareObjectPublish(objectType: analyticsObjectType)
            case .update:
                AnytypeAnalytics.instance().logClickShareObjectUpdate(objectType: analyticsObjectType)
            }

            let service = try originalPublishingService()
            try await service.create(spaceId: spaceId, objectId: objectId, uri: customPath, joinSpace: showJoinSpaceButton)
            let updatedStatus = try await getStatus(from: service)

            try withCurrentSource {
                try validateStatusIdentity(updatedStatus)
                status = updatedStatus
                if status.isNotNil {
                    switch action {
                    case .create:
                        AnytypeAnalytics.instance().logShareObjectPublish(objectType: analyticsObjectType)
                        toastBarData = ToastBarData(Loc.PublishingToWeb.published)
                    case .update:
                        AnytypeAnalytics.instance().logShareObjectUpdate(objectType: analyticsObjectType)
                        toastBarData = ToastBarData(Loc.PublishingToWeb.updated)
                    }
                }

                UINotificationFeedbackGenerator().notificationOccurred(.success)
            }
        }
    }
    
    func onUnpublishTap() async throws {
        try await performAction { [self] in
            AnytypeAnalytics.instance().logClickShareObjectUnpublish(objectType: analyticsObjectType)

            let service = try originalPublishingService()
            try await service.remove(spaceId: spaceId, objectId: objectId)
            let updatedStatus = try await getStatus(from: service)

            try withCurrentSource {
                try validateStatusIdentity(updatedStatus)
                status = updatedStatus
                if status.isNil {
                    AnytypeAnalytics.instance().logShareObjectUnpublish(objectType: analyticsObjectType)
                    toastBarData = ToastBarData(Loc.PublishingToWeb.unpublished)
                }

                UINotificationFeedbackGenerator().notificationOccurred(.success)
            }
        }
    }
    
    func onFreeDomainTap() {
        try? withCurrentSource {
            AnytypeAnalytics.instance().logClickUpgradePlanTooltip(type: .publish, route: .publish)
            output?.onShowMembership()
        }
    }
    
    func updatePreviewForJoinButton(_ showJoin: Bool) {
        try? withCurrentSource {
            AnytypeAnalytics.instance().logJoinSpaceButtonToPublish(objectType: analyticsObjectType, type: showJoin)
            previewData = previewBuilder.buildPreviewData(
                from: previewData,
                showJoinButton: showJoin
            )
        }
    }
    
    // MARK: - PublishingPreviewOutput
    
    func onPreviewOpenWebPage() {
        try? withCurrentSource {
            AnytypeAnalytics.instance().logClickShareObjectOpenPage(objectType: analyticsObjectType, route: .menu)
            guard let publishedUrl = urlBuilder.buildPublishedUrl(domain: domain, customPath: customPath) else { return }
            output?.onOpenPreview(url: publishedUrl)
        }
    }
    
    func onPreviewShareLink() {
        try? withCurrentSource {
            AnytypeAnalytics.instance().logClickShareObjectShareLink(objectType: analyticsObjectType)
            guard let publishedUrl = urlBuilder.buildPublishedUrl(domain: domain, customPath: customPath) else { return }
            output?.onSharePreview(url: publishedUrl)
        }
    }
    
    func onPreviewCopyLink() {
        try? withCurrentSource {
            AnytypeAnalytics.instance().logClickShareObjectCopyUrl(objectType: analyticsObjectType)
            guard let publishedUrl = urlBuilder.buildPublishedUrl(domain: domain, customPath: customPath) else { return }
            UIPasteboard.general.string = publishedUrl.absoluteString
            toastBarData = ToastBarData(Loc.copiedToClipboard(Loc.link))
        }
    }
}
