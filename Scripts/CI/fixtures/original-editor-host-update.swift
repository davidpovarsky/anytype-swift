import Foundation

@MainActor
private struct HostUpdatePreparedFixture {
    let document: LifetimeDocumentProbe
    let destination: TextProbe
    let session: PreparedEditorPageSession
    let state: EditorPageViewState
    let container: FixturePreparedContainer
    let coordinator: FixturePreparedContainer.Coordinator?

    init(document: LifetimeDocumentProbe = LifetimeDocumentProbe(), attach: Bool = true) throws {
        let destination = TextProbe()
        let prepared = try PreparedEditorPageSession(
            data: lifetimeData(document), document: document, textService: destination,
            services: fixtureServices(events: LocalPublisherProbe())
        )
        let state = try FixturePreparedAssembly().buildStateModel(
            preparedSession: prepared, output: nil, showHeader: true, torahSession: nil
        )
        let container = FixturePreparedContainer(
            viewController: state.viewController, preparedSession: prepared
        )
        self.document = document
        self.destination = destination
        self.session = prepared
        self.state = state
        self.container = container
        self.coordinator = attach ? container.makeCoordinator() : nil
    }

    func write(_ block: String) async -> EditorDocumentWriteError? {
        await lifetimeFailure {
            try await session.services.blockActionService.textServiceHandler.checked(
                contextId: document.objectId, blockId: block, newValue: true
            )
        }
    }
}

@MainActor
private func exerciseOriginalHostUpdates(_ checks: BoundaryChecks) async throws {
    let originalEffects = ["insets:91", "hidden:true", "owner:fixture-owner"]

    do {
        let actual = EditorPageController()
        let container = FixturePreparedContainer(viewController: actual)
        let coordinator = container.makeCoordinator()
        container.updateUIViewController(actual, context: .init(coordinator: coordinator))
        checks.expect(actual.updateEffects == originalEffects,
            "host_update_legacy_nil_session_keeps_all_three_original_effects")
    }

    do {
        let actual = EditorPageController()
        let original = FixturePreparedContainer(viewController: actual)
        let coordinator = original.makeCoordinator()
        let replacement = EditorPageController()
        let changed = FixturePreparedContainer(viewController: replacement)
        changed.updateUIViewController(actual, context: .init(coordinator: coordinator))
        checks.expect(actual.updateEffects.isEmpty && replacement.updateEffects == originalEffects,
            "host_update_legacy_nil_to_nil_replacement_preserves_original_callback_behavior")
    }

    do {
        let host = try HostUpdatePreparedFixture()
        host.container.updateUIViewController(
            host.state.viewController, context: .init(coordinator: host.coordinator!)
        )
        let outcome = await host.write("matching")
        let effects = await host.destination.snapshot()
        checks.expect(host.state.viewController.updateEffects == originalEffects
            && outcome == nil && effects.count == 1 && !host.session.owner.isRetired,
            "host_update_matching_prepared_identity_preserves_effects_and_actual_writer")
    }

    do {
        let host = try HostUpdatePreparedFixture()
        let replacement = EditorPageController()
        let changed = FixturePreparedContainer(
            viewController: replacement, preparedSession: host.session
        )
        changed.updateUIViewController(
            host.state.viewController, context: .init(coordinator: host.coordinator!)
        )
        let outcome = await host.write("stale-controller")
        let effects = await host.destination.snapshot()
        checks.expect(outcome == .rejected(.retired) && effects.isEmpty
            && host.state.viewController.updateEffects.isEmpty && replacement.updateEffects.isEmpty,
            "host_update_changed_incoming_controller_retires_only_the_captured_host")
    }

    do {
        let first = try HostUpdatePreparedFixture()
        let second = try HostUpdatePreparedFixture(document: first.document)
        second.container.updateUIViewController(
            first.state.viewController, context: .init(coordinator: first.coordinator!)
        )
        let oldOutcome = await first.write("old-session")
        let currentOutcome = await second.write("current-session")
        let oldEffects = await first.destination.snapshot()
        let currentEffects = await second.destination.snapshot()
        checks.expect(oldOutcome == .rejected(.retired) && oldEffects.isEmpty
            && currentOutcome == nil && currentEffects.count == 1
            && !second.session.owner.isRetired && second.coordinator?.hostLease != nil
            && first.state.viewController.updateEffects.isEmpty
            && second.state.viewController.updateEffects.isEmpty,
            "host_update_changed_session_does_not_revoke_another_already_hosted_owner")
    }

    do {
        let first = try HostUpdatePreparedFixture()
        let second = try HostUpdatePreparedFixture(document: first.document)
        first.container.updateUIViewController(
            second.state.viewController, context: .init(coordinator: first.coordinator!)
        )
        let firstOutcome = await first.write("first-remains")
        let secondOutcome = await second.write("second-remains")
        let firstEffects = await first.destination.snapshot()
        let secondEffects = await second.destination.snapshot()
        checks.expect(firstOutcome == nil && secondOutcome == nil
            && firstEffects.count == 1 && secondEffects.count == 1
            && !first.session.owner.isRetired && !second.session.owner.isRetired
            && first.state.viewController.updateEffects.isEmpty
            && second.state.viewController.updateEffects.isEmpty,
            "host_update_foreign_actual_callback_changes_neither_controller_nor_owner")
    }

    do {
        let host = try HostUpdatePreparedFixture()
        let changed = FixturePreparedContainer(viewController: host.state.viewController)
        changed.updateUIViewController(
            host.state.viewController, context: .init(coordinator: host.coordinator!)
        )
        let outcome = await host.write("removed-session")
        let effects = await host.destination.snapshot()
        checks.expect(outcome == .rejected(.retired) && effects.isEmpty
            && host.state.viewController.updateEffects.isEmpty,
            "host_update_removed_prepared_session_retires_the_captured_writer")
    }

    do {
        let actual = EditorPageController()
        let legacy = FixturePreparedContainer(viewController: actual)
        let coordinator = legacy.makeCoordinator()
        let incoming = try HostUpdatePreparedFixture(attach: false)
        incoming.container.updateUIViewController(actual, context: .init(coordinator: coordinator))
        let outcome = await incoming.write("unattached-reuse")
        let effects = await incoming.destination.snapshot()
        checks.expect(outcome == .rejected(.retired) && effects.isEmpty
            && actual.updateEffects.isEmpty && incoming.state.viewController.updateEffects.isEmpty,
            "host_update_new_unattached_prepared_session_cannot_reuse_a_legacy_host")
    }
}
