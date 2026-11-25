import Foundation
import SwiftUI
import PinkhaSharing

struct SpaceMembersView: View {

    @State private var model: SpaceMembersViewModel
    @State private var sharingService: HeartSpaceSharingService?
    @State private var showSharing = false

    init(data: SpaceMembersData) {
        _model = State(initialValue: SpaceMembersViewModel(data: data))
    }
    
    var body: some View {
        VStack(spacing: 0) {
            DragIndicator()
            TitleView(title: Loc.SpaceShare.members)
            Button {
                if let service = try? model.makeSharingService() {
                    sharingService = service
                    showSharing = true
                }
            } label: {
                Label(Loc.SpaceShare.members, systemImage: "person.2.badge.gearshape")
            }
            .accessibilityIdentifier("pinkha.sharing.manage")
            .padding(.bottom, 8)
            
            ScrollView {
                VStack(spacing: 0) {
                    ForEach(model.rows) { participant in
                        SpaceShareParticipantView(participant: participant)
                    }
                }
                .padding(.horizontal, 16)
            }
        }
        .task {
            await model.startParticipantTask()
        }
        .task {
            await model.startSpacePermissionsTask()
        }
        .onAppear {
            model.onAppear()
        }
        .sheet(isPresented: $showSharing, onDismiss: { sharingService = nil }) {
            if let sharingService { PinkhaSpaceMembersView(service: sharingService) }
        }
        .anytypeSheet(item: $model.participantInfo) {
            ProfileView(info: $0)
        }
    }
}
