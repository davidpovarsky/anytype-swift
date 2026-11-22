# V5 original fixed-schema observer — source candidate, not executed

## Exact continuation

V4 and its 133-payload index remain unchanged. This V5 candidate adds only persisted Space metadata/readback to the five-source observer. The strict original source.go is byte-identical to V4 (30481a09de754219aa3e714cab42a5750880f9d835a720e1330de22690262e55); its bounded independent source review remains applicable. No Go build, test, native call or CI dispatch has been performed. Source formatting, inverse patch applicability and whitespace checking are the only executed checks.

The base remains original Heart d98420b1113536afd08cde6de9a5816f6d27ffff; the original pinned Go 1.26.5, go.mod/go.sum, any-sync and any-store identities are unchanged. The exact r14 patch remains retained and unapplied in this review worktree. A future native runtime packet must compose that exact original patch before compilation.

## The concrete V4 gap and V5 boundary

The original ClientSpaceStorage.Id() retains a previously loaded ID; it does not read the current state collection. V4 therefore did not observe a missing or corrupted persisted state row. V5 freezes the retained original StateStorage object and its SettingsId() before taking the ACL lock. These are original memory-only accessors, not initialization or database reads.

Inside the same owned ReadTx as target/archive/full ACL enumeration, V5 invokes that exact retained StateStorage.GetState(tx.Context()). It then opens the already existing state collection, copies the complete encoded row and requires the original private field names and native types: id, a, s are strings and e is binary. Decoded SpaceId/AclId/SettingsId must match the actual frozen Space, actual ACL list ID and retained native settings ID; the header must be nonempty. It does not construct statestorage.New, which can create the collection.

The same transaction obtains the settings root through the original ClientSpaceStorage.TreeRoot(tx.Context(), actualSettingsID), copies its actual raw change and complete encoded root row, and requires its actual ID/tree membership. The entire transaction finishes and propagates Commit/iterator/read failures before any signature verification or ACL-dependent operation.

The copied payload is then passed to the existing exported spacepayloads.ValidateSpaceStorageCreatePayload. This invokes original header CID/signature/replication-key verification, original ACL root CID/author/master-key verification, original settings root CID/signature verification, and original version-specific header/ACL/settings cross-link validation. No custom signed-header algorithm or caller authority is added. Actual current-account identity remains separately governed by the existing retained ACL admission.

### Why actualSettingsID is not a self-comparison

The expected settings ID is frozen from the already loaded original StateStorage.SettingsId() accessor. Its native constructor originally captured the settings identity when the Space storage was loaded; reading a changed row does not overwrite that retained value. The actual persisted root for that ID must verify through the original creation-payload validator. For V1, the signed Space header embeds the exact ACL and settings root payloads. For legacy headers, the original validator instead requires their explicit Space IDs and actual ACL-root link. This is the original version-specific identity contract, not a new field-only assertion.

The current CommonSpace.Description API is deliberately unused. Its original implementation mixes a database read with an ACL lock and further database reads; using it here would undo V4's explicit lock-order correction. No cached settings-object initialization, tree load, repair, schema registration or native write is performed.

### Original V1 compatibility correction

V4 required the decoded ACL root's SpaceId to equal the current Space unconditionally. Original StoragePayloadForSpaceCreateV1 intentionally leaves that root field empty and signs the ACL/settings payloads into the Space header. V5 removes the incorrect unconditional equality. The original version-aware payload validator now establishes that binding; the actual retained ACL RecordBuilder still verifies every persisted ACL record under its exclusive original lock and still requires the root model to be a genuine AclRoot. This is a source-derived compatibility correction, not a claimed executed V4 failure.

## Second snapshot and scope

The second independent owned ReadTx repeats the state decoder, full raw state row and actual settings-root row reads in addition to every V4 target/archive/ACL input. Full encoded bytes are compared, including unrecognized extra fields. An intervening legitimate state-hash update may conservatively yield ChangedWhileReading; no false stable observation is claimed. A missing/mismatched state row or settings root yields typed unavailability/error. Both snapshots release their actual readers before the final native scope capture.

The result remains a bounded historical local observation. It is not a native ensure/create permission, global absence fence, account-lifetime lease, original annotation receipt or delivery ACK. No schema/body/writer/repair functionality is added. V4's complete ACL, graph/counter/order, archive and strict-replay guarantees and limits remain described in the unchanged retained V4 packet.

## Source and review evidence

SOURCE_MANIFEST.json binds the exact five candidate sources, immutable original input blobs and V4 ancestry. V4_TO_V5.patch is the complete bounded delta; CANDIDATE.patch remains relative to original d984. SOURCE_WRITTEN.json records source-only checks. The V4 root inventory and strict independent reviews are retained unchanged in the new review packet, with explicit source-only limits.

The genuine disposable original-runtime controls and pinned runner are being prepared separately. Their source and achievable setup require full root review before any Go execution. New metadata cases cover absent state, mismatched ACL/settings identity, wrong/malformed header, missing settings root and full second-snapshot state/root byte changes; old passed suites are not selected.
