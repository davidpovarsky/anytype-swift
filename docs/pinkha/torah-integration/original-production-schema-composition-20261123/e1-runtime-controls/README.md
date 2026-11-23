# E1 — immutable original-runtime deployment and defaults isolation

## Status and exact scope

This packet is source preparation for the original Anytype editor in an external host. It does not start the original wallet, account services, middleware, UI or native import. It changes exactly four product paths from base `642a8b9cd9cd243e820db154ea2471b6882e2a94`:

- `Modules/AnytypeCore/AnytypeCore/Utils/OriginalRuntimeEnvironment.swift` (new).
- `Modules/AnytypeCore/AnytypeCore/Utils/TargetsConstants.swift`.
- `Modules/AnytypeCore/AnytypeCore/Utils/UserDefaultWrapper/UserDefaultByAppGroupStorage.swift`.
- `Modules/AnytypeCore/AnytypeCore/Utils/UserDefaultWrapper/UserDefaultStorage.swift`.

The previously reviewed original Host and captured-selection implementation, the five authentic generated schema outputs, native Lib pin, host application project and all workflows are unchanged. This source does not inherit the pending retained signed-consumer SDK runtime result.

The three original source preimages also match the retained original SDK product at `de63125b97cd5b91a1fa4f4b71d03738076e735f`. Their narrow changes are necessary because the actual original wrappers resolve and cache their stores inside AnytypeCore: a downstream UI wrapper cannot intercept the original initializer's first read or bare-key migration. Source provenance, inverse comparison and exact input/output hashes are in `SOURCE_PROOF.json`.

## Deployment behavior

`OriginalRuntimeEnvironment.configureEmbedded(appGroup:expectedTarget:)` is deployment configuration. It supplies no authenticated account, selected Space, saved-source capture, write permission or native operation.

One process lock protects one immutable context. Before the first consumer, the same embedded configuration is idempotent and a conflicting configuration throws. The first group, standard-defaults or deployment-mode consumer captures the context permanently. All later installations throw, including an otherwise identical installation.

Without an embedded installation, first use captures the original standalone group: `group.io.anytype.app.dev` for the original debug/nightly target or `group.io.anytype.app` for release Anytype. Original keys, JSON decoding/default behavior, optional removal, group-to-standard lookup/write behavior, standard-to-group migration and the standard wrapper's process-local cache/lock semantics remain intact.

An embedded installation requires an explicitly recognized main-bundle CompilationCondition and a matching **unchanged** CoreEnvironment cached target. It then calls the real Foundation signed app-group container API and requires the returned file URL to resolve to a directory. Creating an optional UserDefaults suite is not substituted for this access check. The installation does not construct a defaults suite or resolve an account service.

Embedded keys use the fixed `AnytypeOriginalEditor.v1.` prefix. Callers cannot supply or replace the namespace. Each wrapper derives and stores its key once from the same captured context. The standard wrapper's **initializer** reads `self.key`, preventing an early unqualified read before later namespaced writes. The group wrapper preserves its original dual-store algorithm but applies it only to the derived key in both stores. It can reuse values already in its own established namespace; it never migrates bare host account/settings keys or another standalone app's account.

The new public read-only `deploymentMode` returns an explicit immutable `.standalone` or `.embeddedEditor` fact from this same context. Reading it is a first consumer and seals the same context. Later original services can choose their scoped deployment policy from this fact, without guessing from a group name or namespace and without using a separate mutable session flag. No E2 service policy changes are included here.

## CoreEnvironment limitation remains explicit

CoreEnvironment itself is byte-for-byte unchanged. A direct early read can therefore cache its original main-bundle target without touching this four-file seam. A cached target mismatch is rejected and is never overwritten. An earlier **matching** direct read is not detected. The control `matching-direct-read-limitation` demonstrates that limitation; it is not described as a global pre-service bootstrap seal.

The later account/session composition still has to establish actual ownership and first-use ordering for original services, middleware registration, resources, Keychain and the host window. This E1 implementation cannot establish that a matching CoreEnvironment target means no original service has previously run. No fifth CoreEnvironment change was introduced.

## Actual verification, with source correspondence

| Evidence | Actual outcome | Scope |
| --- | --- | --- |
| `attempt-1` | Four unprojected product files parsed successfully. The isolated portable compile failed because its initial source closure omitted the original OptionalExtension supplying Optional.isNil. Zero behavior cases ran. | Failure and compiler stderr retained in full. No product repair or fake Optional implementation. |
| `attempt-2` | The authentic unchanged OptionalExtension was added to the closure; Swift 6 compilation and **16/16** behavior controls passed. The unchanged successful parse from attempt 1 was authenticated and reused. | Initial E1 source image SHA256 `1885a2d54b7585a4fd0be81b631c6ea87336bb4b83cdb8e5bb2744dfb8c72264`. |
| `attempt-3-mode` | Updated unprojected syntax and complete portable compilation passed; **4/4 new mode controls** passed. | Final E1 mode API/source image SHA256 `adbd976a8f3a83b792775e04db3bbcf524fd176a2ff4761c639599551453141f`. The original 16 cases were not replayed. |

The final mode-only delta adds the enum, read-only capture accessor, immutable field and two constant constructor arguments. Removing precisely those additions reproduces the exact prior source image; the three original file afterimages are identical across both passing control stages. `MODE_ONLY_DELTA.patch` and `SOURCE_PROOF.json` bind this correspondence. The packet reports 16 retained initial-E1 controls plus 4 actually executed final-mode controls; it does not claim all 20 ran on the final source.

The original 16 cases cover standalone debug/release group/key behavior; real Foundation JSON migration and dual-store writes/removals; embedded first-read/write/removal isolation from bare host account/settings; all three initial consumer paths; idempotent, conflicting, invalid and late installation; missing/invalid main metadata; declared and previously cached target mismatch; the matching early-read limitation; unavailable/non-file/non-directory container responses; original cache/malformed-JSON semantics; and a 24-operation simultaneous installation/first-use race that must produce one coherent group/namespace.

The four added cases cover a first standalone mode read, a first embedded mode read, mode read after an existing standalone standard wrapper, and mode read after an existing embedded group wrapper. They require the same sealed context, original/namespaced keys and late-install rejection.

Both passing control binaries used actual Foundation UserDefaults in unique test-owned suites and actual JSON/default/cache logic, with run-owned temporary directories and cleanup. Each case ran in a new process, so no hidden reset hook was added to production. No real user account data or app defaults domain was used.

### Portable boundary substitutions

The Oracle executor is Linux and cannot call the Apple signed container or OSAllocatedUnfairLock implementation. The source admission records every exact substitution and occurrence count:

- Main-bundle reads use an explicit test metadata model. The original CoreEnvironment cache/switch logic is otherwise retained unchanged.
- The signed-container API response uses an explicit owned-directory/adverse-response model. The final returned URL's file/directory validation still executes through real Foundation.
- Original Apple lock references use a test NSLock-backed implementation. The original standard-wrapper locking/caching statements are unchanged.
- Original standard and group UserDefaults references map to real Foundation stores in unique test-owned suite domains.
- The local AppTarget and Optional extension declarations are exact original source bytes; only unavailable module imports are omitted.

There is no test injection flag, alternate validator or qualification SPI in product source. The complete projected compilands, per-file source hashes and transforms, executed commands, stdout/stderr, case receipts and failure history are retained. The binary files stay in the owned diagnostic directories; their exact SHA256s are recorded.

These controls do **not** qualify signed AppGroup entitlements, the real Apple lock implementation, actual main-bundle metadata, Keychain, UIKit, native ABI linkage, account login/recovery, selected-Space registration, the original editor or any device/runtime acceptance. Those remain genuine later gates. No historical 245/38 source suite or existing Apple producer was rerun for E1.

## Reproduction and rollback

`run_controls.py --repo <isolated-worktree> --output <new-owned-directory>` admits the exact base and source projection and executes the available cases. `--cases` selects bounded cases; `--reuse-syntax-evidence` accepts only an authenticated successful parse with identical affected product hashes. Existing output directories are rejected and nonzero exits are retained.

The exact initial/final driver and initial harness bytes are also retained alongside their run evidence. This makes the original incomplete-closure failure reviewable after the later source-closure and mode additions.

This is an isolated, source-only branch commit with `[skip ci]`; no existing account, host metadata, original framework distribution or production pin is activated. Rollback is limited to reverting this E1 source commit on the owned integration branch. It does not require changing the earlier accepted Host, selection or generated-schema work.
