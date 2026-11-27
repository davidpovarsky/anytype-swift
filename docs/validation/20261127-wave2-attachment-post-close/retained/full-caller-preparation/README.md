# Original attachment creator recovery — complete caller source preparation

Status: frozen for independent source review. No Swift compilation, component tests, HTTP fixture, Native call, mounted Apple test, publication or runtime admission has been performed for this candidate.

The three candidate files are based on exact shared App source `9b510b5ea80fba508d01314cefb646682943f7a9` (tree `5e473fcc6c5d744fb27e75c402bd4dca35cf9cd1`). Primary GitHub bytes and Git blob identities are retained in the sibling `full-caller-proposal` directory. This parent already contains W1's immutable `063d3ef0b16392f67e5044faa81cf8689a75dab2` attachment recovery API. Both Host files were primary-read and match that dependency. No Host, Engine, Native owner, journal format, project or controller source changes are proposed.

## Why the full successor is needed

The preserved live-only candidate `c63745bb` can capture a real opaque acknowledgement while the original task and authority remain current. Cancellation or owner retirement can prevent that late export even when the real HTTP acknowledgement already populated the original Host actor's private memory. W1's explicit contract answer, HQ story `1220960414985793`, permits retaining that exact original actor and intent before dispatch, then exporting only its remembered acknowledgement under a fresh current same-scope read lease after the actual owner transition. W3 integration is recorded by story `1220960414556727`.

This candidate implements that caller contract in the existing recovery-owned `AnyNativeAttachmentIntentStore`. The older carrier `ff24dab5`, test prefix `c6abeef1`, live UI `c63745bb`, their reviews and all earlier failure evidence remain unchanged. `successor.patch` is the finite extension of those reviewed bytes; `source.patch` includes the complete three-file delta from the actual shared parent.

## Ownership and state transitions

| State | Existing production operation and candidate behavior |
|---|---|
| Selected file, no dispatch | Acquire the original caller filesystem claim, compute the existing fingerprint, save the exact format1 intent durably, then retain the current creator + actual session generation + exact encoded intent before the original Host attach call. |
| Live uncertain acknowledgement | The original awaited best-effort catch may export under its still-current lease. Its first error remains authoritative if capture fails. No separate task or manager is created. |
| Cancelled/closed original sheet | The original close cancels and awaits its task. The caller claim is released only after all nested work settles. The original creator remains process-local in the existing recovery owner; claim release does not clear it. A sheet-only close does not heal a poisoned creation journal. |
| Actual workspace owner retirement | Unchanged Root code revokes/drains the presentation, awaits application close; the workspace owner awaits session revoke/drain before actual protected-journal close. No timeout or synthetic closed boolean substitutes for these completed operations. |
| Same account/Space reopened | Unchanged serialized connect opens the original protected journal, constructs the new current ObjectCreator/session and only then publishes the workspace with the existing recovery owner. Its immutable unique UUID generation and one attachment actor are forwarded together. Session lifetime is monotonic active → revoked → closed; the UUID is not a numeric order counter. |
| User chooses Check | Require the exact current claim and durable original intent, exact UTF8 scope and current creator/generation pairing. Read only the old actor's remembered ACK using the new lease plus original mounted/object ACL callback. Only the current creator calls the existing resume overload. |
| No private ACK | Only the original Host's actual missing-memory `writeUncertain` result may fall through to current journal-only resume. Permission, cancellation, scope, claim and storage failures propagate. A callback that itself throws `writeUncertain` is wrapped privately and rethrown, not mistaken for ACK absence. |
| Current Host verified | The Host has persisted verified state and checked current authority. Clear volatile token/original-creator entries. Keep the durable caller intent until the original FilesV2 reconciliation and final mounted/session checks complete. |
| Missing reservation, rejected lease or process death | Retain the unresolved durable intent and never POST again. Process death loses process-local creator/token memory; only an original ID already recorded durably can then support recovery. |

`owner-transition-source-proof.json` binds fifteen exact declarations to primary source or the finite candidate. This is source reasoning about the existing production route, not an executed lifecycle witness. A different creator alone is insufficient proof of a completed owner transition: the private caller obtains the current pair only from the original serialized owner/journal-open path.

## Carrier invariants

The store holds at most 128 distinct unresolved object/request slots across its token and original-creator maps, consistent with its existing 128-record filesystem bound. It never evicts unresolved entries or replaces an original creator with a new owner. Insertion/access checks the active claim and actual durable encoded intent; both are checked again after every awaited export. A same-generation/different-creator pair and a new-generation/original-creator pair are rejected. Original creators remain until current Host verified consumption or the original verified caller-file removal succeeds.

No opaque token is encoded, reconstructed, logged, accepted as a bare file ID, or stored in format1 JSON. The complete `AnyAttachmentIntentFiles` suffix and private `AnyNativeAttachmentIntentRecord` remain byte-identical to the original. The original claim inode, protected I/O, exact CAS, no-overwrite, permissions and durability behavior remain unchanged.

## Test scope and exact counts

The complete original 8,725-byte test file (three methods/four declared cases) remains an exact prefix. The separately reviewed carrier precursor extends that prefix to 32,593 bytes with four methods/four cases. This successor appends only `AnyNativeAttachmentOriginalCreatorTests`:

| New selector | Declared cases | Actual source path exercised |
|---|---:|---|
| `registeredOriginalCreatorSurvivesDrainedOwnerAndClaimReopen` | 1 | Store registers the original actor before real Host attach callbacks retain the ACK; real session drains, modeled original journal closes/reopens, fresh session/current creator consumes the genuine Host-minted token, verifies original ID/content and performs exactly one upload. Durable caller JSON remains unchanged. |
| `originalPairCannotBeReplacedAndAuthorityErrorsAreNotMissingACK` | 1 | Rejects both creator/generation mismatches and original replacement; proves callback `writeUncertain` propagates; only actual absent ACK returns nil, and absent reservation remains unresolved with zero uploads. |
| `retiredClaimOrCurrentLeaseCannotPublishLateOriginalExport(retireClaim:)` | 2 (`true`, `false`) | Suspends the actual Host export callback, retires/reacquires the caller claim or revokes/drains the real current session, then rejects late publication. Awaited gate cleanup preserves claim ownership through settlement. |

This is three new methods/four declared cases. The combined source file contains ten methods/twelve declared cases; those are not executed counts and do not authorize replay of earlier accepted suites. Each new test uses the existing controlled Host initializer, the actual session/lease implementation, genuine Host-minted opaque tokens, the existing real protected caller intent files, and the already-reviewed modeled journal/native callbacks. There is no public opaque-token constructor or new product test seam.

The modeled journal close/reopen does **not** qualify an actual `AnyProtectedCreationJournal` append failure, a native HTTP server, a mounted view, filesystem journal reopening on Apple, or Native engine recovery. W1's separate Host post-close/cancellation/permission tests and a future genuine mounted caller fixture remain distinct obligations. Compilation and all new tests are `NOT_RUN`.

## Preservation and handoff

`source-inverse.json` contains all literal changes in forward order and the full computed reverse back to all three exact 9b originals. It also proves the complete reverse to the preserved live-only predecessor, exact original/precursor test prefixes, unchanged durable record and full filesystem suffix. `candidate-manifest.json` binds full file bytes, patch, inverse, test inventory and source transition proof.

The original upload/resume, ACL, session, claim-drain, FilesV2 and final result checks remain the authority. No new POST fallback, new journal owner, recovery manager, Native API, opaque-token serialization, profile/timeout change or runtime gate has been introduced. Publication requires the independent reviews and root's separate authorization; W3 retains shared integration ownership.
