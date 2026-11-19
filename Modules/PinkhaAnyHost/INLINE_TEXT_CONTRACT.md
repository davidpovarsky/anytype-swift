# Native inline text contract

The native editor and Hanlin share `AnyInlineMarkdown` in `PinkhaAnyHost`. The original `PinkhaAnyUI.AnyInlineMarkdown`, `AnyInlineTraits` and `AnyInlineTextError` names remain public aliases. Native text contains inline Markdown; block structure is stored separately.

## Text preservation

The shared projection preserves literal heading/list prefixes, indentation, whitespace, line endings and Unicode bytes. Hanlin exports the supported visible text that the editor displays. Native code blocks bypass Markdown interpretation. Unsupported inline HTML, entities, media, ambiguous emphasis and unsupported code syntax cause an explicit read/edit refusal. Their native source is retained for recovery.

Only newly inserted literal text is escaped. Escaping operates on Unicode scalars: a delimiter followed by a combining mark or variation selector still needs an escape even when Swift treats the pair as one Character. Existing native source is not normalized. Quote provenance and citations remain canonical association metadata; they are not appended to the editable body.

The source-bound regression receipts `../PinkhaAnyEngine/Evidence/inline-projection-regression-v2.json` and `inline-literal-grapheme-regression-v2.json` retain the actual failures before the fixes. The former reproduced five changes to literal prefixes/whitespace under a full-document parser. The latter reproduced four delimiter-plus-combining-mark cases in which visible characters were lost.

## Formatting and UTF-16 selection

`toggling(_:to:)` accepts one of bold, italic, strikethrough or inline code and a nonempty UTF-16 display range. It removes that trait when all selected characters have it; otherwise it applies it. The existing `adding(_:to:)` remains add-only.

Each accepted result preserves exact visible UTF-8 bytes, link destinations, unrelated traits and source outside the affected span. The implementation does not serialize the whole document. Known complete containers can be combined. Partial container crossings in formatting toggles, or whitespace/style splits that the supported grammar cannot represent, remain explicit refusals. Invalid UTF-16 boundaries, including split surrogate pairs, are rejected.

## Replacement across formatting contexts

`replacing(displayRange:withLiteral:)` supports representable selections that cross known formatting or link containers. Its single-context path remains intact. The crossing path expands only to affected known container boundaries, reconstructs that original source fragment byte for byte, and edits its ordered raw leaf spans. The reconstruction check rejects invisible or unknown structure rather than guessing.

Surviving source text is copied exactly. Replacement text inherits the first selected run's traits and link, matching the existing within-style insertion rule. Original wrapper and link destination bytes are retained wherever representable; bounded equivalent emphasis delimiters are considered only inside the affected fragment. The candidate must match the intended visible UTF-8 bytes and complete per-UTF-16 trait/link map before it is accepted.

For example, replacing the visible range `b c` in `**ab** cd` with `Z` produces `**aZ**d`: the remaining `a` and inserted `Z` are bold, and the untouched `d` remains plain. Replacing part of a linked label preserves the exact destination, including its percent-escape and query bytes. `sourceRange(for:)` retains its stricter contract; callers must use the replacement operation for supported crossings.

## Evidence and remaining boundary

The final exact-source codec/alias component run executed **33 tests with zero failures**, source stable: `../PinkhaAnyEngine/Evidence/inline-cross-context-components-20261119-201708.json`. It includes eight existing cases, fifteen toggle/literal cases, and ten crossing-replacement cases. The earlier failed golden expectation and the earlier 22-test extraction runs remain retained.

These component tests compile the actual Host codec and actual AnyUI public aliases as separate modules. They do not prove the complete UIKit editor, native app, or engine executed. The fresh Hanlin renderer and shared codec also passed all 13 unchanged XCTest methods: `../PinkhaAnyHanlin/Evidence/inline-render-components-v5.json`. That direct component build excluded cached Hanlin implementation objects and recorded stable hashes for every cached dependency. It does not replace the complete Apple package/UI gate. The earlier SwiftPM setup attempt executed no tests; a missing test-framework path and a later disk-exhaustion harness failure are retained separately.

The original attributed-string model can represent selections that the supported Markdown grammar cannot express exactly. Examples include retaining styled boundary whitespace after certain deletions, and some partially overlapping formatting-toggle ranges. These cases still fail explicitly without modifying source. The tested restoration covers the documented supported grammar; it does not claim unrestricted attributed-string parity.
