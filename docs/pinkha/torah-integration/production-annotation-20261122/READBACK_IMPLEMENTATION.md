# Isolated original object read adapter

This is the next internal implementation step after the pure recovery proposal at 53392efc0010ac0c75b9c104b51bc144b545eb5e. It is not wired into the public original-editor facade, the canonical envelope, SQLite mapping, ACK, or any production transport.

The adapter binds an existing retained PreparedEditorPageSession only when it has the original external source binding, original BaseDocument, exact object/Space, and original concrete AccountManager. The actual AccountManager generation is captured, and the original BasicUserInfoStorage account ID must match. Both are checked before and after each asynchronous read; the same original Owner validates source/document ownership.

The actual ObjectShow uses the same Owner's exclusive read barrier and native per-RPC Invocation permit. No indexed search, cached provider, qualifier runtime, bootstrap, object creation, or alternate engine is involved. Missing/duplicate root rows, wrong actual object or Space, invalid exact type representation, and archived/deleted state fail. Returned ObjectDetails are raw observations only: they are not an annotation UUID/classification/body proof.

## Required dependencies before identity receipt or mapping writer

1. A genuine established original production account/Space runtime in the consumer. The current Debug Simulator qualification runtime deliberately creates its own disposable account and is not this production authority.
2. A native annotation type outside the three existing registeredDocumentTypes, plus real native relation objects for immutable creation identity. The existing schema1 manifest cannot safely accept silently added JSON fields because older writers drop unknown fields.
3. The consumer's existing namespace/UUID, destination/account/Space, messageID=attemptID, mutationID, exact exchange revision, source.snapshotSHA256, and payloadDigest must be copied without a second envelope codec or hash authority.
4. A separate original body export/readback step. Creation identity or matching metadata must never acknowledge body delivery.
5. A reviewed capability that retains the real Owner and consumes once inside its synchronous operation, containing the original serialized outer SQLite transaction and exact current delivery validation. No await may separate final authority validation and commit.
6. Independent first creators remain a coordination problem: zero index matches do not establish global absence. Existing local durable fences cover same-ledger retries/crashes; neither this reader nor fixed schema-type keys assert distributed annotation uniqueness.

## Original schema capability observed read-only

At canonical Heart d98420b1113536afd08cde6de9a5816f6d27ffff, ObjectCreateRelation uses the supplied relationKey in a native rel- UniqueKey and original derived state. ObjectCreateObjectType honors a supplied ot- UniqueKey. The original codec rejects multiple hyphen separators; future fixed internal schema keys must be delimiter-safe and must be checked through actual native type/relation readback. Names and apiObjectKey are not identity, because their uniqueness check logs failures and continues.

This supported fixed schema-object identity does not apply to ordinary annotation ObjectCreate: that route still creates a native Page tree with an engine-generated object ID. Namespace/UUID are metadata, not an injected Page unique key.

Sources: core/create.go; core/block/object/objectcreator/relation.go, object_type.go, util.go, smartblock.go; core/domain/uniquekey.go. Read Git objects, not the dirty T2 worktree overlay. Root and the consumer agent independently reviewed the scope and conservative recovery constraints.

## Verification boundary

Only source-level admission, syntax and separately identified focused controls may be reported until a real Apple module build and original runtime read actually execute. This file does not claim native identity recovery, body persistence, live transport, mapping insertion, ACK, annotation registration, or cross-account adoption.
