# Heart Note writes retain presentation authorization

Status: **frozen source candidate; compilation and all new tests are NOT_RUN**.
Base: `9f0cbdffbda45520124ee1f0b50961641c5c49b1`.

## Concrete source finding

The shared `TorahEditorSession` supplies an authorization closure that binds the
active document epoch, Inspector epoch, selection, cancellation and current
association-editing policy. The Heart Note service checked it before a creation
or unlink phase, then erased its repository to the weaker
`TorahAssociationRepository` protocol and called the overload without that closure.
The related-document service did the same for its unlink operation.

The real `AnytypeTorahAssociationRepository` queues each write and awaits a native
document read. Its existing guarded overload checks the supplied closure again
after that read, immediately before applying and dispatching the canonical write.
Without forwarding, a presentation can retire while the read is suspended and
the old Heart metadata operation can still reach dispatch. This is a source
finding, not a claim of an observed wrong-Space write or a device failure.

## Exact change

Both internal Heart services now require the **existing** snapshot/guarded
repository protocol. Four Note writes and one related-document removal forward
the same original `authorize` value. The latter's parameter adopts the existing
`@escaping TorahAssociationWriteAuthorization` alias required by that repository
method. No new protocol or substitute token check is introduced.

The unchanged native repository remains responsible for serialization, native
target permissions, write dispatch, canonical readback and uncertainty. The
unchanged `T5NoteCreationFlow` retains its original pending Note and partial-phase
behavior. The changes do not delete created text or objects as rollback, change
Note Type selection, change source identity, replace properties infrastructure,
or modify any Native/Host/index/ACL/schema code.

The complete original service files reverse exactly through the eight recorded
literal substitutions (ten occurrences). The source map retains all **145**
entries and changes only the two corresponding replacement blobs. The existing
73,306-byte repository test file is an exact prefix; the tests are appended.

## Focused tests to run once on a matching hosted App

Suite: `TorahNoteRepositoryAuthorityTests` in the existing
`AnyTypeTests/Pinkha/TorahAssociationNativeRepositoryTests.swift` input.

| Method | Declared cases | Actual exercised boundary |
| --- | ---: | --- |
| `noteCreationRejectsRetiredRepositoryDispatch(phase:retirement:)` | 4 | Source-link and origin-link writes, each held inside the real repository read; Inspector close/reopen or same-document deactivation/reactivation |
| `unlinkRejectsRetiredRepositoryDispatch(phase:retirement:)` | 6 | Note source removal, Note origin removal, and related-document removal at that same post-read dispatch boundary, each under both retirements |

These are **two methods and ten declared cases**, not ten executed results.
Each case checks zero additional canonical writes after retirement, exact raw
payload retention at the pause, unchanged current UI message, and a successful
fresh current retry. Earlier completed phases remain intact; creation retries
retain one controlled Note and one source-line call. Unrelated quote records,
semantic-anchor association metadata and unknown payload fields remain exact.
This tests canonical association preservation; it does not claim native marker
rendering, block persistence or physical UI behavior.

The session, Heart services, Note flow, mutation coordinator, canonical codec and
repository are production implementations. The `TorahAssociationNativeStore` is
a controlled in-memory native-store boundary with a non-cooperative suspended
read. The unrelated object/block creation services are controlled protocol
implementations. The observer delegates to the real Note service and only exposes
entered/completed service-call counts and the returned recovery error. On a thrown
test failure, cleanup first deactivates the session, samples the actual entered
count, releases the single held repository read, and waits for those service calls
with the original three-second bound. A cleanup failure is recorded separately;
the original thrown failure is rethrown.

Service completion is not a join of the original unstructured UI task or an
already-entered refresh continuation. On the expected retired path, the original
MainActor service return is followed synchronously by authorization failure and
the session's catch/defer. The successful current retry also waits for the original
open callback at the end of that action. These are the precise observed source
boundaries; there is no new production test hook, copied production flow, HTTP
fixture or runtime controller.

Fixture initialization constructs selection, services, repository, observer and
session as local values, assigns every stored dependency, and only then installs
the weak-self callback. The first fixture draft and both source-review findings
are retained in `review-v1`; they are not compiler or runtime failures.

Creation uses the original pinned Factory `8ca11a7bd1ede031e8e6d7a912bb116e2e43961b`
(resolved branch `2.3.1`) eager `@Injected` mechanism. The exact source shows
`push`/`pop` restoring registrations, options, shared cache and auto-registration
state; both original service registrations use `.shared`, not singleton scope.
Push/register/construct/deferred-pop are synchronous on MainActor, and the test
instance retains its injected controlled services before the first await.
**Select this suite alone.** Its `.serialized` trait does not serialize unrelated
test suites, so it does not by itself authorize mixing global Factory overrides
with other tests.

## Source custody and exclusions

`candidate-manifest.json`, `source-inverse.json`, `source-edits.json`, `source.patch`
and `source-proof.json` bind all changed and relevant unchanged bytes. The parent
inspection is retained in `../quote-note-current`, including primary Git bodies,
the exact-ref App/test caller inventory, the pinned Factory sources, and original
inspection failures. Every concrete initializer in that bounded App/test inventory
already supplies the guarded/snapshot capability. No current-ref completeness
claim is inferred from default-branch search or from the separate failed Modules
inspection.

The first-empty-quote insertion, source-copy preview, old Inspector queued-tap fix,
G04 reader lifetime correction, semantic text byte-equality corrections and new
engine Note adapter remain at their existing source/evidence scopes. Full quote
drop/Undo/focus, controlled partial metadata failure on a mounted editor, precise
destination block display, linked-anchor UI persistence and the broader T3/T4/T6
device criteria remain open. This candidate does not replay or relabel any of the
historical T5 36+9 results, or create a new Native acceptance claim.
