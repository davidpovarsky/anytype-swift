# Native inline text contract

The native editor and Hanlin share `AnyInlineMarkdown` in `PinkhaAnyHost`. The original `PinkhaAnyUI.AnyInlineMarkdown`, `AnyInlineTraits` and `AnyInlineTextError` names remain public aliases. The native text field contains inline Markdown; block structure is stored separately.

## Text preservation

The shared projection preserves literal heading/list prefixes, indentation, whitespace, line endings and Unicode bytes. Hanlin exports the same supported visible text as the editor. Native code blocks bypass Markdown interpretation entirely. Unsupported inline HTML, entities, media, ambiguous emphasis and unsupported code syntax cause an explicit read/edit refusal; they are never silently flattened into a purported plain-text result.

Only newly inserted literal text is escaped. Existing native source is retained. The quote insertion path keeps provenance and citations in their canonical association metadata rather than appending them to the editable body.

A source-bound regression run reproduced the previous full-document parser defect: five literal-prefix/whitespace fixtures changed while a normal formatted Hebrew/link fixture did not. See `../PinkhaAnyEngine/Evidence/inline-projection-regression-v2.json`. A separate regression receipt records the delimiter-plus-combining-mark escaping defect; its scalar-level correction is being validated before the next source checkpoint.

## Formatting and UTF-16 selection

`toggling(_:to:)` accepts one of bold, italic, strikethrough or inline code and a nonempty UTF-16 display range. It removes that trait when all selected characters have it; otherwise it applies it. The existing `adding(_:to:)` remains add-only.

Each accepted result must preserve exact visible UTF-8 bytes, every link destination, all unrelated traits, and source outside the affected span. The implementation does not serialize the whole document. Known complete containers can be combined; a partial container crossing or an unrepresentable whitespace/style split is rejected. Invalid UTF-16 boundaries, including a split surrogate pair, are rejected.

The exact implementation passed 8 existing plus 14 new tests before extraction and passed those same 22 tests through the actual Host-to-AnyUI public aliases. These are isolated component proofs; they do not assert that the complete UIKit editor or native app executed. Their dated receipts remain in `../PinkhaAnyEngine/Evidence/`.

## Open baseline parity boundary

The original attributed-string editor could replace text across different formatting contexts. The current `replacing(displayRange:withLiteral:)` method explicitly refuses those cross-context edits. This is a real remaining editor capability gap. A future range-edit change must preserve every unselected source span and trait and must retain unknown syntax; disabling the refusal or flattening raw Markdown would not close the gap correctly.

The original attributed-string model also supports formatting selections that the currently supported Markdown grammar cannot represent exactly, such as selected style removal that would require retaining styled boundary whitespace. The implementation reports these cases explicitly. The restored toggle therefore establishes lossless toggling for the documented supported grammar, not unrestricted attributed-string parity.
