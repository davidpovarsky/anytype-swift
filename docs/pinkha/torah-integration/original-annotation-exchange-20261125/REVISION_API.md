# Closed native revision API checkpoint — 2026-11-25

The original native revision endpoint uses `pinkha.annotation.revision.v1` on the existing typed AnnotationImport/Cancel transport. This checkpoint adds a closed Swift facade around that genuine original operation. It depends on the companion native engine revision implementation; it is not an independently qualified SDK package yet.

## Host contract

Call `account.readOriginalAnnotation(binding:sourceLifetime:maximumBodyBytes:sourceIsCurrent:)` with the actual selected account/Space, a captured existing native root and the current saved local note’s UUID/revision/source witness. The method makes the real locked native read, validates its complete copied response, genuine export and complete mapping, and returns `AnytypeOriginalAnnotationReadReceipt`. It mounts no editable remote controller. The receipt includes the full original native capture, original creation profile, exact native response bytes/hash and a nonconstructible `revisionToken`.

The token is bound to this exact AccountSession reference, the actual original account/Space permissions, the captured Host source lifetime and local UUID/revision/witness. Its public `objectID`, `nativeHeads` and `nativeRootSHA256` are historical data. The opaque root hash is produced by the native engine; Swift never substitutes a differently serialized protobuf or an empty exported log-head dictionary for it.

Prepare the local import attempt using the existing saved-row ledger and create `AnytypeOriginalAnnotationImportSourceLifetime(source:)` from that actual preparation. The source must still be the same UUID, saved revision, source digest, account and Space as the read. `account.prepareAnnotationReplacement(snapshot:revisionToken:sourceLifetime:sourceIsCurrent:onDrained:)` claims this token once and prepares the exact original native request, without dispatching it. The desired snapshot must be the whole saved original body with its adjacent pre-save revision and exact body digest.

`AnytypeOriginalAnnotationRevisionAttempt` exposes these immutable witness fields:

* `source: AnytypeOriginalAnnotationImportSource`
* `objectID: String`
* `expectedNativeHeads: [String]`
* `expectedNativeRootSHA256: String`
* `requestSHA256: String`
* `requestBytes: Data` — exact bounded JSON, including the saved original ZIP; it excludes the private native AttemptSecret.

Persist this complete request/target/token/source witness to the originally captured profile before recording the existing SQLite `dispatch_may_have_occurred` transition. Only the actual still-owned recorded outcome may call `invoke()`. A source-retired or ownership-lost outcome cannot dispatch, even when a history file exists. Do not create a fresh-import replacement on conflict.

The attempt has `invoke() async throws`, `requestCancellation()`, `retire()` and `drainedHistory`. Its original one-use typed Import/Cancel owner retains the real account/source admissions through both native drains. Cancellation or a returned Swift await cannot release that history or prove absence of effects. The retained `onDrained` callback delivers `AnytypeOriginalAnnotationRevisionHistory` even after an awaiting UI task is cancelled.

## History and acceptance

The history retains exact native/cancellation response bytes and copy errors, scheduling/drain facts, optional `nativeApplyAttempted` and `nativeWriteObserved`, `conflictObserved`, and `verifiedNativeReceipt`. Missing or invalid response bytes leave effects unknown. A verified conflict requires the actual matching operation, observed nonempty native heads, root digest and no Apply attempt or observed write. A locally accepted receipt requires native status applied/unchanged, actual completed registration/drain, no native error/cancellation, protocol-specific stage 4, matching request/response hashes, a genuine complete original ZIP/export report and complete original source mapping. Original annotation identity and creation markers remain checked independently.

The immutable success receipt exposes the saved source, stable object ID, resulting native heads/root hash, actual native-write flag, original ZIP hash, response hash/raw bytes and object mappings. It is local original-engine evidence. It is never a remote-device/server acknowledgement or a distributed/global lock. A later remote delivery must be proved by an independently running original peer. Offline concurrent edits still require genuine CRDT convergence and explicit conflict history.

## Verification and remaining qualification

* `job_715a36f04900` passed real Apple Swift typechecking for 11 changed primaries in the full 2,278-source original framework context (arm64 iOS 27 simulator), 13.63 seconds, with every source hash unchanged during execution. This proof precedes the final requestBytes getter and additional post-replacement marker check.
* The final focused attempt `job_15a3f72b8dc7` timed out at 180 seconds. It is not a pass. Server resource diagnosis and the final affected-source typecheck remain open at this checkpoint.
* 13/13 public-contract controls passed with 153 mandatory public requirements and 22 Debug-only requirements. These are explicitly synthetic symbol-graph controls, not a substitute for emitted compiler graph evidence. The four new authority/history types have no public constructor/decoder. The earlier malformed facade-count control failure is retained separately.
* The new Revision.swift file is registered in the actual framework compiler phase. Removing its two new project objects and restoring the two affected additive framework objects exactly reconstructs the prior project bytes. The original app target is unchanged.

The historical cbe25 complete-source continuation and 34b qualification receipts are unchanged. The SDK lane owns explicit admission of this reviewed 21-facade closure, the additional original request-factory delta and the new native engine source/ABI. Structural and final Debug/Release/consumer/ABI/UI acceptance remain pending that new qualification. No original Native66, remote roundtrip, 43-case SQLite or 4,194-case shared SDK evidence is relabelled as proof of this new endpoint.
