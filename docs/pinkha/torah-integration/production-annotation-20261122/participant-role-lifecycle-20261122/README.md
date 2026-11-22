# Original participant edit role and subscription lifecycle

This isolated component changes the original ParticipantsStorage actor. It does not enable production annotation creation, schema registration, an SDK receipt, an identity mapping writer, body acknowledgement or a new transport. It is not Apple, native engine, Combine, decoder or UI qualification.

## Source boundary

The opaque OriginalParticipantEditPermission is created only in the same original source file from actual decoded Participant records and the original concrete AccountManager lifetime. It validates the exact account source/token and byte-exact Space. The actual original active status and canEdit predicate are used; writer, admin and owner are not replaced by the separate moderator predicate.

The first record for a Space governs selection. Missing/denied/mismatched records cannot be replaced by a later duplicate. Participant ID, identity, Space, permission and status are security-relevant. In particular, owner-to-admin and admin-to-writer retire the earlier capture even though ordinary canEdit remains true: the original legacy-stream rule still requires the owner.

This is only the participant prerequisite. A full Space admission must additionally hold the independently observed original SpaceView lifetime and apply the unchanged native predicate: participantCanEdit && (!isLegacyStream || isOwner). This component never substitutes moderator capability for edit permission.

## Original actor lifecycle

Independent full-source review identified a real reentrancy window: an original startup could be awaiting completion while subscription remained nil; stop could suspend in unsubscribe, and another start could consume the original storage's same-data cached state. The older stop could then cancel the newer consumer without retiring its freshly created capture.

The private actor-owned lifecycle reserves a start attempt before its first await. Stop retires role captures and cancels the consumer before suspension, waits for that exact pending original start to settle, then issues the original unsubscribe once. Duplicate stops join the same teardown. Every start outcome settles its waiter. Only the same active attempt can install or publish a consumer. Failed unsubscribe blocks further starts until an explicit successful stop retry; no cached-state restart silently treats failure as teardown.

The weak-self Task now explicitly awaits the original actor publication. This exact actor hop was independently diagnosed by both the real Apple producer and the first portable compile. Neither the native subscription implementation nor its callback semantics are replaced in product code.

Actual actor deallocation retires both already minted channel-pin and edit-role snapshots and cancels the stored consumer Task. This is passive retirement, not a new RPC or a promise to roll back already-admitted work.

## Actual verification

Three frozen inputs and their full receipts are retained:

| Input | Actual outcome | Scope |
| --- | --- | --- |
| 75428a575873caac9a592c18954c6b476c859381a27111c5ae650fd9447d74ed | Complete-file syntax passed; semantic compile failed on missing actor await. No binary/case executed. | Raw failure retained unchanged. |
| 0f5120fefcafb5763913114142f5ed467a178114d656ca2c01fa40db7c3855ca | Swift 6 portable semantic compilation and 16 new role/lifecycle cases passed. | Only the diagnosed await changed from the earlier input; assertions/dependencies were unchanged. |
| 7fc5fc32d5dd7f21d6133f72511ccc133dea9dbe6bdabcbc9a5e435deffa8da1 | Complete-file syntax, portable semantic compilation and one new actual-actor deallocation case passed. | The six-line deinit addition is the only production delta from 0f. The prior sixteen cases were not replayed. |

The sixteen cases exercise the exact three production helper regions and COMPLETE original actor, the actual original Lifetime/Capture/AccountManager declarations, and original participant value/enum bodies and permission predicates. Portable input and dependency probes replace Factory/Combine/OS lock interfaces, subscription suspension points and already-decoded input values. Native protobuf serialization and the original Participant(details:) decoder are NOT executed. Every such projection and input is listed and hashed.

The deallocation case returns only weak storage plus copied permissions. It observes actual storage destruction, checks both old captures reject while the real AccountManager capture stays current, and observes the live AsyncStream consumer terminate through cancellation. Later input cannot revive the permissions. Its fixture adds only observation counters to the already retained portable publisher.

These are 16 cases on exact 0f plus one newly affected case on exact 7fc, not a claim that seventeen cases were rerun on 7fc. The original eighteen channel-pin cases, fifty-two pure annotation policy cases, Owner/SQLite cases and unrelated gates were not replayed.

No timeout or cleanup occurred in the passing runs. Actual compiler commands, explicit working directories, child PIDs, source-before/after identity, logs, binary digests and result JSON are retained. The issued runner source is archived from the recorded tool input; host upload byte normalization was not separately observed.

## Integration status

The public participant stream still carries the original decoded data for an accepted current subscription. The original channel-pin permission state is byte-identical; the lifecycle fence now protects its delivery as well. The new edit-role entry is internal and does not change the public participant protocol.

The main original-editor producer remains on a separately frozen source. Its one-line actor compiler repair does not itself contain this lifecycle or edit-role component. This isolated branch must be integrated with the original SpaceView prerequisite, real production runtime and strict original schema/readback contract before any production annotation adapter can grant a capability.

An uncertain creation R1 remains a distinct immutable commitment even if local head/source advances to R2 or a tombstone. Future identity recovery must conservatively conflict or revalidate both the immutable creation commitment and a freshly captured current local guard under the real serialized outermost SQLite COMMIT. Identity recovery is not body application or acknowledgement, and this component exposes no identity writer.
