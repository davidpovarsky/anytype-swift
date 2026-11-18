import Foundation
@preconcurrency import Combine
import CryptoKit
import Observation
import UIKit
import Services
import Factory
import HanlinHostContracts

/// Real Anytype authority, scoped to the presenting scene/route/editor, never to a model-supplied target.
@MainActor
final class PinkhaHanlinNativeAccess: PinkhaHanlinHostAccess {
    let session: HanlinHostSession
    private weak var presenter: UIViewController?
    private weak var promptOwner: PinkhaHanlinChatController?
    private weak var scene: UIWindowScene?
    private weak var routeOwner: SpaceHubCoordinatorViewModel?
    private weak var sourceEditor: EditorPageController?
    private weak var document: (any BaseDocumentProtocol)?
    private weak var selection: (any EditorPageBlocksStateManagerProtocol)?
    private let fence = PinkhaHanlinRevocationFence()
    private let navigationScopeFence = PinkhaHanlinRevocationFence()
    private let readConsent = PinkhaHanlinReadConsent()
    private let objectWasBound: Bool
    private let initialSource: Data?
    private var subscriptions: [AnyCancellable] = []
    private let navigation: PinkhaHanlinNavigationLedger
    private var returnHandoff: PinkhaHanlinNavigationHandoff?
    private var onInvalidation: (@MainActor () -> Void)?

    private let accounts = Container.shared.accountManager()
    private let users = Container.shared.basicUserInfoStorage()
    private let application = Container.shared.applicationStateService()
    private let spaces = Container.shared.participantSpacesStorage()
    private let activeSpace = Container.shared.activeSpaceManager()
    private let lifecycle = Container.shared.objectLifecycleService()

    init(presenter: UIViewController, routeOwner: SpaceHubCoordinatorViewModel,
         conversationID: UUID, locale: Locale) throws {
        guard let scene = presenter.viewIfLoaded?.window?.windowScene,
              let spaceID = routeOwner.currentSpaceId, !spaceID.isEmpty else { throw HanlinHostError.invalidContext }
        let accountID = Container.shared.accountManager().account.id
        // Context is derived from the actual presenting editor's live ownership, never supplied beside it.
        let editor = presenter as? EditorPageController
        let document = editor?.viewModel?.document
        let selection = editor?.viewModel?.blocksStateManager
        guard editor == nil || document != nil else { throw HanlinHostError.invalidContext }
        let selected = Self.selectedIDs(selection)
        guard document != nil || selected.isEmpty else { throw HanlinHostError.invalidContext }
        let snapshot = try document.map { try Self.project(document: $0, selection: selected) }
        self.presenter = presenter
        self.scene = scene
        self.routeOwner = routeOwner
        self.sourceEditor = editor
        self.document = document
        self.selection = selection
        self.objectWasBound = document != nil
        self.initialSource = try document.map { try Self.sourceFence(document: $0, selection: selected) }
        let session = HanlinHostSession(conversationID: conversationID, context: .init(
            namespace: try .init(app: "anytype", account: accountID, workspace: spaceID, space: spaceID),
            sceneID: UUID(), generation: UUID(), objectReference: document?.objectId,
            selectionReferences: selected, sourceRevision: snapshot?.sourceRevision, localeIdentifier: locale.identifier))
        self.session = session
        self.navigation = PinkhaHanlinNavigationLedger(context: session.context)
        fence.onRevoke { [weak self] in
            Task { @MainActor in
                self?.readConsent.revoke()
                self?.onInvalidation?()
            }
        }
        navigationScopeFence.onRevoke { [weak self] in
            Task { @MainActor in self?.returnHandoff?.cancel() }
        }
        try validate(session.context)
        editor?.pinkhaHanlinPresentationID = session.id
        installInvalidation(document: document, selection: selection, routeOwner: routeOwner, scene: scene)
    }

    func invalidate() { fence.revoke(); readConsent.revoke() }

    func observeInvalidation(_ callback: @escaping @MainActor () -> Void) {
        onInvalidation = callback
        if fence.isRevoked { callback() }
    }

    func installPromptOwner(_ controller: PinkhaHanlinChatController) throws {
        try validate(session.context)
        guard controller.presentation.session == session,
              controller.viewIfLoaded?.window?.windowScene === scene else { throw HanlinHostError.staleContext }
        promptOwner = controller
    }

    func requestContextReadConsent() async throws {
        try validate(session.context)
        guard objectWasBound, let presenter = promptOwner else { throw HanlinHostError.denied }
        try await readConsent.request(from: presenter, locale: Locale(identifier: session.context.localeIdentifier)) { [weak self] in
            guard let self else { throw HanlinHostError.staleContext }
            try self.validate(self.session.context)
        }
        try validate(session.context)
    }

    func validateRead(_ context: HanlinHostContext) throws {
        try validate(context)
        guard objectWasBound, readConsent.authorized else { throw HanlinHostError.denied }
    }

    func validate(_ context: HanlinHostContext) throws {
        guard !fence.isRevoked else { throw HanlinHostError.staleContext }
        try validateNativeOwner(context)
    }

    /// Native ownership only. The sole post-close caller records a previously authorized UI receipt.
    /// All SDK context/read/write entry points still require the presentation fence above.
    private func validateNativeOwner(_ context: HanlinHostContext) throws {
        guard context == session.context,
              PinkhaHanlinAccountOwner.shared.isAvailable(account: context.namespace.account),
              let presenter, let scene, let routeOwner,
              presenter.viewIfLoaded?.window?.windowScene === scene,
              scene.activationState == .foregroundActive, !presenter.isBeingDismissed,
              case .home = application.state,
              accounts.account.status == .active,
              Self.exact(accounts.account.id, context.namespace.account),
              Self.exact(users.usersId, context.namespace.account),
              routeOwner.currentSpaceId.map({ Self.exact($0, context.namespace.space) }) == true,
              activeSpace.workspaceInfo.map({ Self.exact($0.accountSpaceId, context.namespace.space) }) == true,
              Self.exact(context.namespace.workspace, context.namespace.space),
              let member = spaces.participantSpaceView(spaceId: context.namespace.space),
              Self.exact(member.spaceView.targetSpaceId, context.namespace.space),
              Self.isAuthorized(member, accountID: context.namespace.account) else { throw HanlinHostError.staleContext }
        if objectWasBound {
            guard let sourceEditor, sourceEditor === presenter,
                  let model = sourceEditor.viewModel, let document, let selection,
                  model.document === document, model.blocksStateManager === selection,
                  document.isOpened, document.mode.isHandling,
                  Self.exact(document.objectId, context.objectReference ?? ""),
                  Self.exact(document.spaceId, context.namespace.space),
                  Self.selectedIDs(selection).map({ Data($0.utf8) }) == context.selectionReferences.map({ Data($0.utf8) }),
                  try Self.sourceFence(document: document, selection: context.selectionReferences) == initialSource else {
                throw HanlinHostError.staleContext
            }
        } else {
            guard context.objectReference == nil, context.selectionReferences.isEmpty else { throw HanlinHostError.invalidContext }
        }
    }

    func read(_ context: HanlinHostContext) async throws -> PinkhaHanlinTextSnapshot {
        try validateRead(context)
        try Task.checkCancellation()
        guard let object = context.objectReference else { throw HanlinHostError.unknownTool }
        // Final checks and the real existing service dispatch share this MainActor segment.
        let view = try await lifecycle.openForPreview(contextId: object, spaceId: context.namespace.space)
        try Task.checkCancellation()
        try validateRead(context)
        guard Self.exact(view.rootID, object), view.blocks.count <= 512,
              let row = view.details.first(where: { Self.exact($0.id, object) }) else { throw HanlinHostError.resultMismatch }
        let details = ObjectDetails(id: row.id, values: row.details.fields)
        let blocks = view.blocks.compactMap { BlockInformationConverter.convert(block: $0) }
        guard blocks.count == view.blocks.count else { throw HanlinHostError.invalidRecord }
        let snapshot = try Self.project(details: details, root: object, space: context.namespace.space,
                                        blocks: blocks, selection: context.selectionReferences)
        guard context.matchesRevision(snapshot.sourceRevision) else { throw HanlinHostError.staleContext }
        try validateRead(context)
        return snapshot
    }

    func navigate(_ destination: HanlinHostDestination) throws -> HanlinHostNavigationResult {
        try validate(destination.context)
        guard let object = session.context.objectReference, Self.exact(destination.objectReference, object),
              let document, sourceEditor != nil else { throw HanlinHostError.denied }
        if let block = destination.blockReference {
            guard !block.isEmpty, try Self.reachableBlocks(document).contains(where: { Self.exact($0.id, block) }) else {
                throw HanlinHostError.resultMismatch
            }
        }
        // The original editor already owns this document. A hidden route push cannot acknowledge
        // it. The native Return action consumes this queue only after open() has returned.
        _ = try navigation.enqueue(destination)
        return try navigation.result(for: destination)
    }

    func makeReturnHandoff(_ destination: HanlinHostDestination,
                           controller: PinkhaHanlinChatController) throws -> PinkhaHanlinNavigationHandoff {
        try validate(destination.context)
        try controller.presentation.validateInstallation(for: session)
        guard !navigationScopeFence.isRevoked, returnHandoff == nil,
              promptOwner === controller, controller.presentedViewController == nil,
              let editor = sourceEditor, editor.pinkhaHanlinPresentationID == session.id else {
            throw HanlinHostError.staleContext
        }
        let handoff = try navigation.makeHandoff(for: destination) { [self, weak editor] in
            guard !navigationScopeFence.isRevoked, let editor, editor === sourceEditor,
                  editor.pinkhaHanlinPresentationID == session.id else { throw HanlinHostError.staleContext }
            try validateNativeOwner(destination.context)
            editor.viewIfLoaded?.layoutIfNeeded()
            editor.collectionView.layoutIfNeeded()
            if let block = destination.blockReference { editor.revealBlock(blockId: block) }
            guard !navigationScopeFence.isRevoked, editor.pinkhaHanlinPresentationID == session.id else {
                throw HanlinHostError.staleContext
            }
            try validateNativeOwner(destination.context)
            return try mountedTargetResult(destination, controller: editor)
        }
        returnHandoff = handoff
        return handoff
    }

    /// Only the actual target UI owner can call this after exact-target mount, not from queue completion.
    func acknowledgeMounted(_ destination: HanlinHostDestination,
                            controller: EditorPageController) throws -> HanlinHostNavigationResult {
        try validate(destination.context)
        let result = try mountedTargetResult(destination, controller: controller)
        try navigation.acknowledge(result, for: destination)
        return result
    }

    private func mountedTargetResult(_ destination: HanlinHostDestination,
                                     controller: EditorPageController) throws -> HanlinHostNavigationResult {
        _ = try navigation.result(for: destination)
        guard let scene, let model = controller.viewModel,
              Self.isMounted(controller, in: scene) else { throw HanlinHostError.resultMismatch }
        let target = model.document
        guard
              target.isOpened, target.mode.isHandling,
              Self.exact(target.objectId, destination.objectReference),
              Self.exact(target.spaceId, destination.context.namespace.space) else {
            throw HanlinHostError.resultMismatch
        }
        if let block = destination.blockReference {
            let collection = controller.collectionView
            guard try Self.reachableBlocks(target).contains(where: { Self.exact($0.id, block) }),
                  let item = controller.dataSource.snapshot().itemIdentifiers.first(where: {
                      guard case .block(let mounted) = $0 else { return false }
                      return Self.exact(mounted.info.id, block)
                  }),
                  case .block(let mountedBlock) = item, Self.exact(mountedBlock.info.id, block),
                  let index = controller.dataSource.indexPath(for: item),
                  collection.indexPathsForVisibleItems.contains(index),
                  let cell = collection.cellForItem(at: index),
                  Self.isMounted(collection, in: scene), Self.isMounted(cell, in: scene),
                  cell.convert(cell.bounds, to: collection).intersects(collection.bounds) else {
                throw HanlinHostError.resultMismatch
            }
        }
        let result = HanlinHostNavigationResult.presented(requestID: destination.requestID, context: destination.context,
            objectReference: destination.objectReference, blockReference: destination.blockReference)
        try result.validate(for: destination)
        return result
    }

    static func isMounted(_ controller: UIViewController, in scene: UIWindowScene) -> Bool {
        guard let view = controller.viewIfLoaded, isMounted(view, in: scene) else { return false }
        var child = controller
        while true {
            guard !child.isBeingDismissed, !child.isMovingFromParent,
                  child.presentedViewController == nil else { return false }
            guard let parent = child.parent else { return true }
            if let navigation = parent as? UINavigationController, navigation.visibleViewController !== child { return false }
            if let tabs = parent as? UITabBarController, tabs.selectedViewController !== child { return false }
            child = parent
        }
    }

    private static func isMounted(_ view: UIView, in scene: UIWindowScene) -> Bool {
        guard let window = view.window, window.windowScene === scene,
              !window.isHidden, window.alpha > 0, !view.bounds.isEmpty,
              view.convert(view.bounds, to: window).intersects(window.bounds) else { return false }
        var ancestor: UIView? = view
        while let current = ancestor {
            guard !current.isHidden, current.alpha > 0 else { return false }
            ancestor = current.superview
        }
        return true
    }

    private func installInvalidation(document: (any BaseDocumentProtocol)?,
                                     selection: (any EditorPageBlocksStateManagerProtocol)?,
                                     routeOwner: SpaceHubCoordinatorViewModel, scene: UIWindowScene) {
        let fence = fence
        let navigationScopeFence = navigationScopeFence
        let revoke: @Sendable () -> Void = { fence.revoke(); navigationScopeFence.revoke() }
        let context = session.context
        accounts.accountPublisher.sink { account in
            if !Self.exact(account.id, context.namespace.account) || account.status != .active { revoke() }
        }.store(in: &subscriptions)
        application.statePublisher.sink { state in
            if case .home = state {} else { revoke() }
        }.store(in: &subscriptions)
        let initialMember = spaces.participantSpaceView(spaceId: context.namespace.space)
        spaces.allParticipantSpacesPublisher.sink { members in
            let member = members.first { Self.exact($0.spaceView.targetSpaceId, context.namespace.space) }
            if member != initialMember { revoke() }
        }.store(in: &subscriptions)
        withObservationTracking {
            _ = routeOwner.currentSpaceId
        } onChange: { revoke() } // One-way fence; no rearming/poll loop.
        NotificationCenter.default.publisher(for: UIScene.didEnterBackgroundNotification, object: scene)
            .sink { _ in revoke() }.store(in: &subscriptions)
        NotificationCenter.default.publisher(for: UIScene.willDeactivateNotification, object: scene)
            .sink { _ in navigationScopeFence.revoke() }.store(in: &subscriptions)
        if let document {
            let initial = initialSource
            document.syncPublisher.sink { [weak document] _ in
                guard let document, (try? Self.sourceFence(document: document, selection: context.selectionReferences)) == initial else {
                    revoke(); return
                }
            }.store(in: &subscriptions)
        }
        if let selection {
            Self.observeSelection(selection.editorEditingStatePublisher,
                expected: context.selectionReferences, revoke: revoke).store(in: &subscriptions)
        }
    }

    /// Observe every emitted mode, including Done/editing between equal block IDs.
    /// @Published emits before the property changes: reading the manager again here
    /// could miss that transition. Keep delivery synchronous and both fences final.
    static func observeSelection(_ states: AnyPublisher<EditorEditingState, Never>,
                                 expected: [String], revoke: @escaping @Sendable () -> Void) -> AnyCancellable {
        let identity = expected.map { Data($0.utf8) }
        return states.sink { state in
            if Self.selectedIDs(in: state).map({ Data($0.utf8) }) != identity { revoke() }
        }
    }

    nonisolated private static func exact(_ left: String, _ right: String) -> Bool {
        left.utf8.elementsEqual(right.utf8)
    }

    nonisolated private static func isAuthorized(_ member: ParticipantSpaceViewData, accountID: String) -> Bool {
        guard member.spaceView.isActive, let participant = member.participant,
              participant.status == .active, exact(participant.identity, accountID),
              exact(participant.spaceId, member.spaceView.targetSpaceId) else { return false }
        switch participant.permission {
        case .owner, .admin, .writer, .reader: return true
        default: return false
        }
    }

    private static func selectedIDs(_ selection: (any EditorPageBlocksStateManagerProtocol)?) -> [String] {
        guard let selection else { return [] }
        return selectedIDs(in: selection.editingState)
    }

    nonisolated private static func selectedIDs(in state: EditorEditingState) -> [String] {
        switch state {
        case .selecting(let blocks, _): return blocks
        case .simpleTablesSelection(_, let selected, _): return selected
        default: return []
        }
    }

    nonisolated private static func sourceFence(document: any BaseDocumentProtocol, selection: [String]) throws -> Data {
        let snapshot = try project(document: document, selection: selection)
        let permissions = document.permissions
        return Data((snapshot.sourceRevision + "|\(document.isOpened)|\(document.isLocked)|\(document.mode.isHandling)"
            + "|\(permissions.canEditBlocks)|\(permissions.canEditDetails)|\(permissions.canEditRelationValues)").utf8)
    }

    nonisolated private static func project(document: any BaseDocumentProtocol, selection: [String]) throws -> PinkhaHanlinTextSnapshot {
        guard document.isOpened, document.mode.isHandling, let details = document.details else { throw HanlinHostError.denied }
        return try project(details: details, root: document.objectId, space: document.spaceId,
                           blocks: reachableBlocks(document), selection: selection)
    }

    nonisolated private static func reachableBlocks(_ document: any BaseDocumentProtocol) throws -> [BlockInformation] {
        var pending = [document.objectId]
        var seen = Set<Data>()
        var result: [BlockInformation] = []
        while let id = pending.popLast() {
            guard result.count < 512, seen.insert(Data(id.utf8)).inserted,
                  let block = document.infoContainer.get(id: id), block.childrenIds.count <= 512 else {
                throw HanlinHostError.invalidRecord
            }
            result.append(block)
            pending.append(contentsOf: block.childrenIds.reversed())
        }
        return result
    }

    nonisolated private static func project(details: ObjectDetails, root: String, space: String,
                                           blocks: [BlockInformation], selection: [String]) throws -> PinkhaHanlinTextSnapshot {
        guard exact(details.id, root), exact(details.spaceId, space), !details.isDeleted, !details.isArchived,
              !details.isHidden, !details.isTemplate, details.resolvedLayoutValue.isEditorLayout,
              details.name.utf8.count <= 512, blocks.count <= 512, selection.count <= 64,
              Set(selection.map { Data($0.utf8) }).count == selection.count else { throw HanlinHostError.denied }
        var index: [Data: BlockInformation] = [:]
        for block in blocks {
            guard !block.id.isEmpty, block.id.utf8.count <= 256,
                  index.updateValue(block, forKey: Data(block.id.utf8)) == nil else { throw HanlinHostError.invalidRecord }
        }
        var stack = [root]
        var reached = Set<Data>()
        var text: [PinkhaHanlinTextSnapshot.Block] = []
        let selected = Set(selection.map { Data($0.utf8) })
        var selectedText = Set<Data>()
        var bytes = 0
        while let id = stack.popLast() {
            let key = Data(id.utf8)
            guard reached.insert(key).inserted, let block = index[key], block.childrenIds.count <= 512 else {
                throw HanlinHostError.invalidRecord
            }
            stack.append(contentsOf: block.childrenIds.reversed())
            if !exact(id, root), selected.isEmpty || selected.contains(key), case .text(let content) = block.content {
                bytes += content.text.utf8.count
                guard text.count < 128, bytes <= 24_576 else { throw HanlinHostError.outputLimitExceeded }
                text.append(.init(reference: id, text: content.text))
                selectedText.insert(key)
            }
        }
        guard selected.isEmpty || selected.isSubset(of: selectedText) else { throw HanlinHostError.denied }
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        let basis = PinkhaHanlinTextSnapshot(objectReference: root, spaceReference: space, sourceRevision: "",
            title: details.name, blocks: text, coverage: selected.isEmpty ? "documentTextBlocksOnly" : "selectedTextBlocksOnly")
        let revision = SHA256.hash(data: try encoder.encode(basis)).map { String(format: "%02x", $0) }.joined()
        return .init(objectReference: root, spaceReference: space, sourceRevision: revision,
                     title: details.name, blocks: text, coverage: basis.coverage)
    }
}
