# Original Save worker: Stop after the durable native root

Status: **source only; Apple compile, fixture provisioning and native execution NOT_RUN**.

This is a separate successor to `eee40593bf2088fbf6168106f9d2c49248d3ce1f`.
The original `680364279e08dc69d7d7eee8f6f13169ea8d0be4` Cancel/Allow baseline
and its original XCTest method are retained. No native artifact, account, SDK
pin, project registration, scheme, compiler option or acceptance result is
changed by this source tranche.

## Actual observation boundary

The original native operation creates one root through its existing engine
adapter. `PinkhaHanlinSaveMessageLedger.observe` first awaits the original
protected store, validates the exact returned canonical state, and only then
notifies the DEBUG simulator observer. There is no await inside the journal's
file lock or append operation. The observer independently reads the actor that
the original account owner supplied to this fixture and requires the same
canonical `rootKnown` state and still-reserved generic entry before holding.

The hold retains the original native worker, and Any retains its original
native lease. It supplies no native result, new ID, success receipt, ACK,
permission or body operation. The original worker receives a diagnostic UUID
only in this explicit fixture scenario. A registration is bound to the actual
SDK session/context, tool run and request digest; the driver additionally
checks the full observed identity and exact title/Markdown hashes. Only one
weak process-local observer can be registered.

XCTest presses the original `hanlin-chat-stop` Composer button. In the same
synchronous call, the driver observes Stop after the real cancellation task is
retained and before any queued MainActor drain continuation can run. An observer
failure can therefore synchronously close and join that exact retained task.
The worker reports a drain observation only **after** appending its actual
continuation to `drainWaiters`. While that native worker is held, the fixture
requires its original journal to be closed and uncertain, with no body
dispatch, and the original UI to remain stopping. Only then is the diagnostic
release control enabled. This control resumes the same held worker; it grants
no authority to dispatch.

The original worker must finish, `AgentSession.cancelCurrentRun()` must return
its actual matching reconciliation-required result, and the actual consumer
task must join. The original actor must then retain the known incomplete root
and an uncertain generic receipt, with every ordered body effect still pending
or Any's atomic operation still absent. The read-only postflight uses:

* **Any:** the captured original session/client/DocumentStore, its real lease,
  a same-version native Markdown/row read, and the actual root record. It
  requires zero rows, empty actual native Markdown, and the original Page title.
* **Heart:** the existing mounted original account/Space/Type checks and a fresh
  original `Object.Show` response decoded by the existing strict native codec.
  It requires the exact known root and zero body rows after the native header.

The result is an **incomplete retained page**, never a successful body save or
rollback claim. The message remains uncertain/unconfirmed, its original request
ID is retained, and the original conversation reconciliation barrier stays set.
Neither this test nor its helper deletes the page, retries it, or writes through
a replacement account.

## Closed fixture and lifetime

The optional scenario `stopAfterDurableRoot` is bound in the fresh preparation
request, its actual mounted receipt, the fixture, and
`PINKHA_HANLIN_SAVE_SCENARIO`. Nil preserves the original baseline encoding.
All existing DEBUG/simulator/disposable, source, PID, native artifact, custody,
account, Space, source revision, runtime generation and age checks remain.
The native account must be separate from the owner's reserved T5 account.

The hold lasts at most 20 seconds, ends at least one second before the original
request deadline, and is admitted only with at least five seconds remaining.
The UI Stop itself must occur before that deadline. A timeout, evidence-write
failure or observer mismatch records failure and revokes through the original
presentation before releasing the worker. Normal owner teardown schedules its
release after the owner's synchronous revocation. The proof and release tasks
are joined; the bounded sleep-only watchdog is cancelled, not explicitly joined.
No observer can manufacture completion of an uncooperative native call; the
finite XCTest wait fails and the original unresolved native drain remains an
unpassed requirement.

Ordinary Debug has no observer and no additional Ledger actor hop without the
exact scenario flags. All instrumentation is excluded from Release. The source
receipt contains literal inverse operations and a narrowly labelled text-only
Release conditional projection; neither is a Swift compiler receipt.

## Exact prospective selection

`PinkhaStage1AcceptanceUITests/HanlinSaveMessageAcceptanceUITests/testOriginalSDKStopAfterDurableRootDrainsWithoutBody`

Run this selector separately for genuine Heart and Any fixtures on the same
qualified future product used by its related acceptance consumers. The original
baseline remains a separate selector and separate fixture. Its 4,459-byte method
is unchanged, SHA-256
`cf979fd9595ba1f9d284239e90f733c05169d1fdd79b3ddf006312d3da6462f6`.

The existing `eee40593` Stage1 source registration already includes this file;
there is no extra PBX or scheme edit. Two new default SwiftPM source files must
appear in actual compiler inputs: `PinkhaHanlinSaveMessageNativeObservation`
in Core and `PinkhaHanlinSaveMessageStopAcceptance` in UI. The module source
inventory becomes 25 Core + 12 AnyHanlin + 19 UI = 56 Swift files. The prior
111 authored hosted methods are unchanged and remain NOT_RUN. Actual discovery
must find both native UI methods; zero discovered/skipped tests do not pass.

The original Composer is `davidpovarsky/hanlin-ai` at canonical `45d5d905`,
`Packages/HanlinPlatform/Sources/HanlinScriptUI/HanlinChatUIComponents.swift`,
blob `11ac73b335fa72e300baf0cda8d467df196972b1`; it is unchanged. This source
does not requalify the shared SDK, original handler, compiled companion or
native `8ac` artifact. In particular, Any's real conditional Markdown route
must be positively admitted by the future native product. Account/engine
replacement and ACK/readback-loss native selectors remain separate unfinished
matrix entries and are not credited by this Stop case.

## Independent source review retained

The original independent review and byte proof are retained byte-for-byte under
`native-stop-independent-review/`. The sealed review admits only these eleven
frozen source files after two cleanup corrections. Its source snapshot and
original failed extraction correction remain alongside the review. The owner
source intake remains unchanged at SHA-256
`9cb2381418435037878971c35c59fab58e1c62a973aa4d77fe8024b23056bec8`.
The publication inventory records the exact reviewed bytes; neither review
constitutes an Apple compile or either engine's runtime acceptance.
