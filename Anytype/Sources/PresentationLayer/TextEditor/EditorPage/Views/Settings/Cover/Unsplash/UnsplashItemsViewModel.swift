import Foundation
import Combine
import Services

@MainActor
final class UnsplashViewModel: GridItemViewModelProtocol {
    typealias Item = UnsplashItemViewModel
    typealias Section = GridItemSection<Item>

    let searchAvailability: SearchAvailability = .available(placeholder: Loc.search)
    let onItemSelect: (UnsplashItem) -> ()

    @Published var sections = [Section]()

    private var unsplashItems = [UnsplashItem]() {
        didSet {
            sections = backgroundSections()
        }
    }
    @Injected(\.unsplashService)
    private var unsplashService: any UnsplashServiceProtocol
    private let documentWriteOwner: EditorDocumentWriteOwner?
    private(set) var isLoading: Bool = true
    private var searchTextChangedSubscription: AnyCancellable?

    @Published private var searchValue: String = ""

    init(
        onItemSelect: @escaping (UnsplashItem) -> (),
        documentWriteOwner: EditorDocumentWriteOwner? = nil
    ) {
        self.onItemSelect = onItemSelect
        self.documentWriteOwner = documentWriteOwner
        self.unsplashService = unsplashService

        searchImages(query: "")

        searchTextChangedSubscription = $searchValue
            .debounce(for: .seconds(0.5), scheduler: RunLoop.main)
            .sink { [weak self] value in
                self?.searchImages(query: value)
            }
    }

    func didSelectItem(item: UnsplashItemViewModel) {
        performCurrentPresentation { onItemSelect(item.item) }
    }

    func didChangeSearchQuery(query: String) {
        performCurrentPresentation { searchValue = query }
    }

    private func searchImages(query: String) {
        performCurrentPresentation { isLoading = true }

        Task { @MainActor [weak self] in
            let items = try? await self?.searchService.searchUnsplashImages(query: query)
            self?.performCurrentPresentation {
                self?.isLoading = false
                if let items {
                    self?.unsplashItems = items
                }
            }
        }
    }

    private var searchService: any UnsplashServiceProtocol {
        guard let documentWriteOwner else { return unsplashService }
        return DocumentOwnedUnsplashService(owner: documentWriteOwner, service: unsplashService)
    }

    private func performCurrentPresentation(_ operation: () -> Void) {
        if let documentWriteOwner {
            try? documentWriteOwner.performSynchronousOperation(requiresEditing: false, operation: operation)
        } else {
            operation()
        }
    }

    private func backgroundSections() -> [Section] {
        let items = unsplashItems.map(UnsplashItemViewModel.init(item:))

        return [Section(title: nil, items: items)]
    }
}
