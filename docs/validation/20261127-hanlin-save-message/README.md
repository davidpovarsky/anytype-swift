# Hanlin message save: original-scope preparation and progress

Status: **SOURCE_ONLY_NOT_COMPILED_OR_EXECUTED**. No save tool is advertised.
The current source includes the strict request plan, original-parser conversion,
canonical semantic readback, original protected-journal aggregate, and a Heart
body worker using the original native RPC/protobuf APIs. It does not claim that
these new Swift files compile or that a real native body has been saved.

The original plan/state source is `29b0761947099f7961106fbc6d0c738f53cc9573`;
the bounded journal-envelope follow-up is
`7f2fc9fe105357f54ebc2fe3b6bf6c90004faa28`. Their original receipts remain
separate. The current tranche is based on the normal fast-forward of the owned
`codex/chatgpt-wave15-miniapps-return-20261127` branch to the SDK companion
`fe0bb5a7dda6b6d37f8cd61ad7e8ea95e30d1b7c`. That companion contains the
original protected journal, one shared cancellation worker, typed native consent
and an optional save route whose production binding remains absent.

## Input and identity

`PinkhaHanlinSaveMessagePlan` accepts exactly `title` and `markdown` strings for
the `anytype_save_message` / `anytype.host:save-message` route. Title is nonblank
and at most 512 UTF-8 bytes. Markdown is nonempty and at most 65,536 UTF-8 bytes.
The conversion plan permits at most 64 semantic body blocks. Over-limit or unsupported
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

The original protected-journal integration is owned by the SDK lane and is
present in the source companion, with its own NOT_RUN filesystem/worker cases:

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
`PinkhaHanlinOriginalMarkdownSavePlanner` calls that exact original parser with
`speculativeRewrite: false`. It retains the non-Sendable AST within the helper
and returns only the converted Sendable value. The source text must still match
the exact request. `PinkhaHanlinMarkdownSaveConversion` walks that AST, preserving
UTF-16 text ranges and bold, italic, strike, inline code and ordinary HTTP(S) links.
The original `AnyInlineMarkdown` projection verifies complete text and formatting;
it is not used as a substitute parser for the original message.

Supported structure is a flat sequence of paragraphs, headings 1–3, single
paragraph quotes, code blocks, unordered items, ordered items starting at 1, and
checkboxes. Ordered-list restart, nested containers, tables, thematic breaks,
images, HTML, citations, math, unknown nodes, and links requiring normalization or
unqualified schemes are explicitly refused before native effects. Heart code
languages must also be accepted by the original `CodeLanguage` enumeration.
The planner never truncates, splits an over-limit block or flattens an unsupported
structure. The complete semantic document has a 4,096-run bound in addition to
the 64 KiB input/body and 64-block bounds.

No native conversion output is fabricated from `AnyHeartInlineProjection`:
that type binds actual original native codec output and is not a general-purpose
constructor for newly authored Markdown.

## Original Heart body worker

`PinkhaHanlinHeartSaveBody` converts the completed semantic plan through original
`BlockInformation`, `BlockText`, `BlockInformationConverter` and native protobuf
marks. A preflight round trip must preserve every semantic byte and attribute.
The native serialization has its own hash. Each body block carries an immutable
plan/index marker; this is correlation and reconciliation metadata, not a claim
that native `Object.Create` supports deduplication.

`PinkhaHanlinHeartSaveMessageOperation` uses original `objectActionsService`,
`blockService.addFirstBlock/add` and `objectLifecycleService.openForPreview`.
The operations are separate native effects. The actual created ID is durably
retained in aggregate progress and the original known-incomplete sidecar before
the first Object.Show. Every new effect is fenced both before and after its
durable dispatch event. Each prefix is read from actual original protobuf rows;
the entire body is read again before a final receipt. Title, style, marks,
language, hierarchy, order, native IDs, original Space/type, and unexpected rows
are checked. No expected text is copied into an actual-readback witness.

`PinkhaHanlinSaveMessageRunner` uses the single original generic worker and
the companion's one-use full-body approval. Every effect and late original read
revalidates the exact prepared Page type as well as current original authority.
Stop, timeout or authority loss durably closes future dispatch; late original
receipts may settle metadata without reopening it or delivering through another
account. The metadata ledger retries only one exact concurrent close CAS race,
and never retries native effects, unrelated state changes or I/O failures.

The fresh Page precondition is deliberately strict: native header, no body rows.
It does not discard or overwrite a native placeholder paragraph. A real standard
Page may not satisfy this shape; that is an explicit native qualification gate.
An unknown root-create result stays uncertain, with no title-based search or new
object on retry. Final `receive(objectID)` occurs only after durable full-body
verification. No atomic page-plus-body guarantee is claimed.

## Any conditional body mode and required native handoff

Wave 1 owns the original conditional Markdown adapter for
`/v1/spaces/{space}/objects/{object}/editor/editor_blocks/markdown`. Its proposed
contract is a fresh GET with opaque version, one PUT with `ifVersion`, an actual
native ACK, and readback at that saved version. Wave 1 has now published that
primitive as `2619d5b144b23eb80247df613d5d128aa2efbfb6`, with its separate
component and original local native crash/offline evidence. Its accepted source
SHA-256 is `7097c7c5f7bbf67eba21a961986a892064a1833425ff74b053917a0d4e11e4af`.
This source tranche does not yet consume the adapter or transfer that native
acceptance to Hanlin. No per-block Any writer is included or installed.

The aggregate's explicit optional `conditionalMarkdown` mode represents ONE body
effect, not fabricated per-block operations. Its immutable request digest,
expected version digest, real ACK receipt and saved-version digest remain bound
separately from the raw input hash and expected normalized semantic body hash.
The request ID is host correlation, not native deduplication. Lost ACK remains
uncertain even if current Markdown looks equal. Body verification requires the
ACK, same-version readback, all ordered actual native IDs and complete matching
semantics. Opaque versions are not assumed to change on every write.

The absent optional mode/version/state fields retain the original ordered-block
wire shape; authored source tests check omission and canonical replay. The pure
`AnyHanlinSaveMessageReadback` projects an actual bounded original editor snapshot
for semantic fixtures; it is not a qualified replacement for Wave 1's native
ACK/version adapter or an installed Any save binding.

The SDK lane retains ownership of existing router/catalog/UI, shared runner and
protected journal files. This lane owns new save planner, aggregate, conversion,
binding and test files. No engine Go, generated protocol, Wave2 editor or final
integration worktree changes are part of this tranche.

## Verification

`PinkhaHanlinSaveMessageStateTests` now has 36 authored Swift XCTest methods
against the production plan/state/record/ledger implementations. The original
23 methods are retained. They cover exact input bytes,
UTF-8 boundaries, strict schema, immutable scope/IDs, root-only incompleteness,
serial effects, pre/post-dispatch cancellation, late original receipts,
uncertain-effect no-retry, conflicting references, complete ordered readback,
canonical event replay, maximum escaped-reference receipt/replay, control-character
reference refusal, and metadata-only retention. Eight additive methods cover
atomic operation/ACK/version/no-redispatch semantics and legacy optional-field
omission. Five additive methods exercise controlled metadata close conflicts,
unrelated changes, I/O failure and wrong acknowledgements.

`PinkhaHanlinSaveMessageConversionTests` has 15 authored methods using the exact
original parser, production conversion and synthetic Any native-row fixtures.
`PinkhaHanlinHeartSaveBodyTests` has 10 authored methods using the original
parser/converter and synthetic native protobuf fixtures. Their checks include
Hebrew/Unicode, all supported styles, literal code, native mark segmentation,
unsupported structure, wrong body/title/style/order/scope, and refusal to hide
placeholder or orphan content. These fixtures prove no real native operation.

All 61 methods are **NOT_RUN**. No Oracle compiler, Mac build, native operation
or simulator test was started. Mechanical source/diff evidence is recorded
separately and must not be promoted to a Swift compilation or application pass.

Remaining gates are an original Apple compile/test of these exact files and
dependency closure; actual standard Page/header/body shape; native custom-field,
mark and ordered-content preservation; live cancellation/account switch/drain;
consumer integration of the qualified Wave 1 Any atomic adapter and its
normalization contract; and real
both-engine end-to-end body readback. No production save factory or catalog
installation is part of this source milestone.
