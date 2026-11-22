import Foundation
import SwiftUI

struct VersionHistoryCoordinatorView: View {

    @State private var model: VersionHistoryCoordinatorViewModel
    @Environment(\.dismiss) private var dismiss

    init(data: VersionHistoryData, output: (any ObjectVersionModuleOutput)?,
         preparedSession: PreparedEditorPageSession? = nil) {
        _model = State(initialValue: VersionHistoryCoordinatorViewModel(
            data: data, output: output, preparedSession: preparedSession
        ))
    }
    
    var body: some View {
        VersionHistoryView(
            data: model.data,
            output: model,
            preparedSession: model.preparedSession
        )
        .sheet(item: $model.objectVersionData) {
            ObjectVersionView(data: $0, output: model, preparedSession: model.preparedSession)
        }
    }
}
