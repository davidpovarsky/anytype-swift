import SwiftUI

struct PropertyCreationView: View {
    @State private var model: PropertyCreationViewModel
    @Environment(\.dismiss) private var dismiss
    @Environment(\.locale) private var locale

    init(data: PropertiesSearchData) {
        _model = State(initialValue: PropertyCreationViewModel(data: data))
    }
    
    var body: some View {
        content
            .safeAreaInset(edge: .bottom) {
                if model.hasLookupFailure || model.propertySelection.failed {
                    VStack {
                        if model.nativeLookupFailed {
                            AnytypeText(Loc.Pinkha.Torah.nativePropertiesUnavailable(locale: locale), style: .uxBodyRegular)
                                .accessibilityIdentifier("torah-property-native-lookup-error")
                        }
                        if model.existingLookupFailed {
                            AnytypeText(Loc.Pinkha.Torah.existingPropertiesUnavailable(locale: locale), style: .uxBodyRegular)
                                .accessibilityIdentifier("torah-property-existing-lookup-error")
                        }
                        if model.propertySelection.failed {
                            AnytypeText(Loc.Pinkha.Torah.propertyCouldNotBeAdded(locale: locale), style: .uxBodyRegular)
                                .accessibilityIdentifier("torah-property-add-error")
                            Button(Loc.Pinkha.Home.retry) { Task { await model.retryPropertySelection() } }
                                .accessibilityIdentifier("torah-property-add-retry")
                        }
                        if model.hasLookupFailure {
                            Button(Loc.Pinkha.Home.retry) { Task { await model.retryNativeLookup() } }
                                .accessibilityIdentifier("torah-property-lookup-retry")
                        }
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
            dismissOnSelect: false,
            showsEmptyState: !model.isSearching && !model.hasLookupFailure
        ) { searchText in
            await model.search(text: searchText)
        } onSelect: { selectedItem in
            Task { await model.onRowTap(selectedItem) }
        } onCreateNew: { name in
            model.onNewPropertyTap(name: name)
        }
        .disabled(model.propertySelection.isRunning)
    }

}
