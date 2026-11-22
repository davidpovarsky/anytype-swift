import SwiftUI

struct PublishToWebCoordinator: View {
    
    @StateObject private var model: PublishToWebCoordinatorModel
    
    init(data: PublishToWebViewData, preparedSession: PreparedEditorPageSession? = nil) {
        _model = StateObject(wrappedValue: PublishToWebCoordinatorModel(data: data, preparedSession: preparedSession))
    }
    
    var body: some View {
        PublishToWebView(data: model.data, output: model, preparedSession: model.preparedSession)
            .sheet(isPresented: $model.showMembership) {
                MembershipCoordinator()
            }
            .sheet(item: $model.sharedUrl) { url in
                ActivityView(activityItems: [url])
            }
            .safariSheet(url: $model.safariUrl)
    }
}