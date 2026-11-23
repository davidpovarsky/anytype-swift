# Native-owned local-store witness slice

## Contract

This candidate adds a native storage ownership and lifetime capability issued only by the existing Heart storage service after it creates or opens a real local Space database. It is consumed by a bounded read-only Witness scan. It does not authorize access for an account, session, user, ACL, migration, exporter or destination. It does not establish a whole-Space semantic census or external file-payload completeness.

Native base is 35c169e7a39e3dafc0a1281f56a1fe37fce57533, retaining the previously qualified Witness and local-tree structural census. Only clientstorage.go, storageservice.go and Capture's acquisition boundary change. New production files are owned_snapshot.go and native_capture.go. New controls reside in native_capture_test.go. The original fixture Capture entry point remains fixture-only; the shared bounded reader is an exact extraction with a fixed authority substitution. The existing census continues to refuse this new authority.

## Issuance and public boundary

A successful native CreateSpaceStorage or WaitSpaceStorage registers the concrete native storage handle, exact database instance, private service nonce and increasing generation under the storage-service owner mutex. Callers cannot construct a registered owner, inject storage or inject an acquisition callback. A zero capability refuses acquisition. Generic NewClientStorage wrappers cannot issue a capability.

AcquireWitnessLease is exported on an opaque capability. Its concrete lease has private fields, an allocation self identity and actual registry membership. Go value copies and zero leases cannot reveal its context/storage/binding or cancel, count down or unlock the original. The reviewed production consumer in this slice is CaptureNativeOwned; the API does not enforce that only Witness code can invoke the exported primitive. This is not a security perimeter against arbitrary code in the same process, and an unowned raw storage/database alias is outside the managed close guarantee.

## Lock and lifetime ordering

Acquisition performs a brief owner check, releases the owner mutex, acquires the existing per-Space gate, then rechecks the caller context and actual owner/handle identity before counting the lease. The caller context is rechecked after the gate because a ready select may otherwise choose an available gate despite cancellation.

A registered lease holds that per-Space gate through the entire bounded scan, iterator cleanup, read-transaction cleanup and final owner validation. The final native release validates and removes exactly the registered lease under the owner mutex; it always releases its count, cancellation function and gate once even when the genuine lease was revoked. Repeated genuine Close preserves its recorded outcome. An unregistered or copied lease returns before any side effect.

Handle Close and service Close revoke and cancel under the owner mutex, release that mutex, then wait for the actual outstanding leases to drain. No lease wait or database Close is performed while the owner mutex is held. Registration checks the service closing epoch after opening, so a constructor already in flight cannot publish a handle after shutdown; it closes its unpublished native handle.

Delete uses the existing same-Space gate and rechecks caller cancellation before revoking all same-Space registered handles and following the unchanged directory deletion. Successful backup rename also revokes those handles under the same canonical caller gate. Backup decisions, errors, names, rename and cached backup bookkeeping remain unchanged. This covers direct unusable-storage recovery, uninitialized-store recovery and preserveOrphanWal through their single existing backup helper. Recreate or reopen receives a new generation; detached handles cannot acquire current capabilities.

This gate drains the managed snapshot leases. It is not a global ordinary-writer, file-service, cache, session or whole-Space quiescence barrier.

## Same-database read transaction

CaptureNativeOwned obtains the native lease and invokes the same bounded reader using its derived cancelable context. The reader calls the actual leased storage's AnyStore().ReadTx and uses only that fresh tx.Context() for native collection inventory and row queries.

Pinned any-store v1.0.3 ReadTx creates a new transaction and shadows any ambient transaction context. Therefore an incoming context carrying a foreign transaction is safely rebound, not rejected as a context. A direct un-rebound query on another database is separately rejected by ErrTxOtherInstance. The new control verifies both real behaviors and proves the ambient transaction remains open and usable until its own explicit Commit.

The scan uses no openDb, recovery, ReadDoc, ReadStoreDoc, BuildState, live exporter, index, file resolver, network service or caller callback. Unknown collections and empty collections are preserved by the original bounded scan. Failures return no Witness, including iterator, transaction, final-current or lease-release failures.

The caller deadline governs gate waiting, lease waiting and scan cancellation. Vendor read Commit and parts of database Close use background contexts; this candidate does not claim an end-to-end cleanup deadline beyond the existing vendor behavior.

## Four new controls only

1. TestNativeOwnedSnapshotBindsActualServiceHandle uses actual native service construction and real private databases, verifies unknown/empty retention, refuses generic/zero issuance, distinguishes a direct foreign query from a fresh native read transaction, leaves that foreign transaction usable, and retains the existing census authority refusal.
2. TestNativeOwnedSnapshotCloseRevokesAndDrains holds a real native read transaction and lease, proves copied/zero leases cannot cancel or release it, observes actual handle Close revoke and wait, completes transaction cleanup before the genuine release, and verifies actual database close plus a new reopen generation.
3. TestNativeOwnedSnapshotDeletePreservesLeaseBoundary verifies two actual same-Space database epochs, canceled deletion with a live lease, actual deletion and recreation, and successful backup-rename revocation using a disposable native store whose mandatory changes collection is removed through the native database API.
4. TestNativeOwnedSnapshotShutdownAndCanceledAcquire verifies canceled acquisition and actual service shutdown drain. It then holds a real SQLite write transaction and observes a new native database descriptor from an in-flight reopen. Shutdown wins before registration; the unpublished handle is refused and its descriptors return to the original count.

The descriptor observation is a Linux-only test of a real native lifetime, not a production hook. Test fixture failures or timing failures remain original failures and require review; no automatic retry or fallback is permitted.

The binary may compile existing helper and test files, all included in the frozen input map, but selects exactly these four top-level methods once. Old Witness six methods, hardening two methods, census five methods and Swift dry-run eighteen methods are retained and never selected.

## Build, source and execution admission

The source manifest binds both Git worktrees, all six authored native files and three original-file patch inverses, every retained compiled local source/helper, module metadata, pinned any-store/any-sync source and the resolved Go/C/assembly/embed inputs. Offline dependency enumeration is preserved separately; it is not a build or test.

The controller uses only Python's standard library. Its actual loaded module map and source/physical/Git inputs are recorded before and after. One build uses pinned Go 1.27.4 linux/arm64, the established glibc/CGO profile, GOMAXPROCS=1 and -p=1, with GOPROXY=off, GOSUMDB=off and GOTOOLCHAIN=local. No dependency download, old suite execution, shared cache deletion or source update is permitted. The same binary is then used once for the four selected methods; its source, dependency and binary identities must remain equal.

A fresh build requires at least 2,950,000,000 free bytes. The owned command stops below 2,600,000,000 bytes, preserving the 2,500,000,000-byte reserve. These are sampled capacity guards, not a measured peak allocation guarantee. Original command stdout/stderr, PID/process group, deadline, exit, cleanup and source checks are retained even on failure.

## Private data and public receipts

All stores, keys, native IDs, raw logs and Witness frames remain inside an explicitly private root. Directories admit only exact modes 0700 or inherited-setgid 02700; regular original files use 0600. No group or other permission is allowed. Raw values are never included in public receipts.

Safe output consists only of fixed method names, fixed factual observation keys, booleans, integer counts, hashes and explicit scope flags. The two private Witness frames must match their public safe receipt digests and frame accounting. Raw SQLite stores are not deleted as part of qualification.

Any PASS is limited to the new native owner/lease and read-only local-store slice. hasNativeSourceAdmission, permitsDestinationWrites, semanticIdentityCensusComplete, accountSessionACLAuthorized and filePayloadCoverageComplete remain false.

## Remaining acceptance

A production migration source still requires actual account/session/selected-Space authority, semantic reconstruction of every Object/block/type/property/file identity from an admitted immutable source, complete unknown/unresolved accounting, cryptographic/replay validity where required, and an authoritative whole-Space/file-payload completeness boundary. Live ReadDoc/BuildState cannot substitute for this boundary because those paths may migrate or mutate.

Migration destination writes still require an explicit reviewed mapping and authorization contract, durable idempotent native operations, conflict/loss recovery, and end-to-end count/content/link/metadata verification against that admitted source. The earlier inline-file HTTP/Swift, local process-crash and lost-ack proofs remain valid only for their demonstrated narrow operations.

The separate original D/E/F/SDK acceptance lanes and device gates remain separate: UI journeys/archive/Type/history, Page154 native and mounted composition, coherent Release/Text/Heart scopes, SDK exact selection/executed argument cases, and any physical-device/external-access checks. This native slice cannot close those tasks or establish whole-project acceptance.
