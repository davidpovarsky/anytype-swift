import Services
import SwiftUI

@MainActor
protocol ObjectVersionModuleOutput: AnyObject {
    func versionRestored(_ text: String)
}

@MainActor
@Observable
final class ObjectVersionViewModel {

    var screenData: EditorScreenData?
    var preparedEditorModel: EditorPageCoordinatorViewModel?
    var preparationFailed = false
    var dismiss = false

    let data: ObjectVersionData
    @ObservationIgnored
    private let preparedSession: PreparedEditorPageSession?
    @ObservationIgnored
    private var versionSession: PreparedEditorPageSession?
    @ObservationIgnored
    private var preparationStarted = false

    var hasPreparedSource: Bool { preparedSession != nil }

    @ObservationIgnored
    @Injected(\.historyVersionsService)
    private var historyVersionsService: any HistoryVersionsServiceProtocol

    @ObservationIgnored
    private weak var output: (any ObjectVersionModuleOutput)?
    
    init(data: ObjectVersionData, output: (any ObjectVersionModuleOutput)?,
         preparedSession: PreparedEditorPageSession? = nil) {
        self.data = data
        self.output = output
        self.preparedSession = preparedSession
    }
    
    func onAppear() {
        try? withCurrentSource { AnytypeAnalytics.instance().logScreenHistoryVersion() }
    }
    
    func setupObject() async {
        guard let preparedSession else {
            self.screenData = currentScreenData()
            return
        }
        guard !preparationStarted else { return }
        preparationStarted = true
        var acquired: PreparedEditorPageSession?
        do {
            try withCurrentSource {
                guard !data.isListType, preparedSession.document.details?.isList == false,
                      !data.versionId.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                    throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
                }
            }
            let childPreparation = try PreparedEditorChildPreparation(owner: preparedSession.owner)
            let page = EditorPageObject(
                objectId: data.objectId, spaceId: data.spaceId,
                mode: .version(data.versionId), usecase: .embedded
            )
            let session = try await childPreparation.prepareReadOnlyVersion(data: page)
            acquired = session
            try session.owner.performSynchronousOperation(
                contextId: data.objectId, spaceId: data.spaceId, requiresEditing: false
            ) {
                try session.owner.validateDocument(session.document)
                guard let details = session.document.details,
                      details.id.utf8.elementsEqual(data.objectId.utf8), !details.isList else {
                    throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
                }
            }
            let model = try EditorPageCoordinatorViewModel(preparedSession: session, showHeader: false)
            try withCurrentSource {
                versionSession = session
                preparedEditorModel = model
                screenData = .page(page)
            }
        } catch {
            acquired?.retire()
            try? withCurrentSource { preparationFailed = true }
        }
    }
    
    func onCancelTap() {
        try? withCurrentSource { dismiss.toggle() }
    }
    
    func onRestoreTap() {
        if let preparedSession {
            do {
                // Reserve at the real button tap, before the original task is
                // created. Restoration belongs to the current handling owner,
                // never to the separately acquired read-only version owner.
                let scheduled = try preparedSession.owner.scheduleDocumentAction(
                    contextId: data.objectId, requiredPermissions: [.restoreVersionHistory]
                )
                Task { @MainActor [self] in
                    try await scheduled.run { @MainActor [self] in
                        try withCurrentSource {
                            guard data.canRestore,
                                  !data.versionId.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                                throw EditorDocumentWriteError.rejected(.notEditable)
                            }
                        }
                        let original = try OriginalHistoryVersionsServiceBinding.requireOriginal(historyVersionsService)
                        try await original.setVersion(objectId: data.objectId, versionId: data.versionId)
                        try withCurrentSource {
                            output?.versionRestored(data.title.trimmingCharacters(in: .whitespaces))
                            AnytypeAnalytics.instance().logRestoreFromHistory()
                        }
                    }
                }
            } catch { }
            return
        }
        Task {
            try await historyVersionsService.setVersion(objectId: data.objectId, versionId: data.versionId)
            output?.versionRestored(data.title.trimmingCharacters(in: .whitespaces))
            AnytypeAnalytics.instance().logRestoreFromHistory()
        }
    }

    private func withCurrentSource<Value>(_ operation: () throws -> Value) throws -> Value {
        guard let preparedSession else { return try operation() }
        return try preparedSession.owner.performSynchronousOperation(
            contextId: data.objectId, spaceId: data.spaceId, requiresEditing: false
        ) {
            try preparedSession.owner.validateDocument(preparedSession.document)
            return try operation()
        }
    }
    
    private func currentScreenData() -> EditorScreenData? {
        let mode: DocumentMode = .version(data.versionId)
        if data.isListType {
            return .list(
                EditorListObject(
                    objectId: data.objectId,
                    spaceId: data.spaceId,
                    mode: mode,
                    usecase: .embedded
                )
            )
        } else {
            return .page(
                EditorPageObject(
                    objectId: data.objectId,
                    spaceId: data.spaceId,
                    mode: mode,
                    usecase: .embedded
                )
            )
        }
    }
}

