# Hanlin message save: original-scope preparation and progress

Status: **SOURCE_ONLY_NOT_COMPILED_OR_EXECUTED**. No save tool is advertised.
This tranche adds a strict request plan and the aggregate metadata state needed
by a real save binding. It does not claim native body persistence, filesystem
durability, Markdown conversion, a complete application build or acceptance.

Base branch: `codex/chatgpt-wave15-miniapps-return-20261127` at
`769b676a42123745dc4f6903ac321b474aec7116`. The audited host/native APIs were
read at `e5bc1e78b904475ea5988df88a2cb83134933006`. Existing files are unchanged.

## Input and identity

`PinkhaHanlinSaveMessagePlan` accepts exactly `title` and `markdown` strings for
the `anytype_save_message` / `anytype.host:save-message` route. Title is nonblank
and at most 512 UTF-8 bytes. Markdown is nonempty and at most 65,536 UTF-8 bytes.
The conversion plan permits at most 64 native blocks. Over-limit or unsupported
content must fail before any native effect; no truncation or implicit splitting
is permitted. Original title, Markdown, Unicode normalization and line-ending
bytes remain unchanged in memory.

The plan preserves the original SDK envelope, session, namespace, account,
Space, invocation, run, step, provider-call digest and deadline. Caller arguments
cannot select a destination or existing document. The argument digest is domain
separated and length delimited. Session identity is additionally bound through
canonical encoded bytes, including the engine namespace.

## Aggregate state and original journal

`PinkhaHanlinSaveMessageManifest` contains metadata only: the immutable original
identity, input hashes/byte counts and a complete native conversion-plan hash
with ordered semantic block hashes and explicit expected root and complete-body
readback hashes. Root and block mutation IDs are deterministic. A
relaunch or reconciliation cannot mint a new ID or exchange identical blocks.

`PinkhaHanlinSaveMessageProgress` tracks each effect as pending, dispatched,
uncertain (with an optional retained native reference), or verified. Native
effects dispatch serially. A known root is not a complete body. Unknown or
partial effects cannot return to pending or be dispatched again. Cancellation
closes future dispatch without erasing an already dispatched native result.
Late results may refine only their original references. Complete native body
readback must match the manifest, root, every ordered block reference and the
EXACT expected semantic readback digest before the aggregate becomes ready for
commit. A merely well-formed hash of the wrong title/content/style/hierarchy
cannot mark the root, a block or the complete body as verified.

These are pure value transitions. The existing protected journal owner must
persist them before allowing the next native effect. `ProgressStore` is an
actor protocol for that owner; it is not an independent filesystem journal.
`ProgressRecord` carries canonical, bounded sequence/previous/result digests.
An initial sequence-zero manifest plus contiguous records reconstructs the
state; gaps, reordering, unknown JSON fields, changed identity or changed native
references fail closed. Duplicate identical metadata is a no-op, not another
append or native retry. The 262-event ceiling follows from four monotonic
transitions for each of at most 65 effects, plus dispatch closure and readback.

The final event envelope is bounded to 65,536 bytes. The accepted 64 native
references of up to 256 UTF-8 bytes can expand past 32 KiB through JSON escaping;
the larger bound includes the original root/reference/hash envelope without
truncating a valid readback after native effects. Ordinary events remain subject
to the original protected journal's tighter per-type cap. The store protocol
also requires atomic `closeSaveMessageDispatch(for:)` under the same original
owner; late observations can settle, while dispatch can never reopen.

Required journal integration, owned by the SDK lane:

1. Retain the original generic `PinkhaHanlinWriteJournal` reservation first.
2. Reserve a matching aggregate initial state under that same namespace, file
   lock, data-protection and account-removal/drain owner.
3. Compare the expected canonical state inside the actor; flush each typed event
   before exposing the advanced state. Preserve partial writes as unresolved.
4. Preserve the real known-created-root sidecar before its original lease drains.
5. Record generic `.committed` only after the persisted aggregate validates and
   `isReadyForCommit` is true. Root-only `receive(objectID)` cannot be reused as
   final success. Suppress stale caller/UI delivery while retaining original
   native and journal outcomes.

## Original Markdown seam inspected

Hanlin union `f3afac65296e843ced1f7ddd7a55c2452e90b270` retains Presentation
source from `6a6638c314fe04c481eb0a2e29fbeaaafcbb0908`. Its pinned parser is
`davidpovarsky/hanlin-streaming-markdown` at
`5cbb4b6c950051f98f02a0b0ae56756f5174a9b8`.

The original public `MarkdownParserImpl.parse(text:option:)` returns
`MarkdownParseResult.document`, `sourceText` and `speculativeRewritten`.
The document is the original Swift Markdown AST. `MarkdownRenderable` and its
renderables are internal UI representations, not native persistence APIs.
The parser can preprocess LaTeX and rewrite partial markup/images; a persistence
adapter must explicitly retain or reject those constructs, not silently save
the rewritten display as ordinary text. The original inline renderer displays
both soft and hard breaks as newline and has formatting/link/citation semantics.
The next adapter must map supported AST nodes into native block semantics and
verify their original renderer projection before dispatch.

No native conversion output is fabricated from `AnyHeartInlineProjection`:
that type binds actual original native codec output and is not a general-purpose
constructor for newly authored Markdown.

## Native seams and remaining binding work

Any has original `AnyNativeObjectCreator`, `AnyNativeBlockCreator`, and the
native prepared-migration object/block protocol. Object and block effects are
separate; block text is bounded at 65,536 UTF-8 bytes. The block writer retains
returned IDs and verified readback before its original session lease drains.
`AnyEditorDocumentStore` provides CAS for existing blocks, not an aggregate new
document transaction.

Heart has original `objectCreate` and separate `blockCreate` / `blockPaste`.
The generated `Object.Create.Request` has no body input. Body conversion and
native readback/reconciliation must be implemented with the current native
account owner, not a synthetic MiniApps request or an arbitrary UI closure.
No atomic page-plus-body guarantee is claimed for either engine.

The SDK lane retains ownership of existing router/catalog/UI, shared runner and
protected journal files. This lane owns new save planner, aggregate, conversion,
binding and test files. No engine Go, generated protocol, Wave2 editor or final
integration worktree changes are part of this tranche.

## Verification

`PinkhaHanlinSaveMessageStateTests` adds 23 real Swift XCTest methods against the
production plan/state/record implementations. They cover exact input bytes,
UTF-8 boundaries, strict schema, immutable scope/IDs, root-only incompleteness,
serial effects, pre/post-dispatch cancellation, late original receipts,
uncertain-effect no-retry, conflicting references, complete ordered readback,
canonical event replay, maximum escaped-reference receipt/replay, control-character
reference refusal, and metadata-only retention.

All 23 methods are **NOT_RUN**. No Oracle compiler, Mac build, native operation
or simulator test was started. Mechanical source/diff evidence is recorded
separately and must not be promoted to a Swift compilation or application pass.
