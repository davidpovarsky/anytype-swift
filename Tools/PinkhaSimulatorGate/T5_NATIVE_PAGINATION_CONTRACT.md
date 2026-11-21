# T5 production native pagination gate

This gate runs one actual Swift Testing method against the production
`AnytypeTorahSpaceRelatedDocumentsService`, backed by the verified r15 native
runtime. Its account and job-owned OS27 simulator are newly created for this
route. The original r14/r15 pair and its UI account, processes and receipts are
not inputs to this route and are never opened or modified.

## Source and execution boundary

The manual dispatcher route is `t5-native-pagination`. It requires the original
successful r15 build run ID through `t5_r15_run_id`. The controller verifies the
original artifact digest, exact native inventory, every framework file and all
three architecture slices using the existing reviewed pair helpers. Application
source, package locks, Kit revision, Hanlin snapshot, build flags and executable
carrier hashes are retained. The test host's installed carriers must match the
packaged build after actual execution.

Only this test build enables `PINKHA_NATIVE_DERIVED` and
`PINKHA_NATIVE_T5_LOOKUP_V1`. The production lookup flag stays OFF. The exact
selected method is:

`AnytypeTests/TorahT5NativePaginationTests/nativePaginationCurrentSpaceAndMutationAcceptance`

One passing method, zero failed methods and zero skipped methods are required
from the original xcresult summary and test tree. Passing Swift assertions alone
does not pass the route: the independent Python validator must accept every
native observation and the public evidence must pass the credential scan.

## Independent fixture and native page evidence

The fixture creates ten real native objects. Seven belong to the current Space
and expose nine exact targets: Page A, Page B, Note, Writing, one block link,
one source quote, and one document with separate document/block/quote targets.
Two additional objects use a different verse or provider. A tenth object in a
second native Space uses the same requested canonical source.

Each target is recorded from the native creation/association operation before
calling the service under test. Canonical v2 bytes, association identities,
native ObjectShow metadata, authority, projection readiness and original block
graphs are retained independently. Expected returned rows are derived from
this inventory and subsequent native readbacks; they are never copied from the
production result or from the service's target collector.

The test registers a recorder around the original `SearchMiddleServiceProtocol`
implementation. It passes the identical `SearchRequest` to that implementation
and returns its unchanged `[ObjectDetails]` result. It records actual filters,
keys, sort, limit, offset, requested Space and result identities. It supplies no
fake records, synthesized pages, pagination offsets or alternate search logic.
The original registration is restored when the test finishes.

The independent membership probe explicitly supplies the same current-Space,
visibility, type and template predicates. The validator requires exactly eight
predicates for the first production page and nine for subsequent pages,
including the accumulated exact-ID exclusion. This makes the proof explicit;
it is not an archival product fix. At pinned Heart
`d98420b1113536afd08cde6de9a5816f6d27ffff`, `core/object.go` routes ObjectSearch
through `SpaceIndex.Query`, `spaceindex/queries.go` calls `database.NewFilters`,
and `database/database.go` injects `isArchived != true` and `isDeleted != true`
when absent. The verified r15 patch
`5a0906158569d47642d9fc978932cdf254550a31c864a1fb34bd1f8e4e7c10f2`
does not alter those defaults. The original pair's index-only archive probe
therefore remains valid under the pinned native contract.

The baseline has page size 2 and four actual ObjectSearch pages for seven
candidates. The validator requires exact exclusion progress and stable ID
sorting, plus independent raw native membership reads before and after each
production query. The candidate-cap case uses `(pageSize:2,candidateLimit:5,
targetLimit:50)`; the target-cap case uses `(2,50,3)` and still visits all seven
candidates. Each must disclose `resultLimitReached` independently.

## Ordered acceptance observations

| Observation | Native state and required result |
|---|---|
| baseline | Seven current-Space candidates, nine exact targets, four pages |
| candidate_cap | Five actual candidates across three pages; exact targets only for those candidates |
| target_cap | All seven candidates across four pages; exactly three most recent/stably ordered targets |
| other_space | Real active-Space switch; only the distinct other-Space object |
| return_to_original | Same production service and original nine targets after the actual switch back |
| note_archive | Native archive readback; Note absent and every other original object retained |
| note_unarchive | Native unarchive readback; original Note target restored |
| page_unlink | Native canonical write removes only Page A records; all unknown canonical fields retained |
| page_restore | Original Page A canonical bytes restored exactly; original target returns |
| block_removed | Native block deletion; original canonical bytes and index candidate remain, exact block is unreachable and excluded |

The original service instance is retained across Space switches and mutations;
the two cap variants have distinct service instances. No explicit host cache
invalidation follows native writes. Exactly two active-Space switches and five
native data mutations are counted: two archive calls, two canonical writes and
one block deletion. Actual native account stop, the subsequent specific
account-not-running response and AppShutdown must complete before the receipt
can be accepted.

## Publication and remaining acceptance

The two disposable credentials are retained only inside private owned work.
Every allowlisted native log/JSON file is scanned for both credentials in UTF-8,
UTF-16LE and UTF-16BE before any native file is copied into public proof. Missing
credentials or a match withhold native output. Raw xcresults, app account data,
unapproved files and private credentials are never uploaded or cached. XCTest
activity logs are moved out of the compilation cache before it is saved.

Every result remains `indexedTargetsOnly` with `indexFreshnessUnverified`.
The final deletion observation additionally requires `staleCandidates`.
This finite fixture proves its explicitly enumerated pagination, identity,
Space and native mutation cases. It does not prove whole-Space index
completeness, two-account ACL revocation, a forced network outage, navigation,
physical-device acceptance, real VoiceOver or the full T5 matrix. These remain
separate, and this route does not enable the product feature.
# Native readback states

The Note fixture's native `name` may be empty. The pinned Heart Note creation
path moves a requested name into a text block; it does not promise a nonempty
`name` detail. Actual original Apple run `44561407476` returned an empty Note
title in both `old-create` and `new-upgrade`. The validator permits an empty
string only for the independently created Note role. Every observed title and
returned row still has to equal that object's original native title exactly;
missing values and substituted display titles fail. The other named fixture
objects still require a nonempty title.

For precisely the `note_archive` observation and precisely the original Note,
the independent readback requires `isArchived`, `isReadonly`, and
`detailsRestricted` to be true and `isDeleted` to remain false. It requires
`projectionReady=false`, an empty projection-state readback, and both projection
versions to have the fixture's missing-value sentinel `-1`. This follows the
actual pinned engine behavior: archived objects are ineligible for projection,
their old local projection fields are removed, and archived objects carry all
write restrictions except deletion. The Note must be absent from both raw
membership reads and production rows; its canonical bytes and block graph must
remain unchanged. After unarchive, and for every other object and stage, the
original writable/READY/version-1 requirements remain mandatory.

Primary source and original evidence:

- [Pinned Heart Note creation and readonly detail injection](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/block/editor/smartblock/detailsinject.go),
  `convertNewObjectLayoutBlocks` and `setRestrictionsDetail`.
- [Pinned Heart archived-object restrictions](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/block/restriction/object.go),
  `baseObjectRestrictions`.
- [Exact r15 source patch](https://github.com/davidpovarsky/anytype-swift/blob/947fbde24d5657d0e1229f45bb3993648884a8a1/docs/pinkha/torah-integration/evidence/native-derived/8494cfb347/approval/revision-15/native-heart-integration.patch),
  SHA256 `5a0906158569d47642d9fc978932cdf254550a31c864a1fb34bd1f8e4e7c10f2`:
  `torah.Project`, `Index.project`, `Index.LocalDetails`, and `injectTorahDetails`.
- [Original Apple pair run](https://github.com/davidpovarsky/anytype-swift/actions/runs/44561407476),
  artifact `14553768522`, ZIP SHA256
  `cb805208478ef178f30098aa2a90be90632da4592fb86d22f6a11aaac634fa23`.

These are source-bound validator corrections. They do not claim that this new
pagination gate has compiled or executed natively, and they do not change the
original Apple pair's strict public-projection preservation invariant.
