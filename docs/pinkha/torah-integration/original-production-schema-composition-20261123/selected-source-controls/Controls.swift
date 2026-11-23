
@main private struct SelectedSourceControls {
    @MainActor
    static func selection(_ account: EditorDocumentWriteLifetime) throws
        -> (OriginalActiveSpaceSelection, OriginalActiveSpaceSelectionAttempt, EditorDocumentWriteLifetime) {
        let subscription = EditorDocumentWriteLifetime()
        let permission = try OriginalSpaceViewPermission(
            accountID: "same-account-data", techSpaceID: "fixture-tech",
            spaceView: .init(id: "fixture-view", targetSpaceId: "fixture-space"),
            accountCapture: EditorDocumentWriteCapture(account),
            subscriptionCapture: EditorDocumentWriteCapture(subscription)
        )
        let attempt = try OriginalActiveSpaceSelectionAttempt(
            spaceId: "fixture-space", accountManager: AccountManager(account),
            workspaceStorage: SpaceViewsStorage(permission)
        )
        return (try OriginalActiveSpaceSelection(
            attempt: attempt, info: .init(accountSpaceId: "fixture-space", spaceViewId: "fixture-view")
        ), attempt, subscription)
    }

    @MainActor
    static func expect(_ expected: EditorDocumentWriteError, _ body: () throws -> Void) {
        do { try body(); preconditionFailure("Required rejection was absent: \(expected)") }
        catch { precondition(error as? EditorDocumentWriteError == expected, "\(error)") }
    }

    @MainActor static func main() async throws {
        var passed: [String] = []
        do {
            let source = EditorDocumentWriteLifetime(), account = EditorDocumentWriteLifetime()
            let additional = EditorDocumentWriteLifetime(), current = FixtureCurrentness()
            let original = try EditorDocumentWriteSourceBinding(
                lifetime: source, accountLifetime: account,
                additionalLifetimes: [additional], isCurrent: { current.value }
            )
            let parent = EditorDocumentWriteOwner()
            let child = original.inheritingParent(
                owner: parent, captures: original.captures,
                rpcRestriction: ["ObjectShow", "ObjectOpen"], isCurrent: { current.value }
            ).inheritingParent(
                owner: parent, captures: original.captures,
                rpcRestriction: ["ObjectShow"], isCurrent: { current.value }
            )
            let (selected, attempt, subscription) = try selection(account)
            let restricted = try child.requiringOriginalSelectedSpace(selected)
            precondition(restricted.lifetime === child.lifetime)
            precondition(restricted.parentOwner === parent && restricted.rpcRestriction == ["ObjectShow"])
            precondition(restricted.captures.count == child.captures.count + 1)
            for (before, after) in zip(child.captures, restricted.captures) {
                precondition(before.source === after.source && before.token == after.token)
            }
            precondition(restricted.captures.last!.source === attempt.capture.source)
            precondition(restricted.captures.last!.token == attempt.capture.token)
            try restricted.validate()
            _ = subscription
            passed.append("preserves original lifetime, all captures, parent identity and intersected RPC restriction")
        }
        do {
            let original = try EditorDocumentWriteSourceBinding(lifetime: .init(), isCurrent: { true })
            let (selected, _, _) = try selection(.init())
            expect(.rejected(.unqualifiedDispatch)) {
                _ = try original.requiringOriginalSelectedSpace(selected)
            }
            passed.append("rejects a source without an original private account capture")
        }
        do {
            let original = try EditorDocumentWriteSourceBinding(
                lifetime: .init(), accountLifetime: .init(), isCurrent: { true }
            )
            let (selected, _, _) = try selection(.init())
            expect(.rejected(.wrongContext)) {
                _ = try original.requiringOriginalSelectedSpace(selected)
            }
            passed.append("same account and Space data do not replace another original account lifetime")
        }
        do {
            let account = EditorDocumentWriteLifetime()
            let original = try EditorDocumentWriteSourceBinding(
                lifetime: .init(), accountLifetime: account, isCurrent: { true }
            )
            account.markUnavailable(); account.confirmOpened()
            let (selected, _, _) = try selection(account)
            expect(.rejected(.retired)) { _ = try original.requiringOriginalSelectedSpace(selected) }
            passed.append("reopened account generation cannot recapture authority for an older source")
        }
        do {
            let account = EditorDocumentWriteLifetime()
            let original = try EditorDocumentWriteSourceBinding(
                lifetime: .init(), accountLifetime: account, isCurrent: { true }
            )
            let (selected, attempt, _) = try selection(account)
            let restricted = try original.requiringOriginalSelectedSpace(selected)
            var sawRejection = false
            do {
                try await restricted.performOperation(rpcNames: ["ObjectShow"]) {
                    let permit = try await InvocationDispatchContext.binding!.prepare(messageName: "ObjectShow")
                    attempt.retire()
                    attempt.capture.source.confirmOpened()
                    let completion = try permit.begin()
                    completion.finish()
                    preconditionFailure("A retired selected attempt reached admitted work")
                }
            } catch {
                precondition(error as? EditorDocumentWriteError == .rejected(.retired))
                sawRejection = true
            }
            precondition(sawRejection)
            passed.append("selection retirement closes a prepared original permit before begin even after reopening")
        }
        do {
            let account = EditorDocumentWriteLifetime()
            let original = try EditorDocumentWriteSourceBinding(
                lifetime: .init(), accountLifetime: account, isCurrent: { true }
            )
            let (selected, _, subscription) = try selection(account)
            let restricted = try original.requiringOriginalSelectedSpace(selected)
            subscription.markUnavailable(); subscription.confirmOpened()
            expect(.rejected(.retired)) { try restricted.validate() }
            passed.append("actual SpaceView subscription retirement propagates through original selection capture")
        }
        do {
            let account = EditorDocumentWriteLifetime(), current = FixtureCurrentness()
            let original = try EditorDocumentWriteSourceBinding(
                lifetime: .init(), accountLifetime: account, isCurrent: { current.value }
            )
            let (selected, _, _) = try selection(account)
            let restricted = try original.requiringOriginalSelectedSpace(selected)
            current.value = false
            expect(.rejected(.documentChanged)) { try restricted.validate() }
            precondition(original.lifetime.token() == nil)
            passed.append("selection restriction retains host currentness predicate and original lifetime retirement")
        }
        do {
            let account = EditorDocumentWriteLifetime()
            let original = try EditorDocumentWriteSourceBinding(
                lifetime: .init(), accountLifetime: account, isCurrent: { true }
            )
            let parent = EditorDocumentWriteOwner()
            let child = original.inheritingParent(
                owner: parent, captures: original.captures, rpcRestriction: ["ObjectShow"], isCurrent: { true }
            )
            let (selected, _, _) = try selection(account)
            let restricted = try child.requiringOriginalSelectedSpace(selected)
            do {
                try await restricted.performOperation(rpcNames: ["ObjectShow", "ObjectOpen"]) {
                    _ = try await InvocationDispatchContext.binding!.prepare(messageName: "ObjectOpen")
                    preconditionFailure("Inherited RPC restriction was widened")
                }
                preconditionFailure("Forbidden RPC returned successfully")
            } catch { precondition(error as? EditorDocumentWriteError == .rejected(.unqualifiedDispatch)) }
            passed.append("actual source dispatch preserves inherited named RPC restriction")
        }
        let report: [String: Any] = [
            "status": "PORTABLE_SELECTED_SOURCE_BOUNDARY_PASS",
            "executed": passed.count, "passed": passed.count, "controls": passed,
            "native_rpc_calls": 0, "account_bootstrap": "NOT_RUN",
            "actual_parent_writer_runtime": "NOT_RUN_IDENTITY_FIXTURE_ONLY",
            "UIKit": "NOT_RUN", "Apple_native": "NOT_RUN", "device": "NOT_RUN",
            "historical_245_and_38": "NOT_REPLAYED"
        ]
        print(String(data: try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys]), encoding: .utf8)!)
    }
}
