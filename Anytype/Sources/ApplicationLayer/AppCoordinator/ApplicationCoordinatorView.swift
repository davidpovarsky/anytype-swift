import Foundation
import SwiftUI
import AnytypeCore

struct ApplicationCoordinatorView: View {
    
    @State private var model: ApplicationCoordinatorViewModel
    @Environment(\.dismissAllPresented) private var dismissAllPresented
    private let ownsConsumerTasks: Bool
    private let embeddedInitial: AnyView?
    private let embeddedHome: AnyView?

    init() {
        _model = State(initialValue: ApplicationCoordinatorViewModel())
        ownsConsumerTasks = true
        embeddedInitial = nil
        embeddedHome = nil
    }

    /// The external process owner retains the same original model and tasks.
    /// This initializer does not create another model or start authentication.
    init(model: ApplicationCoordinatorViewModel, initial: AnyView, home: AnyView) {
        _model = State(initialValue: model)
        ownsConsumerTasks = false
        embeddedInitial = initial
        embeddedHome = home
    }
    
    var body: some View {
        ZStack {
            applicationView
        }
        .onAppear {
            model.setDismissAllPresented(dismissAllPresented: dismissAllPresented)
        }
        .task {
            if ownsConsumerTasks { await model.startAppStateHandler() }
        }
        .task {
            if ownsConsumerTasks { await model.startAccountStateHandler() }
        }
        .task {
            if ownsConsumerTasks { await model.startEncryptionKeyEventHandler() }
        }
        .task {
            if ownsConsumerTasks { await model.startFileHandler() }
        }
        .task(item: model.selectAccountTaskId) { accountId in
            await model.selectAccount(id: accountId)
        }
        .onChange(of: dismissAllPresented) {
            model.setDismissAllPresented(dismissAllPresented: $1)
        }
        .snackbar(toastBarData: $model.toastBarData)
        // migration
        .fullScreenCover(item: $model.migrationData) {
            MigrationCoordinatorView(data: $0)
        }
    }
    
    @ViewBuilder
    private var applicationView: some View {
        switch model.applicationState {
        case .initial:
            if let embeddedInitial { embeddedInitial } else { InitialCoordinatorView() }
        case .auth:
            AuthCoordinatorView()
        case .launch:
            LaunchView()
        case .home:
            if let embeddedHome { embeddedHome } else { SpaceHubCoordinatorView() }
        case .delete:
            model.deleteAccount()
        }
    }
}
