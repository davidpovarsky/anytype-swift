import SwiftUI
import Services

enum SearchViewEmptyViewMode {
    case object
    case property
    
    func title(_ searchText: String) -> String {
        switch self {
        case .object:
            Loc.thereIsNoObjectNamed(searchText)
        case .property:
            Loc.thereIsNoPropertyNamed(searchText)
        }
    }
    
    var buttonTitle: String {
        switch self {
        case .object:
            Loc.newObject
        case .property:
            Loc.newProperty
        }
    }
}

struct SearchView<SearchData: SearchDataProtocol>: View {
    @Environment(\.dismiss) private var dismiss
    
    @State private var searchText = ""
    
    let title: String?
    let placeholder: String
    let searchData: [SearchDataSection<SearchData>]
    let emptyViewMode: SearchViewEmptyViewMode
    
    var dismissOnSelect = true
    
    var search: (_ text: String) async -> Void
    var onSelect: (_ searchData: SearchData) -> Void
    var onCreateNew: ((_ name: String) -> Void)?
    
    var body: some View {
        SearchViewShell(
            title: title,
            placeholder: placeholder,
            searchText: $searchText
        ) {
            content
        }
        .task(id: searchText) {
            // Debounce real typing: a new keystroke changes the id, cancelling this task so
            // the sleep throws and `search` is never called for intermediate terms. Skip the
            // delay for the initial/empty load so pickers populate immediately without a flash
            // of the empty state (and its malformed empty-query title).
            if searchText.isNotEmpty {
                guard (try? await Task.sleep(for: .milliseconds(300))) != nil else { return }
            }
            await search(searchText)
        }
    }
    
    private var content: some View {
        Group {
            if searchData.isEmpty {
                emptyState
            } else {
                searchResults
            }
        }
    }
    
    private var searchResults: some View {
        ScrollView {
            LazyVStack(spacing: 0) {
                ForEach(searchData) { section in
                    Section(content: {
                        ForEach(section.searchData) { searchData in
                            Button(
                                action: {
                                    if dismissOnSelect { dismiss() }
                                    onSelect(searchData)
                                }
                            ) {
                                SearchCell(data: searchData)
                            }
                        }
                    }, header: {
                        if section.sectionName.isNotEmpty {
                            VStack(alignment: .leading, spacing: 0) {
                                Spacer()
                                AnytypeText(section.sectionName, style: .caption1Regular)
                                    .foregroundStyle(Color.Text.secondary)
                                    .divider(spacing: 7, leadingPadding: 0, trailingPadding: 0, alignment: .leading)
                            }
                            .padding(.horizontal, 20)
                            .frame(height: 52)
                        } else {
                            EmptyView()
                        }
                    })
                }
            }
        }
    }
    
    private var emptyState: some View {
        if let onCreateNew {
            EmptyStateView(
                title: emptyViewMode.title(searchText),
                subtitle: "",
                style: .plain,
                buttonData: EmptyStateView.ButtonData(
                    title: emptyViewMode.buttonTitle,
                    action: { onCreateNew(searchText) }
                )
            )
        } else {
            EmptyStateView(
                title: emptyViewMode.title(searchText),
                subtitle: Loc.createANewOneOrSearchForSomethingElse,
                style: .plain
            )
        }
    }
}

/// The native search-sheet chrome shared by Link To and feature-specific searches.
/// Keeping the drag indicator, title, focused search field and background here prevents
/// feature sheets from drifting away from the host presentation recipe.
struct SearchViewShell<Content: View>: View {
    let title: String?
    let placeholder: String
    @Binding var searchText: String
    private let searchFieldAccessibilityIdentifier: String?
    private let content: Content

    init(
        title: String?,
        placeholder: String,
        searchText: Binding<String>,
        searchFieldAccessibilityIdentifier: String? = nil,
        @ViewBuilder content: () -> Content
    ) {
        self.title = title
        self.placeholder = placeholder
        self._searchText = searchText
        self.searchFieldAccessibilityIdentifier = searchFieldAccessibilityIdentifier
        self.content = content()
    }

    var body: some View {
        VStack(spacing: 0) {
            DragIndicator()
            TitleView(title: title)
            searchBar
            content
        }
        .background(Color.Background.secondary)
    }

    @ViewBuilder
    private var searchBar: some View {
        if let searchFieldAccessibilityIdentifier {
            SearchBar(text: $searchText, focused: true, placeholder: placeholder)
                .accessibilityIdentifier(searchFieldAccessibilityIdentifier)
        } else {
            SearchBar(text: $searchText, focused: true, placeholder: placeholder)
        }
    }
}
