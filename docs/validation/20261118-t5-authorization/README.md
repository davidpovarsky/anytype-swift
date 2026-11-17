# T5 host action authority and native proof wiring — 2026-11-17 UTC

## Result

Completed a bounded T5 host implementation update and preserved the existing native proof drafts in the new wave worktree. The T5 Asana task remains open. Full current-Space related-document acceptance, block-only and source-quote discovery, native compatibility, iOS host tests, Inspector UI, and physical iPad acceptance are not established by this work.

Worktree: `C:/Users/DAVID/Code/anytype-swift-chatgpt-t5-20261118`
Branch: `codex/chatgpt-wave15-t5-20261118`
Original app base: `5f023e9dc8d33cad7fac73103acd763cdcba8730`

| Change | Exact revision or patch |
| --- | --- |
| Initial host lifetime/authority changes and 7 host tests | `8797be2575eb12954340611240a6fefd43eaeac2` |
| Preserved native proof controller/workflow and dispatch route | `56be32bd491ad635c3e734ffdf767b14ac073486` |
| Uncommitted lifetime/flow follow-up against 56be32bd | `followup.patch`, SHA-256 `11e90fa05181ebcc0a6821bbbe44efa313df5cf31fc2a23b0ce254e49492e986` |
| Complete T5 change against original 5f023e9d base | `complete-t5.patch`, SHA-256 `65f8662946d79263cd94efe0bef148c285df0561f30fbb50b2edbaf45cb81ce3` |

Both commits completed before this agent received the manager's automatic-approval rejection boundary. No staging, commit, push, cherry-pick or merge was performed after that boundary. The five follow-up source/test files and this evidence folder remain uncommitted.

## Host behavior changed

- Related-document navigation checks the active document lifetime, captured presenter selection, current Space, and nonempty object ID.
- Add Note, open Note and unlink callbacks retain the presenter selection ID and action epoch from when the callbacks were created. Replacing the root selection or document lifetime invalidates older callbacks.
- Inspector close advances the action epoch. A retained close callback cannot dismiss a later presentation.
- Unlink checks current edit authority and cancellation before canonical reads, after suspended reads, and before each association mutation. Unlink still removes associations and never deletes a Note object.
- Late unlink, open-Note and add-Note errors are published only into the lifetime that initiated the action.
- The existing T5NoteCreationFlow now requires an authorization closure and checks it before object creation, source linking, source-line writing and origin linking. Existing partial recovery preserves the created Note ID and does not blindly repeat an uncertain source-line write.
- The host retains the extra cancellation/authorization check after the asynchronous last-block lookup and before dispatching the source-line write.

The authorization checks precede dispatch. They do not establish atomic native ACL enforcement while an already dispatched command commits.

### Presenter and source identities

The Inspector intentionally reuses hostActions for segment details, linked sources and internal full-source search destinations. A source action may therefore receive a segment or linked-source selection different from the root presenter selection. The implementation validates the captured presenter identity and lifetime; it does not incorrectly require the action's segment selection to equal the root selection.

Contract evidence: TorahInspectorKit at c3fbb6c, `Sources/TorahInspectorCore/Models.swift` (TorahInspectorSelection and TorahInspectorFocus), `Sources/TorahInspectorUI/TorahInspectorView.swift` (navigation destinations), and `Sources/TorahInspectorUI/TorahSegmentDetailView.swift` (Notes and Related Documents actions).

## Executed verification

| Verification | Actual result | Boundary |
| --- | --- | --- |
| Swift 6 parse of the five follow-up files | PASS | Grammar only for Anytype host code |
| git diff whitespace check | PASS | Source formatting only |
| Existing CI controller tests | 5 PASS | Run identity, interruption and evidence-reuse controls; no native fixture |
| Immutable proof input SHA verification | 6/6 PASS | Inputs match pinned source 947fbde |
| Portable T5NoteCreationFlowTests | 6 test functions / 8 cases PASS, 0 failures | Actual production PinkhaKit flow code on Windows; controlled write callbacks |
| TorahRelatedDocumentActionTests | 10 authored test functions / 11 cases; NOT_RUN | Requires Anytype Apple test host |
| r15 native-index / RPC / compatibility pairing | NOT_RUN | Client capability remains disabled |
| SwiftUI / iPad / physical device | NOT_RUN | No UI acceptance claim |

The portable test package copies all 44 actual PinkhaKit Swift source files and all 7 TorahInspectorCore files from pinned Kit c3fbb6c, plus the exact updated T5NoteCreationFlowTests file. All 52 files are SHA-verified against the original worktrees before and after execution. No production source is replaced by a test implementation. Note creation/write effects use controlled closures: this validates the flow's ordering, authorization and recovery behavior, not native object allocation or actual storage.

Swift 6.3.3, x86_64-unknown-windows-msvc, one build job:

```
swift test --package-path .build/portable-t5-authorization --jobs 1 --filter T5NoteCreationFlowTests
```

The four original regressions cover write order, failed source-link recovery without duplicate Note creation, uncertain text-write suppression on retry, and failed native allocation without a fabricated recovery object. The two new test functions cover denied authority before creation and three suspension boundaries (after object creation, after source linking, after source-line writing). All three boundary cases preserve the Note ID, block subsequent writes, and resume without a duplicate Note.

The initial cold compile was terminated by the external SentinelX 60-second timeout before any test started (`job_be31ba8cfda3`). It is retained as INCOMPLETE_TIMEOUT. A single continuation from that build cache completed with exit 0 in `job_8686f92ed6df`; build time 69.28 seconds. This is not a functional failure followed by a retry.

The XCTest compatibility runner prints “Executed 0 tests” before Swift Testing starts. The authoritative result is the later Swift Testing line: 6 tests in 1 suite passed, including the parameterized test's 3 cases. A compiler warning about mutating the test's captured `permitted` variable is retained in the log; the test suite, authorization closure, Task and state changes are MainActor isolated. No production-source warning was emitted in this component build.

## Native proof prepared, not executed

The preserved draft workflow now has a dedicated manual route:

- Dispatcher: `.github/workflows/torah-inspector-ipados27.yml`
- Route: `t5-coverage-proof`
- First component: `native-index`
- Other bounded components: `projection-cache`, `native-rpc`
- Source fixture revision: `947fbde24d5657d0e1229f45bb3993648884a8a1`
- Heart revision: `d98420b1113536afd08cde6de9a5816f6d27ffff`
- r15 patch SHA-256: `5a0906158569d47642d9fc978932cdf254550a31c864a1fb34bd1f8e4e7c10f2`

The controller requires an exact GitHub run/attempt/source identity, fresh evidence, immutable input hashes, expected native test names and counts, no skips, and a disabled client capability. Even a future PASS would prove only the selected native source component, not packaged old/new binaries or Swift/UI/physical acceptance.

The manager has already incorporated the four CI files into the root working tree as source copies and added runtime restoration wiring there. Do not blindly reapply the complete patch or overwrite that dispatcher. Integrate the host anchor and five-file follow-up separately after the required Git authorization.

## Acceptance still open

- R01: full native Page/Note/custom-type results and exact canonical/provider isolation in the active Space.
- R02: real block-only and source-quote discovery, exact-block navigation, and actual r14/r15 compatibility/reopen/old-new process evidence before enabling the feature.
- R03/R04: native Note self-association and unlink-not-delete, archive/delete/type/save/relaunch/index freshness.
- R06: real current-Space, revoked permission, private/deleted/hidden isolation; pre-dispatch host checks alone do not establish native enforcement.
- R07: real loading/error/offline/retry/pagination and lifecycle behavior.
- R08/R09: Apple app compilation and host test execution, actual Inspector UI, RTL/accessibility/appearance/compact layouts, and physical iPad.
- T2 remains blocked on a concrete independently runnable two-client implementation and real conflict/transport evidence. No T2 engine, protobuf, CRDT or unrelated sync work was changed.

## Evidence

- `handoff.json`: revisions, patch hashes and exact follow-up file hashes.
- `followup.patch`: uncommitted five-file change against 56be32bd.
- `complete-t5.patch`: complete T5 change against 5f023e9d, supplied for review only.
- `component.json`, `component.log`: initial cold compile and external timeout.
- `component-complete.json`, `component-complete.log`: completed actual component build/test and immutable source hashes.
- `portable-Package.swift`, `run-component.py`, `resume-component.py`: reproducible component setup and execution.
- `swift-parse.log`, `ci-controls.log`: actual parse and CI-control verification outputs.

Old producer, coverage, integrated and unrelated Hanlin/Otzaria worktrees were left untouched. No live user Space or account data was changed.
