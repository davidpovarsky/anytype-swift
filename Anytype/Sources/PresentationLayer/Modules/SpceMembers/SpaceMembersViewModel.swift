import Foundation
import Services
import PinkhaSharing

struct SpaceMembersData: Identifiable, Hashable {
    let spaceId: String
    let route: SettingsSpaceMembersRoute
    var id: Int { hashValue }
}

@MainActor
@Observable
final class SpaceMembersViewModel {

    var participantInfo: ObjectInfo?

    // MARK: - DI

    @ObservationIgnored
    @Injected(\.accountManager)
    private var accountManager: any AccountManagerProtocol
    @ObservationIgnored
    @Injected(\.participantSpacesStorage)
    private var participantSpacesStorage: any ParticipantSpacesStorageProtocol
    @ObservationIgnored
    private lazy var participantsSubscription: any ParticipantsSubscriptionProtocol = Container.shared.participantSubscription(data.spaceId)

    private let data: SpaceMembersData

    // MARK: - State

    var rows: [SpaceShareParticipantViewModel] = []
    @ObservationIgnored
    private var isOwner = false
    @ObservationIgnored
    private var participants: [Participant] = []
    @ObservationIgnored
    private var currentSpace: ParticipantSpaceViewData?

    func makeSharingService() throws -> HeartSpaceSharingService {
        let scope = try PinkhaSharingScope(engine: .heart, accountID: accountManager.account.id,
                                           spaceID: data.spaceId)
        return try HeartSpaceSharingService(scope: scope) { [weak self] in
            guard let self, let space = self.currentSpace,
                  self.accountManager.account.id == scope.accountID else {
                throw PinkhaSharingError.staleContext
            }
            return (self.participants, space)
        }
    }
    
    init(data: SpaceMembersData) {
        self.data = data
    }
    
    func startParticipantTask() async {
        for await participants in participantsSubscription.withoutRemovingParticipantsPublisher.values {
            self.participants = participants
            updateParticipant()
        }
    }

    func startSpacePermissionsTask() async {
        for await participantSpaceView in participantSpacesStorage.participantSpaceViewPublisher(spaceId: data.spaceId).values {
            currentSpace = participantSpaceView
            isOwner = participantSpaceView.isOwner
            updateParticipant()
        }
    }
    
    func onAppear() {
        AnytypeAnalytics.instance().logScreenSettingsSpaceMembers(route: data.route)
    }
    
    private func updateParticipant() {
        let filteredParticipants = participants.filter { participant in
            if participant.status == .joining {
                return isOwner
            }
            return true
        }

        rows = filteredParticipants.map { participant in
            let isYou = accountManager.account.info.profileObjectID == participant.identityProfileLink
            return SpaceShareParticipantViewModel(
                id: participant.id,
                icon: participant.icon?.icon,
                name: isYou ? Loc.SpaceShare.youSuffix(participant.title) : participant.title,
                globalName: participant.displayGlobalName,
                status: .active(permission: participant.permission.title),
                action: SpaceShareParticipantViewModel.Action(title: nil, action: { [weak self] in
                    self?.showParticipantInfo(participant)
                }),
                contextActions: []
            )
        }
    }
    
    private func showParticipantInfo(_ participant: Participant) {
        participantInfo = ObjectInfo(objectId: participant.id, spaceId: participant.spaceId)
    }
}
