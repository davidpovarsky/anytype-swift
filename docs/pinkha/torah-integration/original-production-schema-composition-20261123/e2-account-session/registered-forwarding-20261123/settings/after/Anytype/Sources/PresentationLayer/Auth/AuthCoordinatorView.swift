import SwiftUI

struct AuthCoordinatorView: View {
    
    private enum Constants {
        static let animationDuration = 0.6
    }
    
    @State private var model = AuthCoordinatorViewModel()
    @State private var showCircle: Bool = false
    private let originalEditorCaller: OriginalEditorAuthCaller?

    init(originalEditorCaller: OriginalEditorAuthCaller? = nil) {
        self.originalEditorCaller = originalEditorCaller
    }
    
    var body: some View {
        NavigationStack {
            content
        }
        .authOverlayCircle(show: showCircle)
    }
    
    private var content: some View {
        PrimaryAuthView(output: model, originalEditorCaller: originalEditorCaller)
            .onAppear {
                withAnimation(.linear(duration: Constants.animationDuration)) {
                    showCircle = true
                }
            }
            .sheet(isPresented: $model.showSettings) {
                ServerConfigurationCoordinatorView(originalEditorCaller: originalEditorCaller)
            }
            .sheet(isPresented: $model.showDebugMenu) {
                DebugMenuView()
            }
            .navigationDestination(isPresented: $model.showLogin) {
                LoginCoordinatorView(originalEditorCaller: originalEditorCaller)
                    .onAppear {
                        withAnimation(.linear(duration: Constants.animationDuration)) {
                            showCircle = false
                        }
                    }
            }
            .navigationDestination(isPresented: $model.showJoinFlow) {
                if let state = model.joinState {
                    JoinCoordinatorView(state: state)
                        .onAppear {
                            withAnimation(.linear(duration: Constants.animationDuration)) {
                                showCircle = false
                            }
                        }
                }
            }
    }
}
