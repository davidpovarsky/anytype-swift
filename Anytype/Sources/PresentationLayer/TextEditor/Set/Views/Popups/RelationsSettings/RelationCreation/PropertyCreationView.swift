import SwiftUI

struct PropertyCreationView: View {
    @State private var model: PropertyCreationViewModel
    @Environment(\.dismiss) private var dismiss

    init(data: PropertiesSearchData) {
        _model = State(initialValue: PropertyCreationViewModel(data: data))
    }
    
    var body: some View {
        content
            .safeAreaInset(edge: .bottom) {
                if model.nativeLookupFailed {
                    VStack {
                        AnytypeText(Loc.Content.Common.error, style: .uxBodyRegular)
                        Button(Loc.Pinkha.Home.retry) { Task { await model.retryNativeLookup() } }
                    }
                    .padding()
                    .background(Color.Background.primary)
                }
            }
            .onAppear { model.dismiss = dismiss }
            .sheet(item: $model.newPropertyData) {
                PropertyInfoCoordinatorView(data: $0, output: model)
                    .mediumPresentationDetents()
            }
    }
    
    private var content: some View {
        SearchView(
            title: Loc.addProperty,
            placeholder: Loc.searchOrCreateNew,
            searchData: model.rows,
            emptyViewMode: .property,
            dismissOnSelect: false
        ) { searchText in
            await model.search(text: searchText)
        } onSelect: { selectedItem in
            model.onRowTap(selectedItem)
        } onCreateNew: { name in
            model.onNewPropertyTap(name: name)
        }
    }

}
