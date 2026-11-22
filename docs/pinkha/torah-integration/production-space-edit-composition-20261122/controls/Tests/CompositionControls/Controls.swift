import Foundation
import Testing

private enum CompositionControlFailure: Error {
    case missingAccount, missingDispatchBinding, missingCapture, fixtureTimeout, unexpectedError(String)
}

@MainActor
private func waitFor(_ predicate: @MainActor () -> Bool) async throws {
    for _ in 0..<100_000 {
        if predicate() { return }
        await Task.yield()
    }
    throw CompositionControlFailure.fixtureTimeout
}

@MainActor
private func writerError(_ body: () throws -> Void) throws -> EditorDocumentWriteError? {
    do {
        try body()
        return nil
    } catch let error as EditorDocumentWriteError {
        return error
    } catch {
        throw CompositionControlFailure.unexpectedError(String(describing: error))
    }
}

@MainActor
private func writerErrorAsync(_ body: () async throws -> Void) async throws -> EditorDocumentWriteError? {
    do {
        try await body()
        return nil
    } catch let error as EditorDocumentWriteError {
        return error
    } catch {
        throw CompositionControlFailure.unexpectedError(String(describing: error))
    }
}

private func currentPermit(_ name: String) async throws -> InvocationDispatchPermit {
    guard let binding = InvocationDispatchContext.binding else {
        throw CompositionControlFailure.missingDispatchBinding
    }
    return try await binding.prepare(messageName: name)
}

private func executeProbe(_ name: String, effects: AtomicStorage<Int>) async throws {
    let permit = try await currentPermit(name)
    let completion = try permit.begin()
    defer { completion.finish() }
    effects.access { $0 += 1 }
}

private func participant(_ role: ParticipantPermissions = .owner,
                         space: String = "space-A",
                         account: String = "actual-account",
                         id: String = "native-participant-A") -> Participant {
    Participant(id: id, localName: "Display", globalName: "", icon: nil,
                status: .active, permission: role, identity: account,
                identityProfileLink: "", spaceId: space, type: "native-participant-type")
}

@MainActor
private final class CompositionFixture {
    let account: AccountManager
    let participantTransport: ParticipantSubscriptionProbe
    let spaceTransport: SpaceSubscriptionProbe
    let configuration: ProbeServerConfigurationStorage
    let participants: ParticipantsStorage
    let spaces: SpaceViewsStorage
    private let dependencies: ProbeDependencies
    private let initialParticipants: [Participant]

    init(accountID: String = "actual-account",
         rows: [Participant] = [participant()],
         views: [SpaceView] = [SpaceView()]) {
        let account = AccountManager()
        account.account = AccountData(id: accountID, info: .init(techSpaceId: "actual-technical-space"))
        let participantTransport = ParticipantSubscriptionProbe(rows)
        let spaceTransport = SpaceSubscriptionProbe(views)
        let configuration = ProbeServerConfigurationStorage()
        let dependencies = ProbeDependencies(
            subscriptionStorageProvider: ProbeProvider(participant: participantTransport, space: spaceTransport),
            accountManager: account, spaceViewsSubscriptionBuilder: ProbeSpaceBuilder(),
            serverConfigurationStorage: configuration
        )
        ProbeRegistry.dependencies.value = dependencies
        self.account = account
        self.participantTransport = participantTransport
        self.spaceTransport = spaceTransport
        self.configuration = configuration
        self.dependencies = dependencies
        initialParticipants = rows
        participants = ParticipantsStorage()
        spaces = SpaceViewsStorage()
    }

    func start() async throws {
        ProbeRegistry.dependencies.value = dependencies
        await participants.startSubscription()
        await spaces.startSubscription()
        try await waitFor { self.participants.participants == self.initialParticipants }
    }

    func stop() async {
        await participants.stopSubscription()
        await spaces.stopSubscription()
    }

    func binding(additional: [EditorDocumentWriteLifetime] = [],
                 isCurrent: @escaping @MainActor () -> Bool = { true }) throws -> EditorDocumentWriteSourceBinding {
        guard let accountLifetime = account.editorWriteLifetime else {
            throw CompositionControlFailure.missingAccount
        }
        return try EditorDocumentWriteSourceBinding(
            lifetime: EditorDocumentWriteLifetime(), accountLifetime: accountLifetime,
            additionalLifetimes: additional, isCurrent: isCurrent
        )
    }

    func compose(_ source: EditorDocumentWriteSourceBinding, space: String = "space-A") throws -> EditorDocumentWriteSourceBinding {
        try source.requiringSpaceEditPermission(
            participant: participants.currentParticipantEditPermission(spaceId: space),
            spaceView: spaces.currentOriginalSpaceViewPermission(spaceId: space),
            spaceId: space
        )
    }
}

@MainActor
private final class BindingBox {
    var value: EditorDocumentWriteSourceBinding?
}

@Suite(.serialized, .timeLimit(.minutes(2)))
struct OriginalSpaceEditCompositionControls {
    @Test @MainActor
    func originalRoleAndLegacyPredicateWithBothConfigurations() async throws {
        let cases: [(ParticipantPermissions, Bool, Bool)] = [
            (.owner, false, true), (.admin, false, true), (.writer, false, true),
            (.reader, false, false), (.noPermissions, false, false), (.UNRECOGNIZED(37), false, false),
            (.owner, true, true), (.admin, true, false), (.writer, true, false),
            (.reader, true, false), (.noPermissions, true, false), (.UNRECOGNIZED(37), true, false)
        ]
        for (role, legacy, expected) in cases {
            for local in [false, true] {
                let row = participant(role)
                let view = SpaceView(legacy: legacy)
                let fixture = CompositionFixture(rows: [row], views: [view])
                fixture.configuration.local.value = local
                try await fixture.start()
                let base = try fixture.binding()
                #expect(SpacePermissions(spaceView: view, participant: row, isLocalMode: local).canEdit == expected)
                let result = try writerError { _ = try fixture.compose(base) }
                #expect(result == (expected ? nil : EditorDocumentWriteError.rejected(.notEditable)))
                await fixture.stop()
            }
        }
    }

    @Test @MainActor
    func missingFrozenAccountIsNotGrantedByValidPermissions() async throws {
        let fixture = CompositionFixture()
        try await fixture.start()
        let source = try EditorDocumentWriteSourceBinding(lifetime: EditorDocumentWriteLifetime(), isCurrent: { true })
        let result = try writerError { _ = try fixture.compose(source) }
        #expect(result == .rejected(.unqualifiedDispatch))
        await fixture.stop()
    }

    @Test @MainActor
    func exactAccountSourceAndGenerationAreRetained() async throws {
        let first = CompositionFixture()
        try await first.start()
        let firstBase = try first.binding()
        _ = try first.compose(firstBase)
        let second = CompositionFixture()
        try await second.start()
        let secondBase = try second.binding()
        _ = try second.compose(secondBase)
        let roleB = try second.participants.currentParticipantEditPermission(spaceId: "space-A")
        let viewA = try first.spaces.currentOriginalSpaceViewPermission(spaceId: "space-A")
        #expect(try writerError {
            _ = try firstBase.requiringSpaceEditPermission(participant: roleB, spaceView: viewA, spaceId: "space-A")
        } == .rejected(.wrongContext))
        let roleA = try first.participants.currentParticipantEditPermission(spaceId: "space-A")
        let viewB = try second.spaces.currentOriginalSpaceViewPermission(spaceId: "space-A")
        #expect(try writerError {
            _ = try firstBase.requiringSpaceEditPermission(participant: roleA, spaceView: viewB, spaceId: "space-A")
        } == .rejected(.wrongContext))
        let oldGeneration = try first.compose(firstBase)
        first.account.account = first.account.account
        await first.stop()
        try await first.start()
        _ = try first.compose(first.binding())
        #expect(try writerError { try oldGeneration.validate() } == .rejected(.retired))
        #expect(try writerError { _ = try first.compose(firstBase) } == .rejected(.retired))
        await first.stop()
        await second.stop()
    }

    @Test @MainActor
    func exactSpaceBytesAndBothOriginalSnapshotsMustMatch() async throws {
        let fixture = CompositionFixture(
            rows: [participant(), participant(space: "space-B", id: "native-participant-B")],
            views: [SpaceView(), SpaceView(id: "native-view-B", targetSpaceId: "space-B")]
        )
        try await fixture.start()
        let base = try fixture.binding()
        _ = try fixture.compose(base, space: "space-A")
        _ = try fixture.compose(base, space: "space-B")
        let roleA = try fixture.participants.currentParticipantEditPermission(spaceId: "space-A")
        let viewA = try fixture.spaces.currentOriginalSpaceViewPermission(spaceId: "space-A")
        let viewB = try fixture.spaces.currentOriginalSpaceViewPermission(spaceId: "space-B")
        #expect(try writerError {
            _ = try base.requiringSpaceEditPermission(participant: roleA, spaceView: viewB, spaceId: "space-A")
        } == .rejected(.wrongContext))
        #expect(try writerError {
            _ = try base.requiringSpaceEditPermission(participant: roleA, spaceView: viewA, spaceId: "SPACE-A")
        } == .rejected(.wrongContext))
        await fixture.stop()
    }

    @Test @MainActor
    func originalSourceCapturesCurrentnessAndStandaloneOperationRemainIntact() async throws {
        let fixture = CompositionFixture()
        try await fixture.start()
        let additional = EditorDocumentWriteLifetime()
        let base = try fixture.binding(additional: [additional])
        let composed = try fixture.compose(base)
        #expect(composed.lifetime === base.lifetime)
        #expect(composed.captures.count == base.captures.count + 2)
        for (original, retained) in zip(base.captures, composed.captures) {
            #expect(original.source === retained.source)
            #expect(original.token == retained.token)
        }
        let effects = AtomicStorage(0)
        try await composed.performOperation(rpcNames: ["ObjectSetDetails"]) {
            try await executeProbe("ObjectSetDetails", effects: effects)
        }
        #expect(effects.value == 1)
        additional.markUnavailable()
        #expect(try writerError { try composed.validate() } == .rejected(.retired))
        let current = AtomicStorage(true)
        let currentBase = try fixture.binding(isCurrent: { current.value })
        let currentComposed = try fixture.compose(currentBase)
        current.value = false
        #expect(try writerError { try currentComposed.validate() } == .rejected(.documentChanged))
        #expect(currentBase.lifetime.token() == nil)
        await fixture.stop()
    }

    @Test @MainActor
    func inheritedParentAndNamedRPCRestrictionRemainEnforcedByActualPermit() async throws {
        let fixture = CompositionFixture()
        try await fixture.start()
        let base = try fixture.binding()
        let role = try fixture.participants.currentParticipantEditPermission(spaceId: "space-A")
        let view = try fixture.spaces.currentOriginalSpaceViewPermission(spaceId: "space-A")
        let pin = try fixture.participants.currentChannelPinPermission(spaceId: "space-A")
        let document = CompositionDocument()
        let owner = try EditorDocumentWriteOwner(
            data: .init(objectId: document.objectId, spaceId: document.spaceId, mode: document.mode),
            lifetimeDocument: document, sourceBinding: base
        )
        let box = BindingBox()
        let effects = AtomicStorage(0)
        try await owner.performChannelPinMutation(contextId: document.objectId, permission: pin) {
            let child = try await MainActor.run {
                let original = try owner.childSourceBinding()
                let composed = try original.requiringSpaceEditPermission(participant: role, spaceView: view, spaceId: "space-A")
                box.value = composed
                return composed
            }
            try await child.performOperation(rpcNames: ["BlockCreateWidget"]) {
                try await executeProbe("BlockCreateWidget", effects: effects)
            }
        }
        #expect(effects.value == 1)
        guard let retainedChild = box.value else { throw CompositionControlFailure.missingCapture }
        try retainedChild.validate()
        owner.retire()
        #expect(try writerError { try retainedChild.validate() } == .rejected(.retired))

        let deniedDocument = CompositionDocument(objectId: "native-target-denied")
        let deniedOwner = try EditorDocumentWriteOwner(
            data: .init(objectId: deniedDocument.objectId, spaceId: deniedDocument.spaceId, mode: deniedDocument.mode),
            lifetimeDocument: deniedDocument, sourceBinding: base
        )
        let deniedEffects = AtomicStorage(0)
        let denied = try await writerErrorAsync {
            try await deniedOwner.performChannelPinMutation(contextId: deniedDocument.objectId, permission: pin) {
                let child = try await MainActor.run {
                    try deniedOwner.childSourceBinding().requiringSpaceEditPermission(
                        participant: role, spaceView: view, spaceId: "space-A"
                    )
                }
                try await child.performOperation(rpcNames: ["ObjectShow"]) {
                    try await executeProbe("ObjectShow", effects: deniedEffects)
                }
            }
        }
        #expect(denied == .rejected(.unqualifiedDispatch))
        #expect(deniedEffects.value == 0)
        deniedOwner.retire()
        await fixture.stop()
    }

    @Test @MainActor
    func participantReplacementAfterPreparationRejectsBeforeProbeEffect() async throws {
        let fixture = CompositionFixture()
        try await fixture.start()
        let source = try fixture.compose(fixture.binding())
        let prepared = AtomicStorage(false)
        let effects = AtomicStorage(0)
        let hold = ProbeHold()
        defer { Task { await hold.release() } }
        let operation = Task { @MainActor in
            try await writerErrorAsync {
                try await source.performOperation(rpcNames: ["ObjectSetDetails"]) {
                    let permit = try await currentPermit("ObjectSetDetails")
                    prepared.value = true
                    await hold.pause()
                    let completion = try permit.begin()
                    defer { completion.finish() }
                    effects.access { $0 += 1 }
                }
            }
        }
        try await waitFor { prepared.value }
        let changed = participant(.admin)
        fixture.participantTransport.send([changed])
        try await waitFor { fixture.participants.participants == [changed] }
        _ = try fixture.compose(fixture.binding())
        await hold.release()
        #expect(try await operation.value == .rejected(.retired))
        #expect(effects.value == 0)
        await fixture.stop()
    }

    @Test @MainActor
    func spaceReplacementAfterPreparationRejectsBeforeProbeEffect() async throws {
        let fixture = CompositionFixture()
        try await fixture.start()
        let source = try fixture.compose(fixture.binding())
        let prepared = AtomicStorage(false)
        let effects = AtomicStorage(0)
        let hold = ProbeHold()
        defer { Task { await hold.release() } }
        let operation = Task { @MainActor in
            try await writerErrorAsync {
                try await source.performOperation(rpcNames: ["ObjectSetDetails"]) {
                    let permit = try await currentPermit("ObjectSetDetails")
                    prepared.value = true
                    await hold.pause()
                    let completion = try permit.begin()
                    defer { completion.finish() }
                    effects.access { $0 += 1 }
                }
            }
        }
        try await waitFor { prepared.value }
        await fixture.spaceTransport.emit([SpaceView(legacy: true)])
        _ = try fixture.compose(fixture.binding())
        await hold.release()
        #expect(try await operation.value == .rejected(.retired))
        #expect(effects.value == 0)
        await fixture.stop()
    }

    @Test @MainActor
    func admittedEffectDrainsAfterRetirementButCannotReturnCurrentSuccess() async throws {
        let fixture = CompositionFixture()
        try await fixture.start()
        let source = try fixture.compose(fixture.binding())
        guard source.captures.count >= 2 else { throw CompositionControlFailure.missingCapture }
        let role = source.captures[source.captures.count - 2]
        let view = source.captures[source.captures.count - 1]
        let effects = AtomicStorage(0)
        let admitted = AtomicStorage(false)
        let roleDrained = AtomicStorage(false)
        let viewDrained = AtomicStorage(false)
        let hold = ProbeHold()
        defer { Task { await hold.release() } }
        let operation = Task { @MainActor in
            try await writerErrorAsync {
                try await source.performOperation(rpcNames: ["ObjectSetDetails"]) {
                    let permit = try await currentPermit("ObjectSetDetails")
                    let completion = try permit.begin()
                    defer { completion.finish() }
                    effects.access { $0 += 1 }
                    admitted.value = true
                    await hold.pause()
                }
            }
        }
        try await waitFor { admitted.value }
        #expect(effects.value == 1)
        #expect(role.source.probeAdmissionAndWaiterCounts.0 == 1)
        #expect(view.source.probeAdmissionAndWaiterCounts.0 == 1)
        await fixture.stop()
        #expect(try writerError { try source.validate() } == .rejected(.retired))
        let roleWaiter = Task {
            await role.source.waitForOperationsToDrain()
            roleDrained.value = true
        }
        let viewWaiter = Task {
            await view.source.waitForOperationsToDrain()
            viewDrained.value = true
        }
        try await waitFor {
            role.source.probeAdmissionAndWaiterCounts.1 == 1
                && view.source.probeAdmissionAndWaiterCounts.1 == 1
        }
        #expect(roleDrained.value == false)
        #expect(viewDrained.value == false)
        #expect(effects.value == 1)
        await hold.release()
        #expect(try await operation.value == .rejected(.retired))
        await roleWaiter.value
        await viewWaiter.value
        #expect(roleDrained.value)
        #expect(viewDrained.value)
        #expect(role.source.probeAdmissionAndWaiterCounts.0 == 0)
        #expect(view.source.probeAdmissionAndWaiterCounts.0 == 0)
        #expect(effects.value == 1)
    }

    @Test @MainActor
    func renewedActorSnapshotsDoNotReviveAnOldComposition() async throws {
        let fixture = CompositionFixture()
        try await fixture.start()
        let base = try fixture.binding()
        let old = try fixture.compose(base)
        await fixture.stop()
        try await fixture.start()
        let fresh = try fixture.compose(base)
        #expect(try writerError { try old.validate() } == .rejected(.retired))
        try fresh.validate()
        #expect(old.captures.count == fresh.captures.count)
        for index in base.captures.indices {
            #expect(old.captures[index].source === fresh.captures[index].source)
            #expect(old.captures[index].token == fresh.captures[index].token)
        }
        let effects = AtomicStorage(0)
        try await fresh.performOperation(rpcNames: ["ObjectSetDetails"]) {
            try await executeProbe("ObjectSetDetails", effects: effects)
        }
        #expect(effects.value == 1)
        #expect(try writerError { try old.validate() } == .rejected(.retired))
        await fixture.stop()
    }
}
