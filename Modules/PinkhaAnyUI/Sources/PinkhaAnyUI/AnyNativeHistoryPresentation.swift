import Foundation
import Observation
import PinkhaAnyEngine
import PinkhaAnyIntegration
import PinkhaAnyHost
import PinkhaKit

public enum AnyNativeHistoryProblem: Equatable, Sendable {
    case unavailable, versionNotFound, truncated, viewTooLarge
    case malformed, paginationLimit, paginationChanged, accessChanged, failed

    static func classify(_ error: any Error) -> Self {
        switch error {
        case AnyNativeHistoryError.unavailable: .unavailable
        case AnyNativeHistoryError.versionNotFound: .versionNotFound
        case AnyNativeHistoryError.truncated: .truncated
        case AnyNativeHistoryError.viewTooLarge, AnyEngineError.readLimit: .viewTooLarge
        case AnyNativeHistoryError.malformedResponse: .malformed
        case AnyNativeHistoryError.paginationLimit: .paginationLimit
        case AnyNativeHistoryError.paginationChanged: .paginationChanged
        case AnyNativeHistoryError.authorityUnavailable: .accessChanged
        case AnyHostError.sessionClosed, AnyHostError.engineRestarted, AnyHostError.wrongWorkspace,
             AnyEngineError.accountChanged, TorahAssociationRepositoryError.permissionDenied,
             TorahAssociationRepositoryError.targetNotFound, AnyNativeDocumentPolicyError.dependenciesChanged:
            .accessChanged
        case AnyEngineError.http(let status, let code) where status == 401 || status == 403 || code == "object.not_found": .accessChanged
        case AnyHostError.invalidDocument, AnyHostError.incompleteDocument: .malformed
        default: .failed
        }
    }
}

/// Independent read-only state; it never replaces the live editor snapshot.
/// The injected owner check is the existing mounted-document epoch/lifetime.
@MainActor @Observable
public final class AnyNativeHistoryPresentation: Identifiable {
    public let id = UUID()
    public private(set) var changes: [AnyNativeHistoryChange] = []
    public private(set) var selectedVersion: String?
    public private(set) var selected: AnyNativeHistoryVersion?
    public private(set) var isLoading = false
    public private(set) var isLoadingVersion = false
    public private(set) var isActive = true
    public private(set) var hasMore = false
    public private(set) var problem: AnyNativeHistoryProblem?
    public private(set) var versionProblem: AnyNativeHistoryProblem?
    @ObservationIgnored private let reader: any AnyNativeHistoryReading
    @ObservationIgnored private let session: AnyApplicationSession
    @ObservationIgnored private let checkOwner: @MainActor @Sendable () throws -> Void
    @ObservationIgnored private var epoch = UUID()
    @ObservationIgnored private var pageRequest: UUID?
    @ObservationIgnored private var versionRequest: UUID?
    @ObservationIgnored private var calls: [UUID: Task<Void, Never>] = [:]
    @ObservationIgnored private var pages: [AnyNativeHistoryPage] = []
    @ObservationIgnored private var cursor: AnyNativeHistoryCursor?
    @ObservationIgnored private var usedCursors: [AnyNativeHistoryCursor] = []

    public init(reader: any AnyNativeHistoryReading, session: AnyApplicationSession,
                checkOwner: @escaping @MainActor @Sendable () throws -> Void) throws {
        guard reader.workspace == session.workspace else { throw AnyHostError.wrongWorkspace }
        try checkOwner()
        self.reader = reader; self.session = session; self.checkOwner = checkOwner
    }

    public func refresh() async {
        guard isActive else { return }
        for task in calls.values { task.cancel() }
        epoch = UUID(); pageRequest = nil; versionRequest = nil
        changes = []; pages = []; cursor = nil; usedCursors = []
        selectedVersion = nil; selected = nil; hasMore = false
        isLoadingVersion = false; versionProblem = nil; problem = nil
        await loadPage(first: true)
    }

    public func loadMore() async {
        guard isActive, !isLoading, hasMore else { return }
        await loadPage(first: false)
    }

    private func loadPage(first: Bool) async {
        guard isActive, first || cursor != nil else { return }
        guard pages.count < 20, changes.count < 1000 else {
            hasMore = false; problem = .paginationLimit; return
        }
        let token = UUID(), owner = epoch, continuation = first ? nil : cursor
        pageRequest = token; isLoading = true; problem = nil
        let reader = reader, session = session, authorize = authorization(owner)
        let task = Task { [weak self] in
            guard let self else { return }
            defer {
                calls.removeValue(forKey: token)
                if pageRequest == token { pageRequest = nil; isLoading = false }
            }
            do {
                let value = try await session.perform { lease in
                    try await reader.page(after: continuation, lease: lease, authorize: authorize)
                }
                try requireCurrent(owner)
                guard pageRequest == token, !Task.isCancelled else { return }
                let previousIDs = Set(changes.map(\.version))
                guard previousIDs.isDisjoint(with: value.changes.map(\.version)),
                      changes.count + value.changes.count <= 1000 else {
                    throw AnyNativeHistoryError.paginationChanged
                }
                if let next = value.next, usedCursors.contains(next) {
                    throw AnyNativeHistoryError.paginationChanged
                }
                if let continuation { usedCursors.append(continuation) }
                pages.append(value); changes.append(contentsOf: value.changes)
                cursor = value.next; hasMore = value.next != nil
                if hasMore && (pages.count == 20 || changes.count == 1000) {
                    hasMore = false; problem = .paginationLimit
                }
            } catch {
                guard isActive, epoch == owner, pageRequest == token, !Task.isCancelled else { return }
                fail(error, preview: false)
            }
        }
        calls[token] = task
        await task.value
    }

    public func showVersion(_ id: String) async {
        guard isActive, let change = changes.first(where: { $0.version == id }) else { return }
        if let current = versionRequest { calls[current]?.cancel() }
        let token = UUID(), owner = epoch
        versionRequest = token; selectedVersion = id; selected = nil; versionProblem = nil
        if change.truncated {
            versionRequest = nil; isLoadingVersion = false; versionProblem = .truncated; return
        }
        isLoadingVersion = true
        let reader = reader, session = session, authorize = authorization(owner)
        let task = Task { [weak self] in
            guard let self else { return }
            defer {
                calls.removeValue(forKey: token)
                if versionRequest == token { versionRequest = nil; isLoadingVersion = false }
            }
            do {
                let value = try await session.perform { lease in
                    try await reader.version(id, lease: lease, authorize: authorize)
                }
                try requireCurrent(owner)
                guard versionRequest == token, selectedVersion == id, !Task.isCancelled else { return }
                selected = value
            } catch {
                guard isActive, epoch == owner, versionRequest == token, !Task.isCancelled else { return }
                fail(error, preview: true)
            }
        }
        calls[token] = task
        await task.value
    }

    public func closeVersion(_ id: String) {
        guard selectedVersion == id else { return }
        if let request = versionRequest { calls[request]?.cancel() }
        versionRequest = nil; selectedVersion = nil; selected = nil
        isLoadingVersion = false; versionProblem = nil
    }

    private func authorization(_ owner: UUID) -> @Sendable () async throws -> Void {
        { [weak self] in
            guard let self else { throw AnyHostError.sessionClosed }
            try await self.requireCurrent(owner)
        }
    }

    private func requireCurrent(_ owner: UUID) throws {
        try Task.checkCancellation()
        guard isActive, epoch == owner else { throw AnyHostError.sessionClosed }
        try checkOwner()
    }

    private func fail(_ error: any Error, preview: Bool) {
        let reason = AnyNativeHistoryProblem.classify(error)
        // No historical private data remains visible after current authority,
        // session or document ownership has been invalidated.
        if reason == .accessChanged {
            revoke(); problem = reason; versionProblem = reason
        } else if preview {
            selected = nil; versionProblem = reason
        } else {
            // A page failure must not leave an in-flight version request able
            // to publish into the now-cleared list, even if it ignores cancel.
            epoch = UUID()
            for task in calls.values { task.cancel() }
            pageRequest = nil; versionRequest = nil
            isLoading = false; isLoadingVersion = false; versionProblem = reason
            changes = []; pages = []; cursor = nil; usedCursors = []; hasMore = false
            selected = nil; selectedVersion = nil; problem = reason
        }
    }

    public func revoke() {
        isActive = false; epoch = UUID()
        for task in calls.values { task.cancel() }
        pageRequest = nil; versionRequest = nil
        changes = []; pages = []; cursor = nil; usedCursors = []
        selected = nil; selectedVersion = nil; hasMore = false
        isLoading = false; isLoadingVersion = false
        problem = .accessChanged; versionProblem = .accessChanged
    }

    public func drain() async {
        revoke()
        let pending = Array(calls.values)
        for task in pending { await task.value }
    }
}

#if canImport(SwiftUI)
extension AnyNativeHistoryPresentation {
    convenience init(document: AnyDocumentPresentation) throws {
        let owner = document.mountedOwnerID
        try document.requireMounted(owner)
        let reader = try AnyNativeHistoryReader(client: document.client, workspace: document.workspace,
            objectID: document.objectID, allowedTypeIDs: document.capabilities.allowedTargetTypes)
        try self.init(reader: reader, session: document.nativeSession, checkOwner: { [weak document] in
            guard let document else { throw AnyHostError.sessionClosed }
            try document.requireMounted(owner)
        })
        document.installPresentationLifecycle(revoke: { [weak self] in self?.revoke() },
                                               drain: { [weak self] in await self?.drain() })
    }
}
#endif
