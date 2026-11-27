# Account startup, Stop and explicit retry — source-only component profile

This packet adds four methods and five actual Swift Testing cases to the existing
`AnyTypeTests/Pinkha/PinkhaBootstrapStateManagerTests.swift`. The complete original
1,954-byte file and both original methods remain an exact prefix. The new suite is
`PinkhaAccountRuntimeTests`; the two old methods are not added to this selection.
No test, compiler, simulator, account operation or candidate-module import has run
for this packet. Runtime readiness is false and every final source/product/native
identity remains unbound.

## Exact new selection

| Method | Cases | Observable requirement |
| --- | ---: | --- |
| `startupStopRetiresOriginalAttemptAndDrainsBeforeReplacement()` | 1 | Original startup attempt retires; remove-data, duplicate Stop and replacement selection are rejected while busy; accepted Stop releases the pending base call and completes after caller cancellation; both real wrapper hold tokens resume exactly once; a later selection can proceed. |
| `queuedPublicationCannotReopenOwnersAfterStop(holdSharing:)` | 2 | `false` holds the incoming Hanlin publication hop until retirement and requires zero open effects. `true` holds Sharing's admitted asynchronous open; its actual task must finish before the first Stop owner close and base logout. |
| `accountReplacementRejectsPendingSelectionAndLateBootstrap()` | 1 | Actual `AccountManager` replacement retires the original capture while WorkspaceOpen is pending; its completion cannot publish workspace/subscription/Bootstrap effects. A fresh same-Space request can proceed. A stale Hook invocation after ready produces no extra work; that observation alone does not isolate the captured-account guard. |
| `cachedSameSpaceFailedBootstrapRetriesOnceWithoutWorkspaceReopen()` | 1 | A finished failure can receive one new explicit claim, concurrent explicit activation cannot overlap it, and a ready claim is reused. WorkspaceOpen, widget preparation and both subscription starts remain single occurrences in original order. |

The Boolean argument collection is literally `[false, true]`. The unchanged
original parser and actual-result argument validator read it directly. There is
no synthetic Swift declaration or fabricated parameter-case receipt.

## Controlled effects and actual implementation

The tests execute the actual v5 `PinkhaHanlinAuthService`, `OriginalAuthAttempt`,
`AccountManager`, `ActiveSpaceManager`, `PinkhaBootstrapHook`, and App/Kit state
claim implementations. Events record externally called effects and their order;
tests do not set or imitate their private lifecycle flags.

Existing Auth and storage/subscription protocols supply the deterministic test
effects. Three minimal DEBUG seams are required because existing production
boundaries intentionally prevent substitutes:

1. The Auth decorator directly owns the shared Hanlin, Sharing, MiniApps and
   engine calls. A per-instance `AcceptanceOwners` value redirects only those
   effects and the account/Bootstrap providers. The ordinary initializer retains
   the original owners. Actual attempt registration, publication task retention,
   same-turn MainActor validation, retirement, stage admissions, Stop cleanup,
   error handling and token release remain in the original actor.
2. ActiveSpace's original Workspace service refuses alternate protocol
   implementations. Its DEBUG initializer injects the existing storage protocols
   and one controlled WorkspaceOpen boundary inside the original binding. The
   concrete original `AccountManager` requirement and every captured identity,
   current-selection, retirement and publication check remain. The fixture does
   not provide an original SpaceView capability and expressly checks that no
   `OriginalActiveSpaceSelection` capability is minted.
3. The static Bootstrap Hook obtains its original state and service from global
   Factory registrations. A DEBUG task-local supplies the same existing protocol
   interfaces for this fixture only. There is no global Factory registration,
   alternate account lifetime, feature-gate override or replaced claim algorithm.

The pinned Factory 2.3.1 source confirms that `Injected.wrappedValue` has an
instance setter. No container registration or singleton replacement is used.
All fixture gates are released on failure, retained test tasks are joined, and
the actual account lifetime is drained before fixture exit. The tests refuse
conflicting native preparation/type-preservation fixture flags. All identifiers
and manifests in these component fixtures are synthetic test data.

These cases do **not** qualify real native AccountSelect/AccountStop, native
transport/delegate shutdown, SpaceView or Participant authority, persistent
account state, SDK execution, dual-engine replacement, application UI, or a
physical device. The fixture's `validateForOperation` calls validate the original
context but do not begin a native dispatch permit or execute a native RPC. Those
requirements remain in the existing acceptance ledger.

## Shared App and finite admission

The selected test path is already one of the fixed 61 native compiler inputs.
The App/AnytypeTests and Stage1 source counts remain 61/10; no PBX, package, SDK,
Native, workflow or historical runner file changes. A separate Native UI product
is not required for these component cases. The App must be newly compiled from
the final reviewed source containing this suffix and all 21 supporting source
identities; an earlier product cannot be relabelled.

`profile.py` binds the complete test source, original prefix, full appended
method bodies and 21 current supporting files. It reuses the existing Core22
loader, original compiler witness, original exact compiled enumeration, original
result validator and original Boolean-case parser. One
`CompilerQualifiedProfile` instance must carry actual enumeration through result
validation. Missing, extra, skipped, repeated or wrong parameter cases remain
failures under those original validators.

`profile_binding.py` is only the finite API bridge. It accepts the existing
admitted loader, command barrier and control checkout; it does not create a
`Consumer`, select a new stage/write namespace or implement process cleanup.
Every compiler witness/recheck requires the existing positive command gate.
The original witness's three bounded read-only Git calls are not permitted after
unresolved process custody. The existing corrected consumer retains its stage
writer, first failure, output preservation and owned cleanup.

The future root-owned integration can supply the returned source contract and
the same lane validator through the original consumer helper interfaces. This
packet supplies no execution route or new runner. It leaves the historical warm
22-method/34-case plus four-UI selection unchanged. Existing bounds remain 180s
for enumeration and 600s for a native suite; the new Swift methods have a 120s
limit and their controlled signal waits are bounded to 20s. Parallel testing must
remain disabled for this selected lane. The exact ten incompatible preparation
flags are fixed to `0` in `profile.json`.

Both profile and binding refuse runtime activation. A flag or receipt cannot
open them; root must review a source successor bound to the actual final
source/SDK/Native/compiler/product tuple. Raw original logs and xcresults and
positive original process closure remain required.

## Source custody

The source packet retains full inverses for all four existing Swift files and
for the finite profile and binding templates. Source retention requires
replacement Git blobs at current map indices 15, 133 and 139, plus one new row
for the changed test file. Its original 586 baseline is the same exact
1,954-byte prefix, so it needs its own mapping (row 145, zero-based index 144).
All other existing metadata remains exact. Root's real complete source-retention
gate must confirm the composed final tree before publication. New tests remain
`NOT_RUN`; static byte, AST and ordinary local diff diagnostics are not compiler
or runtime results.
