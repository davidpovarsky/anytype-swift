import Foundation
import Testing

@MainActor
private func selectionWait(_ predicate: @MainActor () async -> Bool) async throws {
    let deadline = ContinuousClock.now.advanced(by: .seconds(20))
    while ContinuousClock.now < deadline {
        if await predicate() { return }
        await Task.yield()
    }
    throw SelectionProbeError.conditionTimedOut
}

private func selectionError(_ body: () throws -> Void) -> (any Error)? {
    do { try body(); return nil } catch { return error }
}

@MainActor
private func selectionAsyncError(_ body: () async throws -> Void) async -> (any Error)? {
    do { try await body(); return nil } catch { return error }
}

private func errorOf<Value>(_ result: Result<Value, any Error>) -> (any Error)? {
    if case .failure(let error) = result { return error }
    return nil
}

@MainActor
private func selectAndSubscribe(_ fixture: SelectionFixture) async throws -> OriginalActiveSpaceSelection {
    let manager = try fixture.ownedManager()
    _ = try await manager.setActiveSpace(spaceId: "space-A")
    await manager.startSubscription()
    return try manager.currentOriginalActiveSpaceSelection()
}

@Suite(.serialized, .timeLimit(.minutes(2)))
struct OriginalSelectedSpaceControls {
    @Test @MainActor
    func exactOriginalServiceResponseAndFrozenIdentityRejectSubstitution() async throws {
        let fixture = SelectionFixture()
        defer { fixture.releaseAll() }
        await fixture.start()
        let manager = try fixture.ownedManager()
        let response = selectionInfo()
        fixture.enqueue(response)
        let value = try await manager.setActiveSpace(spaceId: "space-A")
        #expect(value == response.asModel)
        let selection = try manager.currentOriginalActiveSpaceSelection()
        #expect(selection.accountID == "actual-account")
        #expect(selection.accountInfo == response.asModel)
        let lifetime = try #require(fixture.account.editorWriteLifetime)
        let accountCapture = try EditorDocumentWriteCapture(lifetime)
        let capture = try selection.capture(matching: accountCapture, spaceId: "space-A")
        try capture.validate()
        #expect(selectionError {
            _ = try selection.capture(matching: accountCapture, spaceId: "SPACE-A")
        } as? EditorDocumentWriteError == .rejected(.wrongContext))
        let alien = try EditorDocumentWriteCapture(EditorDocumentWriteLifetime())
        #expect(selectionError {
            _ = try selection.capture(matching: alien, spaceId: "space-A")
        } as? EditorDocumentWriteError == .rejected(.wrongContext))
        #expect(fixture.rpc.state.value.requests == [.init(spaceID: "space-A", withChat: true)])
        #expect(fixture.rpc.state.value.prepared == 1)
        #expect(fixture.rpc.state.value.admitted == 1)
        #expect(fixture.rpc.state.value.finished == 1)
        #expect(fixture.rpc.state.value.qos == [.userInitiated])
        try await fixture.stop()

        for response in [selectionInfo("wrong-space"), selectionInfo(view: "wrong-view")] {
            let rejected = SelectionFixture()
            defer { rejected.releaseAll() }
            await rejected.start()
            rejected.enqueue(response)
            let manager = try rejected.ownedManager()
            let error = await selectionAsyncError { _ = try await manager.setActiveSpace(spaceId: "space-A") }
            #expect(error as? EditorDocumentWriteError == .rejected(.wrongContext))
            #expect(rejected.rpc.state.value.effects == 1)
            #expect(manager.workspaceInfo == nil)
            #expect(selectionError { _ = try manager.currentOriginalActiveSpaceSelection() } != nil)
            try await rejected.stop()
        }

        let replacement = ReplacementWorkspaceService(info: selectionInfo().asModel)
        let foreign = SelectionFixture(service: replacement)
        await foreign.start()
        let foreignManager = try foreign.ownedManager()
        let rejected = await selectionAsyncError { _ = try await foreignManager.setActiveSpace(spaceId: "space-A") }
        #expect(rejected != nil)
        #expect(replacement.calls.value == 0)
        #expect(replacement.shadowCalls.value == 0)
        #expect(foreign.rpc.state.value.requests.isEmpty)
        #expect(selectionError { _ = try foreignManager.currentOriginalActiveSpaceSelection() } != nil)
        try await foreign.stop()
    }

    @Test @MainActor
    func missingInitialViewAuthorityIsNeverRecapturedAfterNativeAwait() async throws {
        let fixture = SelectionFixture(views: [])
        defer { fixture.releaseAll() }
        await fixture.start()
        let manager = try fixture.ownedManager()
        let gate = SelectionGate()
        fixture.enqueue(before: gate)
        let pending = Task { try await manager.setActiveSpace(spaceId: "space-A") }
        try await selectionWait { gate.hasEntered }
        await fixture.transport.emit([SpaceView()])
        _ = try fixture.spaces.currentOriginalSpaceViewPermission(spaceId: "space-A")
        gate.release()
        let response = try await pending.value
        #expect(response == selectionInfo().asModel)
        #expect(manager.workspaceInfo == response)
        #expect(selectionError { _ = try manager.currentOriginalActiveSpaceSelection() }
                as? EditorDocumentWriteError == .rejected(.unqualifiedDispatch))
        #expect(fixture.rpc.state.value.effects == 1)
        try await fixture.stop()
    }

    @Test @MainActor
    func replacementRequestsRetireAThroughBAndABARoundTrip() async throws {
        for returnToA in [false, true] {
            let fixture = SelectionFixture()
            defer { fixture.releaseAll() }
            await fixture.start()
            let manager = try fixture.ownedManager()
            let gate = SelectionNativePause()
            fixture.enqueue(body: gate)
            fixture.enqueue(selectionInfo(returnToA ? "space-A" : "space-B",
                                          view: returnToA ? "native-view-A" : "native-view-B"))
            let first = Task { try await manager.setActiveSpace(spaceId: "space-A") }
            try await selectionWait { gate.hasEntered }
            let originalCapture = try #require(await manager.probeCurrentSelectionCapture())
            let second = Task { try await manager.setActiveSpace(spaceId: "space-B") }
            try await selectionWait { await manager.probeRequestedSpaceID() == "space-B" }
            #expect(selectionError { try originalCapture.validate() } as? EditorDocumentWriteError == .rejected(.retired))
            #expect(fixture.rpc.state.value.admitted == 1)
            if returnToA {
                let intermediate = try #require(await manager.probeCurrentSelectionCapture())
                let third = Task { try await manager.setActiveSpace(spaceId: "space-A") }
                try await selectionWait { await manager.probeRequestedSpaceID() == "space-A" }
                #expect(selectionError { try intermediate.validate() } as? EditorDocumentWriteError == .rejected(.retired))
                gate.release()
                #expect(errorOf(await first.result) != nil)
                #expect(errorOf(await second.result) != nil)
                #expect(try await third.value?.accountSpaceId == "space-A")
                #expect(fixture.rpc.state.value.requests.map(\.spaceID) == ["space-A", "space-A"])
            } else {
                gate.release()
                #expect(errorOf(await first.result) != nil)
                #expect(try await second.value?.accountSpaceId == "space-B")
                #expect(fixture.rpc.state.value.requests.map(\.spaceID) == ["space-A", "space-B"])
            }
            try manager.currentOriginalActiveSpaceSelection().validate()
            #expect(selectionError { try originalCapture.validate() } != nil)
            try await fixture.stop()
        }
    }

    @Test @MainActor
    func realPermitRejectsRetiredQueueAndAdmittedCompletionMustDrain() async throws {
        do {
            let fixture = SelectionFixture()
            defer { fixture.releaseAll() }
            await fixture.start()
            let manager = try fixture.ownedManager()
            let gate = SelectionGate()
            fixture.enqueue(before: gate)
            let request = Task { try await manager.setActiveSpace(spaceId: "space-A") }
            try await selectionWait { gate.hasEntered }
            fixture.account.account = AccountData(id: "replacement-account", info: selectionInfo().asModel)
            gate.release()
            let result = await request.result
            #expect(errorOf(result) as? EditorDocumentWriteError == .rejected(.retired))
            #expect(fixture.rpc.state.value.prepared == 1)
            #expect(fixture.rpc.state.value.admitted == 0)
            #expect(fixture.rpc.state.value.effects == 0)
            try await fixture.stop()
        }
        do {
            let fixture = SelectionFixture()
            defer { fixture.releaseAll() }
            await fixture.start()
            let manager = try fixture.ownedManager()
            let body = SelectionNativePause()
            let completion = SelectionNativePause()
            fixture.enqueue(body: body, after: completion)
            let requestReturned = AtomicStorage(false)
            let request = Task {
                defer { requestReturned.value = true }
                return try await manager.setActiveSpace(spaceId: "space-A")
            }
            try await selectionWait { body.hasEntered }
            let capture = try #require(await manager.probeCurrentSelectionCapture())
            #expect(capture.source.probeAdmissionAndWaiterCounts.0 == 1)
            fixture.account.account = AccountData(id: "replacement-account", info: selectionInfo().asModel)
            #expect(selectionError { try capture.validate() } as? EditorDocumentWriteError == .rejected(.retired))
            let stopped = AtomicStorage(false)
            let stop = Task { await manager.stopSubscription(); stopped.value = true }
            try await selectionWait { await manager.probeStopIsPending }
            #expect(!stopped.value)
            body.release()
            try await selectionWait { completion.hasEntered && capture.source.probeAdmissionAndWaiterCounts.1 > 0 }
            #expect(fixture.rpc.state.value.effects == 1)
            #expect(fixture.rpc.state.value.finished == 0)
            #expect(!requestReturned.value)
            #expect(!stopped.value)
            completion.release()
            #expect(errorOf(await request.result) != nil)
            await stop.value
            #expect(stopped.value)
            #expect(fixture.rpc.state.value.finished == 1)
            #expect(capture.source.probeAdmissionAndWaiterCounts.0 == 0)
            #expect(manager.workspaceInfo == nil)
            #expect(selectionError { _ = try manager.currentOriginalActiveSpaceSelection() } != nil)
            try await fixture.stop()
        }
    }

    @Test @MainActor
    func staleNativeFailureAndHelperCompletionCannotClearReplacement() async throws {
        for failNative in [true, false] {
            let fixture = SelectionFixture()
            defer { fixture.releaseAll() }
            await fixture.start()
            let manager = try fixture.ownedManager()
            let native = SelectionNativePause()
            let helper = SelectionGate()
            fixture.enqueue(fail: failNative, body: failNative ? native : nil)
            if !failNative { fixture.widgets.hold("widgets:space-A", at: helper) }
            fixture.enqueue(selectionInfo("space-B", view: "native-view-B"))
            let first = Task { try await manager.setActiveSpace(spaceId: "space-A") }
            try await selectionWait { failNative ? native.hasEntered : helper.hasEntered }
            let second = Task { try await manager.setActiveSpace(spaceId: "space-B") }
            try await selectionWait { await manager.probeRequestedSpaceID() == "space-B" }
            native.release()
            helper.release()
            #expect(errorOf(await first.result) != nil)
            #expect(try await second.value?.accountSpaceId == "space-B")
            #expect(try manager.currentOriginalActiveSpaceSelection().accountInfo.accountSpaceId == "space-B")
            #expect(manager.workspaceInfo?.accountSpaceId == "space-B")
            #expect(!fixture.widgets.calls.contains("clear"))
            #expect(!fixture.types.calls.contains("stop"))
            #expect(!fixture.properties.calls.contains("stop"))
            try await fixture.stop()
        }
    }

    @Test @MainActor
    func duplicateStopBlocksNewRequestsAndFencesQueuedOldSubscriptionCallback() async throws {
        let fixture = SelectionFixture()
        defer { fixture.releaseAll() }
        await fixture.start()
        let manager = try fixture.ownedManager()
        fixture.enqueue()
        _ = try await manager.setActiveSpace(spaceId: "space-A")
        await manager.startSubscription()
        let oldCallback = try #require(await manager.probeCapturedSubscriptionCallback())
        let clear = SelectionGate()
        fixture.widgets.hold("clear", at: clear)
        let firstStop = Task { await manager.stopSubscription() }
        try await selectionWait { clear.hasEntered }
        let secondStop = Task { await manager.stopSubscription() }
        try await selectionWait { await manager.probeDuplicateStopEntryCount() == 1 }
        #expect(await selectionAsyncError { _ = try await manager.setActiveSpace(spaceId: "space-B") }
                as? EditorDocumentWriteError == .rejected(.unqualifiedDispatch))
        await manager.startSubscription()
        #expect(await manager.probeCapturedSubscriptionCallback() == nil)
        clear.release()
        await firstStop.value
        await secondStop.value
        #expect(fixture.widgets.calls.filter { $0 == "clear" }.count == 1)
        #expect(fixture.types.calls.filter { $0 == "stop" }.count == 1)
        #expect(fixture.properties.calls.filter { $0 == "stop" }.count == 1)
        fixture.enqueue(selectionInfo("space-B", view: "native-view-B"))
        _ = try await manager.setActiveSpace(spaceId: "space-B")
        await manager.startSubscription()
        let currentCallback = try #require(await manager.probeCapturedSubscriptionCallback())
        await oldCallback([])
        #expect(manager.workspaceInfo?.accountSpaceId == "space-B")
        try manager.currentOriginalActiveSpaceSelection().validate()
        await currentCallback([])
        #expect(manager.workspaceInfo == nil)
        #expect(selectionError { _ = try manager.currentOriginalActiveSpaceSelection() } != nil)
        #expect(fixture.rpc.state.value.requests.map(\.spaceID) == ["space-A", "space-B"])
        try await fixture.stop()
    }

    @Test @MainActor
    func accountAndOriginalViewRetirementAreSynchronousAndCannotReviveSelection() async throws {
        for changeAccount in [true, false] {
            let fixture = SelectionFixture()
            defer { fixture.releaseAll() }
            await fixture.start()
            let manager = try fixture.ownedManager()
            fixture.enqueue()
            _ = try await manager.setActiveSpace(spaceId: "space-A")
            let old = try manager.currentOriginalActiveSpaceSelection()
            if changeAccount {
                fixture.account.account = AccountData(id: "restored-account", info: selectionInfo().asModel)
            } else {
                await fixture.transport.emit([SpaceView(accountStatus: .spaceDeleted)])
            }
            #expect(selectionError { try old.validate() } as? EditorDocumentWriteError == .rejected(.retired))
            #expect(selectionError { _ = try manager.currentOriginalActiveSpaceSelection() } != nil)
            if changeAccount {
                await fixture.spaces.stopSubscription()
                await fixture.spaces.startSubscription()
            } else {
                await fixture.transport.emit([SpaceView()])
            }
            _ = try fixture.spaces.currentOriginalSpaceViewPermission(spaceId: "space-A")
            #expect(selectionError { try old.validate() } as? EditorDocumentWriteError == .rejected(.retired))
            fixture.enqueue()
            _ = try await manager.setActiveSpace(spaceId: "space-A")
            let renewed = try manager.currentOriginalActiveSpaceSelection()
            try renewed.validate()
            #expect(renewed.accountID == (changeAccount ? "restored-account" : "actual-account"))
            #expect(selectionError { try old.validate() } != nil)
            #expect(fixture.rpc.state.value.effects == 2)
            try await fixture.stop()
        }
    }

    @Test @MainActor
    func cancellationOfOneAwaiterDoesNotRetireSharedManagerSelection() async throws {
        let fixture = SelectionFixture()
        defer { fixture.releaseAll() }
        await fixture.start()
        let manager = try fixture.ownedManager()
        let body = SelectionNativePause()
        fixture.enqueue(body: body)
        let first = Task { try await manager.setActiveSpace(spaceId: "space-A") }
        try await selectionWait { body.hasEntered }
        let second = Task { try await manager.setActiveSpace(spaceId: "space-A") }
        first.cancel()
        body.release()
        #expect(errorOf(await first.result) is CancellationError)
        #expect(try await second.value?.accountSpaceId == "space-A")
        try manager.currentOriginalActiveSpaceSelection().validate()
        #expect(fixture.rpc.state.value.requests.count == 1)
        #expect(fixture.rpc.state.value.effects == 1)
        try await fixture.stop()
    }

    @Test @MainActor
    func managerDeallocationRetiresRetainedSelectionAndCancelsConsumer() async throws {
        let fixture = SelectionFixture()
        defer { fixture.releaseAll() }
        await fixture.start()
        fixture.enqueue()
        let selection = try await selectAndSubscribe(fixture)
        try await selectionWait { fixture.spaces.allSpaceViewsPublisher.probeSubscriberCount == 1 }
        weak var weakManager = fixture.manager
        fixture.manager = nil
        try await selectionWait { weakManager == nil }
        #expect(selectionError { try selection.validate() } as? EditorDocumentWriteError == .rejected(.retired))
        try await selectionWait { fixture.spaces.allSpaceViewsPublisher.probeSubscriberCount == 0 }
        #expect(fixture.rpc.state.value.effects == 1)
        try await fixture.stop()
    }

    @Test @MainActor
    func existingDocumentAndReadLineageCannotGrantGlobalWorkspaceMutation() async throws {
        let fixture = SelectionFixture()
        defer { fixture.releaseAll() }
        await fixture.start()
        let manager = try fixture.ownedManager()
        let accountLifetime = try #require(fixture.account.editorWriteLifetime)
        let source = try EditorDocumentWriteSourceBinding(
            lifetime: EditorDocumentWriteLifetime(), accountLifetime: accountLifetime, isCurrent: { true }
        )
        let document = CompositionDocument()
        let owner = try EditorDocumentWriteOwner(
            data: .init(objectId: document.objectId, spaceId: document.spaceId, mode: document.mode),
            lifetimeDocument: document, sourceBinding: source
        )
        let readError = await selectionAsyncError {
            try await owner.performRead(contextId: document.objectId, rpcNames: ["ObjectShow"]) {
                _ = try await manager.setActiveSpace(spaceId: "space-A")
            }
        }
        #expect(readError as? EditorDocumentWriteError == .rejected(.unqualifiedDispatch))
        let mutationError = await selectionAsyncError {
            try await owner.performMutation(contextId: document.objectId) {
                _ = try await manager.setActiveSpace(spaceId: "space-A")
            }
        }
        #expect(mutationError as? EditorDocumentWriteError == .rejected(.unqualifiedDispatch))
        #expect(fixture.rpc.state.value.requests.isEmpty)
        fixture.enqueue()
        let service: any WorkspaceServiceProtocol = WorkspaceService()
        let namedError = await selectionAsyncError {
            try await source.performRead(rpcNames: ["ObjectShow"]) {
                _ = try await service.workspaceOpenForOriginalSelection(spaceId: "space-A")
            }
        }
        #expect(namedError as? EditorDocumentWriteError == .rejected(.unqualifiedDispatch))
        #expect(fixture.rpc.state.value.requests.count == 1)
        #expect(fixture.rpc.state.value.prepared == 0)
        #expect(fixture.rpc.state.value.admitted == 0)
        #expect(fixture.rpc.state.value.effects == 0)
        #expect(manager.workspaceInfo == nil)
        owner.retire()
        try await fixture.stop()
    }
}
