import Foundation
import Testing
import HanlinHostContracts
import HanlinPlatformContracts
@testable import Anytype

#if DEBUG
/// Actual SDK combined port + actual read adapter using the existing component access spy.
/// No native write authority/approval is manufactured, and no journal/native/UI proof is claimed.
@Suite("Hanlin combined host port and unavailable-write boundaries", .serialized)
@MainActor
struct HanlinHostReadWriteTests {
    struct Harness: Sendable {
        let access: HanlinHostAdapterTests.Access
        let host: PinkhaHanlinReadWriteHost
    }
    @MainActor final class Events {
        var count = 0
        func record() { count += 1 }
    }

    func harness() throws -> Harness {
        let fixture = HanlinHostAdapterTests()
        let access = HanlinHostAdapterTests.Access(context: try fixture.context())
        let read = try PinkhaHanlinHostAdapter(access: access)
        return .init(access: access, host: try .readOnlyForTesting(read: read, session: access.session))
    }

    func call(_ h: Harness, id: String = UUID().uuidString.lowercased(), run: UUID = UUID(),
              provider: String = "opaque/Call:A") throws -> HanlinHostInvocation {
        try HanlinHostAdapterTests().invocation(h.access, id: id, run: run, provider: provider)
    }

    func changed(_ original: HanlinHostInvocation, alias: String? = nil,
                 descriptor: HanlinDescriptorRevision? = nil, catalog: HanlinCatalogRevision? = nil,
                 origin: HanlinExecutionOrigin? = nil, grants: [HanlinGrantID] = [],
                 arguments: HanlinJSONValue? = nil, timeout: Int64? = nil,
                 deadline: Date? = nil) throws -> HanlinHostInvocation {
        let r = original.request
        return .init(request: .init(id: r.id, logicalToolID: r.logicalToolID, aliasUsed: alias ?? r.aliasUsed,
            descriptorRevision: descriptor ?? r.descriptorRevision, routingTableRevision: catalog ?? r.routingTableRevision,
            arguments: arguments ?? r.arguments, origin: origin ?? r.origin, grantIDs: grants,
            deadline: deadline ?? r.deadline, limits: try .init(timeoutMilliseconds: timeout ?? r.limits.timeoutMilliseconds,
                                                   maximumOutputBytes: r.limits.maximumOutputBytes)),
            session: original.session, runID: original.runID, step: original.step, providerCallID: original.providerCallID,
            writeGuarantee: original.writeGuarantee, expectedRevision: original.expectedRevision)
    }

    @Test func sameSessionReadRoutesToActualAdapterAndExposesMetadataOnly() async throws {
        let h = try harness()
        #expect(try await h.host.context(for: h.access.session) == h.access.session.context)
        let request = try call(h)
        let result = try await h.host.execute(request) { _ in }
        #expect(h.access.reads == 1)
        #expect(result.effectState == .confirmedNoEffect)
        #expect(result.context == h.access.session.context)
        guard case .completed(let contents) = h.host.metadataReceipt(for: request.request.id)?.result.outcome else {
            Issue.record("missing delegated metadata receipt"); return
        }
        #expect(contents.isEmpty)
    }

    @Test func readOnlyFallbackPreservesActualConsentAndOmitsUninstalledWrite() async throws {
        let h = try harness()
        let catalog = try await h.host.catalog(for: h.access.session.context)
        #expect(catalog.tools.count == 1)
        #expect(catalog.tools.allSatisfy { $0.writeGuarantee == .readOnly })
        #expect(!h.host.missingWriteInstallation.isEmpty)
        h.access.consent = false
        #expect(try await h.host.catalog(for: h.access.session.context).tools.isEmpty)
        #expect(h.access.reads == 0)
    }

    @Test func validCreateDTOIsRefusedBeforeProgressApprovalOrNativeRead() async throws {
        let h = try harness()
        let invocation = try HanlinHostWriteTests().invocation(session: h.access.session)
        _ = try PinkhaHanlinCreatePagePlan(invocation: invocation) // A valid plan is still not authority/install readiness.
        let events = Events()
        let result = try await h.host.execute(invocation) { _ in await events.record() }
        #expect(result.effectState == .notDispatched)
        #expect(events.count == 0)
        #expect(h.access.reads == 0)
        #expect(h.host.metadataReceipt(for: invocation.request.id) == nil)
    }

    @Test func changedSessionIsRejectedBeforeDelegateEffects() async throws {
        let h = try harness()
        let other = try harness()
        let result = try await h.host.execute(call(other)) { _ in }
        #expect(result.effectState == .notDispatched)
        #expect(h.access.reads == 0)
        do { _ = try await h.host.context(for: other.access.session); Issue.record("foreign session accepted") }
        catch HanlinHostError.staleContext {}
    }

    @Test func staleRoutesDescriptorsRevisionsOriginsGrantsAndSchemasAreRefused() async throws {
        let h = try harness()
        let original = try call(h)
        let invalid = try [changed(original, alias: "unknown_route"), changed(original, descriptor: HanlinDescriptorRevision(2)),
            changed(original, catalog: .init(2)), changed(original, origin: .nativeModule),
            changed(original, grants: [.init(validating: "foreign-grant")]),
            changed(original, arguments: .object(["targetSpace": .string("other")]))]
        let events = Events()
        for invocation in invalid {
            #expect(try await h.host.execute(invocation) { _ in await events.record() }.effectState == .notDispatched)
        }
        #expect(events.count == 0)
        #expect(h.access.reads == 0)
    }

    @Test func CASAndExpectedRevisionCannotEnterEitherDelegate() async throws {
        let h = try harness()
        for guarantee in [HanlinHostWriteGuarantee.atomicRevisionMutation, .independentObjectCreation] {
            let invocation = try HanlinHostAdapterTests().invocation(h.access, guarantee: guarantee)
            #expect(try await h.host.execute(invocation) { _ in }.effectState == .notDispatched)
        }
        let conditionalRead = try HanlinHostAdapterTests().invocation(h.access, revision: "r1")
        #expect(try await h.host.execute(conditionalRead) { _ in }.effectState == .notDispatched)
        #expect(h.access.reads == 0)
    }

    @Test func cancellationBeforeRouteClaimPreventsRead() async throws {
        let h = try harness()
        let invocation = try call(h)
        await h.host.cancel(invocation.request.id)
        do { _ = try await h.host.execute(invocation) { _ in }; Issue.record("cancelled request dispatched") }
        catch HanlinHostError.cancelled {}
        #expect(h.access.reads == 0)
    }

    @Test func cancellationDuringProgressReachesTheCorrectRealReadAdapter() async throws {
        let h = try harness()
        let invocation = try call(h)
        do {
            _ = try await h.host.execute(invocation) { _ in await h.host.cancel(invocation.request.id) }
            Issue.record("cancelled read delivered")
        } catch HanlinHostError.cancelled {}
        #expect(h.access.reads == 0)
        #expect(h.host.metadataReceipt(for: invocation.request.id)?.effectState == .notDispatched)
    }

    @Test func replayAndChangedEnvelopeAreRejectedBeforeAnotherDelegateRun() async throws {
        let h = try harness()
        let invocation = try call(h)
        _ = try await h.host.execute(invocation) { _ in }
        do { _ = try await h.host.execute(invocation) { _ in }; Issue.record("duplicate delegated twice") }
        catch HanlinHostError.duplicateInvocation {}
        do { _ = try await h.host.execute(changed(invocation, timeout: 10_000)) { _ in }; Issue.record("changed envelope accepted") }
        catch HanlinHostError.idempotencyConflict {}
        #expect(h.access.reads == 1)
    }

    @Test func opaqueProviderIdentityIsExactAndCannotBeReminted() async throws {
        let h = try harness()
        let run = UUID()
        _ = try await h.host.execute(call(h, run: run, provider: "Call/A")) { _ in }
        _ = try await h.host.execute(call(h, run: run, provider: "Call:A")) { _ in }
        do { _ = try await h.host.execute(call(h, run: run, provider: "Call/A")) { _ in }; Issue.record("provider identity reminted") }
        catch HanlinHostError.idempotencyConflict {}
        #expect(h.access.reads == 2)
    }

    @Test func exactReplayAfterConsentLossKeepsOriginalEffectInsteadOfNewRefusal() async throws {
        let h = try harness()
        let invocation = try call(h)
        _ = try await h.host.execute(invocation) { _ in }
        let original = h.host.metadataReceipt(for: invocation.request.id)
        h.access.consent = false
        let events = Events()
        do { _ = try await h.host.execute(invocation) { _ in await events.record() }; Issue.record("known call reclassified") }
        catch HanlinHostError.duplicateInvocation {}
        #expect(h.access.reads == 1)
        #expect(events.count == 0)
        #expect(h.host.metadataReceipt(for: invocation.request.id) == original)
        #expect(original?.effectState == .confirmedNoEffect)
    }

    @Test func changedEnvelopeAndProviderRemintConflictAfterCapabilityDisappears() async throws {
        let h = try harness()
        let invocation = try call(h)
        _ = try await h.host.execute(invocation) { _ in }
        let original = h.host.metadataReceipt(for: invocation.request.id)
        h.access.consent = false
        do { _ = try await h.host.execute(changed(invocation, timeout: 10_000)) { _ in }; Issue.record("changed call reclassified") }
        catch HanlinHostError.idempotencyConflict {}
        let reminted = try call(h, run: invocation.runID, provider: invocation.providerCallID)
        do { _ = try await h.host.execute(reminted) { _ in }; Issue.record("provider remint reclassified") }
        catch HanlinHostError.idempotencyConflict {}
        #expect(h.access.reads == 1)
        #expect(h.host.metadataReceipt(for: invocation.request.id) == original)
    }

    @Test func malformedKnownArgumentsAndProviderConflictAfterCapabilityLoss() async throws {
        let h = try harness()
        let invocation = try call(h)
        _ = try await h.host.execute(invocation) { _ in }
        h.access.consent = false
        let changedSchema = try changed(invocation, arguments: .object(["foreign": .array([])]))
        do { _ = try await h.host.execute(changedSchema) { _ in }; Issue.record("invalid known schema reclassified") }
        catch HanlinHostError.idempotencyConflict {}
        let oversizedProvider = HanlinHostInvocation(request: invocation.request, session: invocation.session,
            runID: invocation.runID, step: invocation.step, providerCallID: String(repeating: "x", count: 1_025),
            writeGuarantee: invocation.writeGuarantee)
        do { _ = try await h.host.execute(oversizedProvider) { _ in }; Issue.record("invalid known provider reclassified") }
        catch HanlinHostError.idempotencyConflict {}
        #expect(h.access.reads == 1)
        #expect(h.host.metadataReceipt(for: invocation.request.id)?.effectState == .confirmedNoEffect)
    }

    @Test func changedExpiredDeadlineAndInvalidatedReplayNeverInventNewNotDispatchedEffect() async throws {
        let h = try harness()
        let invocation = try call(h)
        _ = try await h.host.execute(invocation) { _ in }
        let original = h.host.metadataReceipt(for: invocation.request.id)
        do { _ = try await h.host.execute(changed(invocation, deadline: .distantPast)) { _ in }; Issue.record("known expired change reclassified") }
        catch HanlinHostError.idempotencyConflict {}
        await h.host.invalidate()
        do { _ = try await h.host.execute(invocation) { _ in }; Issue.record("invalidated known call reclassified") }
        catch HanlinHostError.duplicateInvocation {}
        #expect(h.access.reads == 1)
        #expect(h.host.metadataReceipt(for: invocation.request.id) == original)
    }

    @Test func exactReplayAfterItsDeadlineExpiresPreservesOriginalEffect() async throws {
        let h = try harness()
        let deadline = Date().addingTimeInterval(2)
        let invocation = try HanlinHostAdapterTests().invocation(h.access, deadline: deadline)
        _ = try await h.host.execute(invocation) { _ in }
        let original = h.host.metadataReceipt(for: invocation.request.id)
        try await Task.sleep(for: .seconds(max(0, deadline.timeIntervalSinceNow) + 0.02))
        #expect(deadline <= .now)
        do { _ = try await h.host.execute(invocation) { _ in }; Issue.record("expired known call reclassified") }
        catch HanlinHostError.duplicateInvocation {}
        #expect(h.access.reads == 1)
        #expect(h.host.metadataReceipt(for: invocation.request.id) == original)
        #expect(original?.effectState == .confirmedNoEffect)
    }

    @Test func navigationRemainsQueuedAndInvalidationPreservesOriginalMetadata() async throws {
        let h = try harness()
        let destination = HanlinHostDestination(context: h.access.session.context, objectReference: "doc", blockReference: "K")
        let queued = try await h.host.open(destination)
        #expect(!queued.presentationAcknowledged)
        let invocation = try call(h)
        h.access.onRead = { await h.host.invalidate() }
        do { _ = try await h.host.execute(invocation) { _ in }; Issue.record("invalidated payload delivered") }
        catch {}
        #expect(h.host.metadataReceipt(for: invocation.request.id)?.context == invocation.session.context)
        #expect(h.host.metadataReceipt(for: invocation.request.id)?.effectState == .confirmedNoEffect)
        do { _ = try await h.host.catalog(for: h.access.session.context); Issue.record("invalidated catalog accepted") }
        catch HanlinHostError.staleContext {}
    }

    @Test func writePreflightDenialPreventsRunnerAndRetainsOriginalMetadata() async throws {
        let fixtures = HanlinHostWriteTests()
        let invocation = try fixtures.invocation(session: fixtures.session())
        let boundary = PinkhaHanlinWritePreflight()
        var runnerEntries = 0
        let result = try await boundary.execute(invocation, prepare: { () async throws -> Void in
            await Task.yield()
            throw HanlinHostError.denied
        }, dispatch: { _ in
            runnerEntries += 1
            throw HanlinHostError.unresolvedWrite
        })
        #expect(runnerEntries == 0)
        #expect(result.effectState == .notDispatched)
        #expect(result.context == invocation.session.context)
        #expect(result.result.invocationID == invocation.request.id)
        #expect(result.result.logicalToolID == invocation.request.logicalToolID)
        #expect(result.reconciliationReference == nil)
        #expect(boundary.receipt(for: invocation.request.id) == result.metadataReceipt())
        guard case .failed(let failure) = result.result.outcome else {
            Issue.record("Denied native preparation reported success"); return
        }
        #expect(failure.code == .permissionDenied)
    }

    @Test func writePreflightErrorsPreserveSafeCodesWithoutRunnerEntry() async throws {
        let fixtures = HanlinHostWriteTests()
        let boundary = PinkhaHanlinWritePreflight()
        let failures: [(Error, HanlinErrorCode)] = [
            (CancellationError(), .cancelled),
            (HanlinHostError.cancelled, .cancelled),
            (HanlinHostError.deadlineExceeded, .timedOut),
            (HanlinHostError.invalidArguments, .invalidArguments),
            (PinkhaHanlinWriteError.invalidPlan, .invalidArguments),
            (HanlinHostError.outputLimitExceeded, .resourceLimitExceeded),
            (HanlinHostError.staleContext, .permissionDenied),
            (NSError(domain: "private-fixture", code: 17,
                     userInfo: [NSLocalizedDescriptionKey: "private-request-detail"]), .operationUnavailable)
        ]
        var runnerEntries = 0
        for (error, code) in failures {
            let invocation = try fixtures.invocation(session: fixtures.session())
            let result = try await boundary.execute(invocation, prepare: { () async throws -> Void in
                await Task.yield()
                throw error
            }, dispatch: { _ in
                runnerEntries += 1
                throw HanlinHostError.unresolvedWrite
            })
            #expect(result.effectState == .notDispatched)
            #expect(result.context == invocation.session.context)
            #expect(boundary.receipt(for: invocation.request.id) == result.metadataReceipt())
            guard case .failed(let failure) = result.result.outcome else {
                Issue.record("Preparation failure reported success"); return
            }
            #expect(failure.code == code)
            #expect(failure.userMessage == "Host operation unavailable or no longer authorized")
        }
        #expect(runnerEntries == 0)
    }

    @Test func writeRunnerResultsAndErrorsKeepTheirOriginalDisposition() async throws {
        let fixtures = HanlinHostWriteTests()
        let boundary = PinkhaHanlinWritePreflight()
        var runnerEntries = 0
        for effect in [HanlinHostEffectState.notDispatched, .uncertain, .confirmedCommitted] {
            let invocation = try fixtures.invocation(session: fixtures.session())
            let expected = HanlinHostExecutionResult(
                result: .init(invocationID: invocation.request.id, logicalToolID: invocation.request.logicalToolID,
                    outcome: effect == .confirmedCommitted ? .completed([]) : .failed(.init(
                        code: .operationUnavailable, userMessage: "Original runner disposition")), completedAt: .now),
                effectState: effect, context: invocation.session.context, reconciliationReference: "original-receipt")
            let result = try await boundary.execute(invocation, prepare: { 41 }, dispatch: { prepared in
                #expect(prepared == 41)
                runnerEntries += 1
                await Task.yield()
                return expected
            })
            #expect(result == expected)
            #expect(boundary.receipt(for: invocation.request.id) == nil)
        }
        let invocation = try fixtures.invocation(session: fixtures.session())
        do {
            _ = try await boundary.execute(invocation, prepare: { 42 }, dispatch: { prepared in
                #expect(prepared == 42)
                runnerEntries += 1
                await Task.yield()
                throw HanlinHostError.unresolvedWrite
            })
            Issue.record("Runner error was reclassified as a pre-dispatch refusal")
        } catch HanlinHostError.unresolvedWrite {}
        #expect(runnerEntries == 4)
        #expect(boundary.receipt(for: invocation.request.id) == nil)
    }

    #if os(iOS)
    @Test func journalReadinessQueryCannotAdmitUnresolvedOrForeignScope() async throws {
        // New query behavior only. Synthetic journal transitions are NOT native effect/durability proof.
        let fixtures = HanlinHostWriteTests()
        let parent = try fixtures.directory()
        defer { try? FileManager.default.removeItem(at: parent) } // Exact new owned test directory only.
        let session = try fixtures.session()
        let journal = try await PinkhaHanlinWriteJournal.openInTestDirectory(parent, namespace: session.context.namespace)
        try await journal.validateCreationAvailability(namespace: session.context.namespace)
        let plan = try PinkhaHanlinCreatePagePlan(invocation: fixtures.invocation(session: session))
        try await journal.reserve(plan.identity)
        do { try await journal.validateCreationAvailability(namespace: session.context.namespace); Issue.record("pending admitted") }
        catch PinkhaHanlinWriteError.unresolved {}
        try await journal.record(.uncertain, identity: plan.identity)
        do { try await journal.validateCreationAvailability(namespace: session.context.namespace); Issue.record("uncertain admitted") }
        catch PinkhaHanlinWriteError.unresolved {}
        try await journal.record(.committed, identity: plan.identity, createdObjectReference: "native-reference-fixture")
        try await journal.validateCreationAvailability(namespace: session.context.namespace)
        let other = try fixtures.session(space: "other")
        do { try await journal.validateCreationAvailability(namespace: other.context.namespace); Issue.record("foreign admitted") }
        catch PinkhaHanlinWriteError.invalidPlan {}
    }
    #endif
}
#endif
