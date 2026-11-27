# Inspector queued-request retirement

## Source finding and scope

At App `2752229aacf72f468f32a4bfe5fe0a91142f5dbe`, both original Heart search and native search create Tasks around shared presenter Open/Link/Unlink calls. The presenter's request IDs originate inside those async methods. Closing the picker calls `cancelPendingRequests()`, which clears existing IDs, but a previously queued callback can start afterwards and allocate a new ID. The native query-change and Retry callbacks have the same scheduling boundary. This is a source-proven pre-entry ownership gap; no wrong-Space write, UI failure or runtime reproduction is claimed here.

The shared session already checks document lifetime, active context, permissions, dispatch authorization and canonical readback. Those checks are preserved exactly. In particular, this patch does not replace repository authorization with a presentation token. The session can still be active when the picker alone closes, and a queued callback can otherwise reach a reactivated session for the same document; the missing ownership belongs to the picker action before scheduling.

## Minimal shared correction

The presenter adds a private presentation generation and five synchronous request factories for Search, association refresh, Open, Link and Unlink. Each returns an explicitly MainActor-isolated async closure. The closure captures the generation before a Task or framework callback can defer execution, checks generation and caller cancellation, then awaits the existing public async method. `cancelPendingRequests()` retires the generation in addition to clearing the original independent search, refresh, open and mutation request identifiers.

Both views capture button/query actions before Task creation. The original Heart `.task(id:)` and native refresh `.task` await the captured operation directly, so cancellation remains on the caller task; there is no unstructured child `Task.value` bridge. The Heart asynchronous error button receives a captured operation during body evaluation. No direct onSubmit-to-presenter callback exists in these two exact source files.

All five original public async method signatures and complete bodies remain byte-identical. All session, provider, note, exact document/block navigation, native, lease and repository files remain unchanged. The synchronous existing linked-source Open path remains unchanged. Search query/scope rules, per-kind capabilities, original mutation serialization and all existing timeouts are unchanged.

The native view is based on the exact primary readback of Retry successor `1a890015578962bc6eab8c6e9bb70c51ce189cf3` (`beea22b4…`), not the older current-head view. Its localized Retry action is retained and now captures the same presentation ownership before scheduling.

## Focused regressions, not yet executed

The existing `AnyTypeTests/Pinkha/TorahSearchResolutionPublicationTests.swift` retains its complete 6,631-byte original prefix and the original one method/two cases. A separate suite is appended:

| Method | Declared cases | Meaning |
| --- | ---: | --- |
| `TorahSearchQueuedRequestTests.queuedActionIsRetiredBeforeRepositoryEntry(operation:reopenDocument:)` | 12 | Six real request paths (Search, Refresh, Open, Link, Unlink, selection-only Apply), each after picker retirement and after retirement plus same-document deactivate/reactivate. Old queued action must invoke zero provider/repository/open/selection callbacks; a newly captured action must successfully use the original session path. |
| `TorahSearchQueuedRequestTests.cancelledStructuredReadDoesNotEnterProvider(operation:)` | 2 | A cancelled caller awaiting Search or Refresh must not enter the provider/repository or publish loading/results. |

The tests enqueue while still on MainActor, retire or cancel before yielding, and then await completion; they do not rely on arbitrary sleeps. Controlled provider/repository protocol implementations exercise the actual shared session, including its real authorization closure and canonical record readback. They perform no Native call, account creation, remote request or storage setup. The production session's SearchResult/SearchScope remain unchanged; the new returned closures are explicitly MainActor-isolated and are not sent to a nonisolated executor.

**New scope: 2 methods / 14 declared cases. Entire source file: 3 methods / 16 declared cases. Swift compilation, test enumeration, XCTest/Swift Testing execution, mounted UI, visual and Native acceptance remain NOT_RUN.** The existing hosted Inspector profile selects only the old method and must not be relabelled as coverage for the new suite.

## Exact source retention

`candidate-manifest.json` pins all five changes: shared presenter, two UI consumers, appended existing test file, and the source refactor map. `source-inverse.json` records full-byte reversal of each change. All 132 map rows remain; only the existing shared presenter and Heart-view Git blob pins change. `source-structure-proof.json` records complete original async bodies and test-prefix preservation. `primary/` retains immutable GitHub reads; `source/` is App275, and `retry-source/` is the independently published native Retry donor. Initial local materialization/inverse cardinality stops are retained in `preparation-attempt1.json` and `preparation-attempt2.json`; neither involved compilation or remote execution.

Runtime and product admission are coordinated by Wave3. No existing accepted journey, old failure, fixture TTL, Native API or consumer gate is changed by this source candidate.
