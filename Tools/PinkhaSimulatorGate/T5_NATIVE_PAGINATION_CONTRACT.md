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
