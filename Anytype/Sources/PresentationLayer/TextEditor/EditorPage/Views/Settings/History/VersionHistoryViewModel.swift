import Services
import SwiftUI
import OrderedCollections

@MainActor
protocol VersionHistoryModuleOutput: AnyObject {
    func onVersionTap(title: String, icon: ObjectIcon?, versionId: String)
}

@MainActor
@Observable
final class VersionHistoryViewModel {

    var groups = [VersionHistoryDataGroup]()
    var expandedGroups: Set<String> = []
    var lastViewedVersionId = ""

    @ObservationIgnored
    private let objectId: String
    @ObservationIgnored
    private let spaceId: String
    @ObservationIgnored
    private var rawVersions = OrderedSet<VersionHistory>()
    @ObservationIgnored
    private var participantsDict = [String: Participant]()
    @ObservationIgnored
    private weak var output: (any VersionHistoryModuleOutput)?

    @ObservationIgnored
    private var firstOpen = true
    @ObservationIgnored
    private let preparedSession: PreparedEditorPageSession?
    @ObservationIgnored
    private var preparedParticipants: ParticipantsSubscription?

    @ObservationIgnored @Injected(\.historyVersionsService)
    private var historyVersionsService: any HistoryVersionsServiceProtocol
    @ObservationIgnored @Injected(\.versionHistoryDataBuilder)
    private var versionHistoryDataBuilder: any VersionHistoryDataBuilderProtocol

    @ObservationIgnored
    private lazy var participantsSubscription: any ParticipantsSubscriptionProtocol = Container.shared.participantSubscription(spaceId)
    
    init(data: VersionHistoryData, output: (any VersionHistoryModuleOutput)?,
         preparedSession: PreparedEditorPageSession? = nil) {
        self.objectId = data.objectId
        self.spaceId = data.spaceId
        self.output = output
        self.preparedSession = preparedSession
    }
    
    func onAppear() {
        try? withCurrentSource { AnytypeAnalytics.instance().logScreenHistory() }
    }
    
    func startParticipantsSubscription() async {
        let subscription: any ParticipantsSubscriptionProtocol
        if let preparedSession {
            do {
                try withCurrentSource {}
                let original = try await ParticipantsSubscription.prepareOriginal(
                    spaceId: spaceId, owner: preparedSession.owner
                )
                try withCurrentSource { preparedParticipants = original }
                subscription = original
            } catch { return }
        } else {
            subscription = participantsSubscription
        }
        for await participants in subscription.participantsPublisher.values {
            guard (try? withCurrentSource { () -> Void in
                participantsDict = [:]
                participants.forEach { participant in
                    participantsDict[participant.id] = participant
                }
                updateView()
            }) != nil else { return }
        }
    }

    private func withCurrentSource<Value>(_ operation: () throws -> Value) throws -> Value {
        guard let preparedSession else { return try operation() }
        return try preparedSession.owner.performSynchronousOperation(
            contextId: objectId, spaceId: spaceId, requiresEditing: false
        ) {
            try preparedSession.owner.validateDocument(preparedSession.document)
            return try operation()
        }
    }
    
    func getVersions() async {
        do {
            let newVersions: [VersionHistory]
            if let preparedSession {
                let cursor = try withCurrentSource { lastViewedVersionId }
                let original = try OriginalHistoryVersionsServiceBinding.requireOriginal(historyVersionsService)
                newVersions = try await preparedSession.owner.performRead(
                    contextId: objectId, spaceId: spaceId, rpcNames: ["HistoryGetVersions"]
                ) { [objectId] in
                    try await original.getVersions(objectId: objectId, lastVersionId: cursor)
                }
            } else {
                newVersions = try await historyVersionsService.getVersions(objectId: objectId, lastVersionId: lastViewedVersionId)
            }
            try withCurrentSource {
                rawVersions.append(contentsOf: newVersions)
                updateView()
            }
        } catch {
            try? withCurrentSource { groups = [] }
        }
    }
    
    func onAppearLastGroup(_ group: VersionHistoryDataGroup) {
        try? withCurrentSource {
            guard groups.last == group else { return }
            guard lastViewedVersionId != rawVersions.last?.id else { return }
            lastViewedVersionId = rawVersions.last?.id ?? ""
        }
    }
    
    func onGroupTap(_ group: VersionHistoryDataGroup) {
        try? withCurrentSource {
            if expandedGroups.contains(group.title) {
                expandedGroups.remove(group.title)
            } else {
                expandedGroups.insert(group.title)
            }
        }
    }
    
    func onVersionTap(_ version: VersionHistoryItem) {
        try? withCurrentSource {
            if preparedSession != nil {
                guard rawVersions.contains(where: { $0.id.utf8.elementsEqual(version.id.utf8) }) else {
                    throw EditorDocumentWriteError.rejected(.wrongContext)
                }
            }
            output?.onVersionTap(title: version.dateTime, icon: version.icon, versionId: version.id)
        }
    }
    
    private func updateView() {
        guard !rawVersions.isEmpty, !participantsDict.keys.isEmpty else { return }
        
        updateExpandedGroupsOnFirstOpen()
        groups = versionHistoryDataBuilder.buildData(for: rawVersions.elements, participants: participantsDict)
    }
    
    private func updateExpandedGroupsOnFirstOpen() {
        guard firstOpen else { return }
        
        if let firstGroupKey = versionHistoryDataBuilder.buildFirstGroupKey(
            for: rawVersions.elements,
            participants: participantsDict
        ) {
            expandedGroups.insert(firstGroupKey)
        }
        
        firstOpen = false
    }
}
