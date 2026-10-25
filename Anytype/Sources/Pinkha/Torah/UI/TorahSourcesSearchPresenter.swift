import Foundation
import Observation
import PinkhaKit
import TorahInspectorCore

@MainActor
@Observable
final class TorahSourcesSearchPresenter {
    typealias SearchScope = TorahEditorSession.SearchScope
    typealias SearchResult = TorahEditorSession.SearchResult
    typealias SearchState = TorahEditorSession.SearchState

    let context: TorahAssociationContext
    var searchScope: SearchScope
    var searchQuery: String
    private(set) var searchState: SearchState
    private(set) var associations: [TorahAssociationItem]
    private(set) var persistenceState: TorahAssociationPersistenceState?
    var resultListScrollAnchor: String?

    private let session: TorahEditorSession
    private let onOpenSelection: (TorahInspectorSelection) -> Void
    private var searchEpoch: UInt = 0
    private var associationRequestID: UUID?
    private var openRequestID: UUID?
    private var mutationRequestID: UUID?

    init(
        session: TorahEditorSession,
        context: TorahAssociationContext,
        searchScope: SearchScope = .references,
        searchQuery: String = "",
        searchState: SearchState = .idle,
        associations: [TorahAssociationItem]? = nil,
        persistenceState: TorahAssociationPersistenceState? = nil,
        onOpenSelection: @escaping (TorahInspectorSelection) -> Void
    ) {
        self.session = session
        self.context = context
        self.searchScope = searchScope
        self.searchQuery = searchQuery
        self.searchState = searchState
        self.associations = associations ?? session.cachedAssociations(for: context)
        self.persistenceState = persistenceState
        self.onOpenSelection = onOpenSelection
    }

    var associationTargetBlockID: String? { context.blockId }

    func performSearch(debounce: Duration = .zero) async {
        searchEpoch &+= 1
        let requestEpoch = searchEpoch
        let query = searchQuery.trimmingCharacters(in: .whitespacesAndNewlines)
        let scope = searchScope
        guard query.count >= 2 else {
            searchState = .idle
            return
        }

        searchState = .loading
        do {
            if debounce > .zero {
                try await Task.sleep(for: debounce)
            }
            try Task.checkCancellation()
            let results = try await session.search(query: query, scope: scope)
            try Task.checkCancellation()
            guard isCurrentSearch(requestEpoch, query: query, scope: scope) else { return }
            searchState = results.isEmpty ? .empty : .results(results)
        } catch is CancellationError {
            guard isCurrentSearch(requestEpoch, query: query, scope: scope) else { return }
            searchState = .idle
        } catch TorahError.noResults {
            guard isCurrentSearch(requestEpoch, query: query, scope: scope) else { return }
            searchState = .empty
        } catch {
            guard isCurrentSearch(requestEpoch, query: query, scope: scope) else { return }
            searchState = .error(session.searchMessage(for: error))
        }
    }

    func refreshAssociations() async {
        let requestID = UUID()
        associationRequestID = requestID
        do {
            let values = try await session.associationSnapshot(for: context)
            guard associationRequestID == requestID else { return }
            associations = values
        } catch is CancellationError {
        } catch {
            guard associationRequestID == requestID else { return }
            session.reportSearchError(error)
        }
    }

    func openReference(_ result: SearchResult) async {
        guard result.scope == .references else { return }
        let requestID = UUID()
        openRequestID = requestID
        let query = searchQuery
        let scope = searchScope
        do {
            let selection = try await session.resolveReference(result)
            try session.validateSearchContext(context)
            guard openRequestID == requestID,
                  searchQuery == query,
                  searchScope == scope else { return }
            onOpenSelection(selection)
        } catch is CancellationError {
        } catch {
            guard openRequestID == requestID else { return }
            session.reportSearchError(error)
        }
    }

    func openAssociation(_ item: TorahAssociationItem) {
        guard session.canOpenAssociation(item) else { return }
        do {
            try session.validateSearchContext(context)
            onOpenSelection(TorahEditorSession.inspectorSelection(for: item))
        } catch {
            session.reportSearchError(error)
        }
    }

    func canOpenAssociation(_ item: TorahAssociationItem) -> Bool {
        session.canOpenAssociation(item)
    }

    func link(_ result: SearchResult) async {
        let requestID = UUID()
        mutationRequestID = requestID
        let rawQuery = searchQuery
        persistenceState = .waiting
        do {
            persistenceState = .saving
            let values = try await session.link(result, to: context, rawQuery: rawQuery)
            guard mutationRequestID == requestID else { return }
            associations = values
            persistenceState = .saved
        } catch is CancellationError {
        } catch {
            guard mutationRequestID == requestID else { return }
            persistenceState = session.persistenceState ?? .error(error.localizedDescription)
        }
    }

    func unlinkAssociation(_ item: TorahAssociationItem) async {
        let requestID = UUID()
        mutationRequestID = requestID
        persistenceState = .waiting
        do {
            persistenceState = .saving
            let values = try await session.unlinkAssociation(item, from: context)
            guard mutationRequestID == requestID else { return }
            associations = values
            persistenceState = .saved
        } catch is CancellationError {
        } catch {
            guard mutationRequestID == requestID else { return }
            persistenceState = session.persistenceState ?? .error(error.localizedDescription)
        }
    }

    func cancelPendingRequests() {
        searchEpoch &+= 1
        associationRequestID = nil
        openRequestID = nil
        mutationRequestID = nil
    }

    private func isCurrentSearch(
        _ requestEpoch: UInt,
        query: String,
        scope: SearchScope
    ) -> Bool {
        searchEpoch == requestEpoch
            && searchQuery.trimmingCharacters(in: .whitespacesAndNewlines) == query
            && searchScope == scope
    }
}
