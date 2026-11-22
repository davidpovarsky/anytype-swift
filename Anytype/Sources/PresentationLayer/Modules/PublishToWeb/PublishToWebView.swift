import SwiftUI
import AnytypeCore


struct PublishToWebView: View {

    @State private var model: PublishToWebViewModel
    private weak var output: (any PublishToWebModuleOutput)?

    init(data: PublishToWebViewData, output: (any PublishToWebModuleOutput)?,
         preparedSession: PreparedEditorPageSession? = nil) {
        _model = State(initialValue: PublishToWebViewModel(data: data, preparedSession: preparedSession))
        self.output = output
    }
    
    var body: some View {
        Group {
            switch model.state {
            case .initial:
                EmptyView()
            case .error(let error):
                ErrorStateView(message: error)
            case .loaded(let data):
                PublishToWebInternalView(data: data, output: output, preparedSession: model.preparedSession)
            }
        }
        .task { await model.onAppear() }
        .animation(.default, value: model.state)
    }
}

#Preview {
    PublishToWebView(data: PublishToWebViewData(objectId: "", spaceId: ""), output: nil)
}
