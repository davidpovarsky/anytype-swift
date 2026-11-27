# Hanlin complete-message save — focused runtime handoff

Prepared 2026-11-27 04:35 UTC by the Wave 3 MiniApps/Otzaria lane. This is a source review and an execution specification. **No compiler, native operation, UI test, or Mac command was run for this handoff.** Root owns the build and execution slot; SDK owns the additive DEBUG fixture/driver and shared presentation hook.

## Source admitted for planning

Root reports final source `ba1bf2c2cb5cab20efe5edb2d5522ee48f3a88fb`, incorporating c511, 646, and 78dd. The immutable source reviewed directly is:

| Change | Commit | Scope |
|---|---|---|
| Protected journal and shared Any consent/context | `c5117ccfc031493d7fd32e30d5fb1c00be8acd2a` | Seven Swift files; source review complete, no concrete blocker. |
| Real Any root/body worker and full readback | `646c1d9e283a79cb1e996657041ad489122d1ae2` | Actual original creation lease, one conditional Markdown body operation, full ACK, semantic readback. |
| DEBUG native host factories | `78ddc75fc23e39b96f75b0ed894c0b66152e5173` | Real Any/Heart save factories; ordinary production construction remains create-only. |
| Original conditional body adapter | `2619d5b144b23eb80247df613d5d128aa2efbfb6` | Actual native GET/PUT, opaque version, native ACK and same-version readback. Its earlier engine tests do not qualify this Hanlin consumer. |

The source and 97 authored method names below were fetched at exact 78dd and their Git blobs verified. `selected-source-test-methods.json` is the complete machine-readable inventory, SHA256 `51d8963702f569a730ba317e828665466aa4be9262c548ea751aaec919296c24`. Source enumeration is not compiled test discovery. The current frozen Mac product 8f2/SDK385 does not contain this save source and cannot run this acceptance.

Original source review evidence is `mechanical-source-review.json`, SHA256 `0512fc5e1b4e8ff232d97e7df983e32110386f42ae384fb3049a624d471588ee`: all six immutable preimages, seven postimages and 43 literal inverse hunks match. Journal atomic reservation is `131072 + (4*(n+1)+1)*4096 + 65536 + 65536`; at 64 semantic blocks it is 1,331,200 bytes. Ordered mode remains 1,265,664 bytes. Each full ACK/body event has a 65,536-byte limit; the final canonical progress has a 128KiB limit. The original 64MiB aggregate budget, lock, private files, replay and account-removal owner remain intact. These are source findings, not filesystem execution results.

## One compiled product and the exact hosted prerequisites

Use one newly admitted App/AnytypeTests/complete Stage1 UI product for both engines. Bind its actual frozen source manifest, original producer/controller SHA, assembly/native receipt, actual SDK/package lock closure, exact original UI copy, generated project, actual Swift compiler invocation and retained SwiftFileLists. The selected native sources must include the ten paths below plus the new preparation source when published. The Stage1 source manifest must include the new UI source and actual driver/hook definitions. Require actual test discovery from the compiled product before constructing any `-only-testing` selection; no missing selector can become a skip or pass.

Every path below is under `AnyTypeTests/Pinkha/`. Run these authored suites once on the admitted Apple product; parameterized case counts come from actual discovery/results. They isolate controlled metadata/fixtures from real native persistence. The two existing cancellation methods specifically protect the shared worker refactor; no unrelated legacy suite is added.

| Suite / file | Source methods | Git blob at 78dd | Qualification supplied by the suite |
|---|---:|---|---|
| `PinkhaHanlinSaveMessageStateTests.swift` | 42 | `bfa3ff9498b444f5c36b3195e4621d9dc8c29f8d` | Canonical state/identity, no retry, ACK completeness, budgets, close/CAS races. |
| `PinkhaHanlinSaveMessageConversionTests.swift` | 15 | `7f6badb5a109239a2d99bffdc02f64617cc2cfbc` | Original completed parser and strict supported semantics; unsupported refusal. |
| `PinkhaHanlinHeartSaveBodyTests.swift` | 10 | `6561e472090e3e9bc767bad8afd67ba141ae8d4e` | Original protobuf value conversion/readback fixtures; not a Heart service run. |
| `AnyHanlinAtomicSaveBodyTests.swift` | 5 | `8d764769f7826792619e979e092381a4a810627d` | Original parser/native value fixtures; one body operation, full actual ACK shape. |
| `AnyHanlinWriteApprovalTests.swift` | 2 | `eef73d270fc2c41adb579b45b433ba7eb5164e30` | Exact immutable typed approval, once-only consumption. |
| `HanlinSaveMessageJournalTests.swift` | 9 | `f3505cefef5ed3d23286c29c730b38a8ebe59421` | Actual protected Apple filesystem, bounded full ACK/body replay and removal. |
| `HanlinSaveMessageWorkerTests.swift` | 5 | `fe53335c850334871c4990368133e7d16f83ac1f` | Controlled real shared worker and original journal, not native document effects. |
| `HanlinSaveMessageRouterTests.swift` | 6 | `ed982eb46b4791fff93094d61daa331d7dd977f2` | Real router with controlled delegates; route/replay/account fences. |
| `HanlinSaveMessageConsentLayoutTests.swift` | 1 | `2dfd8f343d630d8b1a855a851b81046b4fa7632c` | Real UIKit sheet layout, maximum body, two screen sizes. |
| `HanlinHostCancellationTests.swift` | 2 | `85b239fb3cce56b41eb3489b48b7455882e9aa34` | Original worker keeps the native lease until drain, even after receipt/cancellation. |

Total: 97 source methods, all NOT_RUN in this handoff. Required UI/native evidence below cannot be replaced by these controlled tests.

## Concrete published DEBUG entry points

Any: `AnyHanlinPresentation.presentForSaveMessageAcceptance(from:native:documents:client:sourceOwner:conversationID:locale:creation:)` returns the original `PinkhaHanlinChatController`. It supplies the original parser closure and constructs `AnyNativeMarkdownBody` from the exact captured client. Its host is `AnyHanlinHost.makeForSaveMessageAcceptance(native:documents:owner:conversationID:locale:creation:saveServices:)`. Foreign-client and refined-owner checks precede native access installation.

Heart: `PinkhaHanlinReadWriteHost.makeForSaveMessageAcceptance(presenter:routeOwner:conversationID:locale:)`. It retains the original native permission/context, AccountOwner journal and shared worker.

SDK has reserved these NEW names; their source is still being authored and must be published, reviewed and included in the future build:

- `PinkhaHanlinSaveMessageAcceptanceFixture` and `PinkhaHanlinSaveMessageAcceptanceDriver`.
- `HanlinSaveMessageAcceptancePreparationTests.requalifyRetainedNativeSaveFixture()`.
- `HanlinSaveMessageAcceptanceUITests.testOriginalSDKMessageSaveConsentAndNativeReadback()`.
- Shared mounted-editor entry `AnyHanlinPresentation.presentFromNativeEditor(from:native:documents:client:sourceOwner:conversationID:locale:creation:)`, with ordinary behavior unchanged and fresh DEBUG/simulator admission only.

The same new UI selector may run once for each exact engine fixture, with two distinct execution receipts. This is not a claim that either selector is compiled yet. Additional fault selectors remain **NOT_YET_AUTHORED** until their actual barriers and source names are supplied by SDK; the matrix below does not invent runnable method names.

## Custody required before requalifying a retained fixture

Common custody: preserve the original fixture bytes, original creation/preparation receipt, original source/runtime identity and prior result files. A new separate Save fixture receives a new ID, creation timestamp, run/attempt, current compiled-build/assembly/SDK source references and its own absent result path. Keep the old fixture's identity and age unchanged. Require DEBUG + simulator + explicit disposable opt-in; exact simulator UDID, application bundle/App Groups and original container location; a fresh bounded validity window; no production account; middleware/native request-body logging disabled. Account IDs, Space IDs and source references in metadata are observations, not authority. Credentials, managed capabilities and seed material stay in their existing private owner and are never written into public evidence.

Heart requires an actual current original account and Space, local-only server configuration, the original Page type, a mounted original source document and a fresh original Object.Show readback with exact document/Space/body identity. The legacy native driver logs out its account at the end, so its fixture does not prove that an account is currently open. If closed, select/reopen the retained disposable account through its original owner; fail admission if custody is unavailable. Do not create an inferred replacement or mutate the old fixture. Capture current document state as it actually exists after prior selected-text/return tests; do not assume historical body text survived.

Any requires actual saved-account custody plus the live original `AnyApplicationSession`, original workspace account/Space, writer capability, generation and engine-start identity. The same managed original `AnyHTTPClient` must own creator, document store and body adapter; `expectedAccountID` must match actual native auth and the original workspace byte-for-byte. Read the source through the original document store and current lease; bind actual native instance/version and source fingerprint. Do not serialize/reconstruct the per-boot capability from diagnostic data, substitute an uncredentialed client, or start an independent runtime under another account. The current MiniApps A/B isolation scenario has not run; its source does not establish retained A/B accounts. If no independently qualified retained Any account exists, mark this prerequisite missing and let root coordinate creation through the ordinary native flow.

Replacement scenarios additionally need a distinct real account B and independent source root in the same engine, plus an actual account in the other engine. Capture full original scopes and baseline body/native IDs before the pending operation. A saved-account UI suffix is only a selection aid; the actual full selected native account identity must match. Do not copy an existing account database or write it from the fixture controller.

## Real native/UI matrix

All rows are pending. Rows other than the baseline require an actual separately named SDK fault selector before execution. Use original SDK provider transport only to deliver deterministic Markdown into a genuinely completed live assistant message. Record that original session/run/message/part identity; call `admitInlinePresentation(origin)` and the original `AgentSession.executePresentationTool`. A fabricated task UUID, restored message origin, direct router-only dispatch or injected native/tool result cannot satisfy this lane.

| Case | Engines and real action | Required observations and terminal result |
|---|---|---|
| Native consent and complete save | Any and Heart, using the fixed new baseline selector. Cancel the original full-body sheet for one invocation, then allow a separate fresh invocation from a completed live message. Use Hebrew/English, headings, marks, link, supported list and code. | Cancelled invocation has no new root/body effect. Allowed invocation has exact title, actual created root, complete ordered native body IDs and semantics, original account/Space, durable bodyVerified before final receive, and one original result. Any retains its actual full ACK, expected/saved opaque version, normalized native Markdown separately from raw input, and same-version final readback. Heart retains original Object.Create and every Block.Create callback plus actual Object.Show prefix/final readback. Open the actual saved page in the original editor and cold-reopen it without duplicate creation. |
| Declared bounds and unsupported content | Both engines, one valid 65,536-byte body and one unsupported construct; title limit is 512 UTF8 bytes, up to 64 semantic blocks. Exact conversion limits are already controlled above. | Full valid body persists without truncation; original Cancel/Allow stays visible. Unsupported content is refused before any native effect. Do not treat the parser's refusal as successful save, silently flatten unsupported structures, or infer actual native capacity from pure fixtures. |
| Stop before first native effect | Both engines, actual Stop while consent/preparation is pending. | Original cancellation path closes dispatch; no root/body operation; no consumed replacement approval; original worker joins before source/engine owner is released. The UI does not display a success receipt. |
| Stop after known root, before body/next block | Both engines, bounded barrier after original durable known-root (or a verified Heart prefix). | Exact original root/known prefix survives with closed dispatch; zero later body effects after the fence. Known-incomplete remains distinct from success. Reopening metadata or tapping again cannot mint a new root or retry the old body. |
| Dispatched effect and late native receipt | Both engines, actual in-flight native operation, then Stop and release only that original bounded call. | Native work drains in its original namespace; late real IDs/ACK can refine metadata only. No new effect or stale foreground result. A complete late receipt may settle only if actual full body readback and all original authority conditions still qualify; otherwise uncertainty remains. Account/engine owner cannot finish replacing the runtime before the original lease is joined. |
| Engine replacement during pending save | Any→Heart and Heart→Any using ordinary engine selection while the old native worker is pending. | Actual replacement request, invalidation and drain order; no write/journal/receipt in the new engine's scope. At most the already-dispatched original effect can complete. Return to the original engine and read exact known root/prefix without automatic retry; pending request identity remains unchanged. |
| Account replacement during pending save | A→B independently in each engine, using the ordinary account path and distinct real accounts. | Actual full account B selection; B baseline root/body/native IDs remain unchanged. Old authority cannot read/write B, deliver a stale success or acknowledge a replacement scope. Original dispatched work must drain before replacement completes. A metadata refinement is attributed only to A; reopening A does not redispatch. |
| ACK present, complete readback unavailable | Any: obtain actual native ACK, then cause the original post-write readback to fail. Heart: real Block.Create callback followed by unavailable original Object.Show. | Persist the complete actual ACK/known native IDs and original request/version/content digests; full body is not verified and final receive does not occur. No automatic second PUT, Block.Create or replacement page. If the failure occurs only after the adapter's first Markdown readback, label it final semantic readback loss; do not claim the earlier `acknowledgedReadbackUnavailable` branch unless that branch actually occurred. |
| Native effect with lost ACK | Both engines with a real dispatched effect and a controlled loss of its response. | Keep the original operation uncertain. Even an independently observed equal body cannot manufacture the missing ACK or authorize retry. Heart lost Object.Create cannot be reconciled by title; the mutation ID is host correlation, not an asserted native deduplication facility. No invented created ID. |
| Concurrent change / stale source | Any: real competing edit makes original version stale; Heart: actual native edit changes a verified prefix before the next effect. | Any native409 markdown.conflict, no unconditional fallback or second PUT; original created root remains known-incomplete. Heart refuses changed exact prefix/style/hierarchy/IDs before another Block.Create. Do not call the multi-operation Heart sequence atomic. |

For cold/replay checks, retain the same original invocation and journal identity. A new display/session must not take ownership of the old attempt. Read-only inspection under fresh original-scope authority is separate from successful replay; do not invent an automatic recovery API that is absent from the product.

## Fault control constraints and the concrete remaining seam

The original AnyHTTPClient has a private ephemeral URLSession and no public transport injector (blob `c584a72be3fb60b7870ff89630eb26f6fa931986`). A generic URLProtocol fixture must not be assumed to intercept it. The original2619 adapter first obtains/decode-validates the actual PUT ACK and then reads the body; failure of that read yields `acknowledgedReadbackUnavailable`. A postresponse authority failure before ACK decoding yields uncertainty instead. Those two outcomes must stay distinct in evidence.

Fault barriers may delay/cancel a real original effect or revoke real authority; they must not supply a JSON/protobuf ACK, body, version, created ID or receipt. Barriers require bounded release/timeout and must not outlive the invocation. A passive barrier after the actual ACK is durably recorded and before complete semantic readback is useful, but does not prove the adapter's earlier failure branch. Native transport fault work and any changes to the original engine adapter require coordination with its owner. Until a real bounded seam and exact selector are published, the relevant row remains not runnable.

## Original tests retained in their real scope

The original `HanlinNativeAcceptancePreparationTests.prepareRealHostFixture()` and `HanlinNativeAcceptanceUITests.testRealNativeConsentCreatePageAndAuthorityRevocation()` are Heart native read/create/lifetime tests. Their existing driver uses the canonical dispatcher directly and requires its own original <1h fixture. It logs out at the end. The selected-block pair is `HanlinSelectionAcceptancePreparationTests.prepareSelectedBlockFixture()` and `HanlinSelectionAcceptanceUITests.testRealSelectedBlockReadAndReturn()`.

Keep all these files and assertions unchanged. Their old receipts retain the old source scope. If root schedules the focused original create regression for the changed shared host, use its original fresh preparation/test contract in a separate execution receipt; order it so its logout cannot invalidate pending Save fixtures. Do not rerun unrelated navigation/selection cases merely to increase counts, and never label legacy read/create/return as full-message save acceptance.

## Receipts and completion boundary

Each real run must retain actual compiled test enumeration, app/UI/native product and source identities, UDID/OS/device/locale/theme, fixture/requalification receipts, exact selected methods, xcresult/test summaries, original logs, native request/effect counts, immutable invocation origin, journal state transitions/digests, actual native root/body/version/ACK readback, cancellation/drain ordering and before/after foreign-scope reads. Private original response material stays private; public provenance contains hashes and redacted scope references. No timing assertion based only on elapsed sleeps or status labels can substitute for original native completion.

Coalesce iPhone/iPad, Hebrew/English and light/dark observations with the same admitted product. Run the native body/authority matrix once per engine first; repeat device/UI cases only for a concrete layout, lifecycle or performance gate. A physical device remains a separately declared availability/acceptance requirement. Root alone decides the actual slot and final source freeze. Production Save remains absent until both engines' original native body and lifetime requirements pass; successful controlled suites or a baseline UI pass alone do not satisfy that boundary.
