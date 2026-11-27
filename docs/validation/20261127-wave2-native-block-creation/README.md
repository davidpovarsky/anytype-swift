# Native Add block — existing typed creation path

This future core tranche adds one shared block catalog to the native document
menu and the existing per-block UIKit menu. The reviewed base is
`8f2c11713fb8a40ae13444104723666ffef68afe`; the current shared App remains frozen.
All six changed source/test files are downstream `PinkhaAnyUI` files.

## Behavior

The document menu offers **Add block**; a block's existing menu offers
**Add block before**. Both use the same catalog, the original native control
surfaces, localized Hebrew/English labels and standard system icons. Existing
Add paragraph actions and their accessibility identifiers remain available.

| Choice | Existing native type | Additional native style |
| --- | --- | --- |
| Text | `paragraph` | None |
| Heading 1 | `heading` | `level: 1` |
| Heading 2 | `heading` | `level: 2` |
| Heading 3 | `heading` | `level: 3` |
| Bulleted list | `list_item` | `ordered: false` |
| Numbered list | `list_item` | `ordered: true`, `number: 1` |
| Checklist | `check_list_item` | `checked: false` |
| Quote | `quote` | None |
| Code | `code` | None |

Every choice retains the existing `pinkhaWritingDirection` and natural
alignment style carrier. A new numbered item starts at one; no existing list
is renumbered. This change creates blocks through the published typed API.
It does not convert existing blocks or change Native/Host contracts.

`addParagraph` delegates to the new closed-kind entry point. The existing
flush, mounted owner/epoch, account/Space lease, authorization, current-writer
capability, protected journal, placement, native readback and focus/reveal
path remain in place. The actual `currentWriterBlockCreate == 1` gate stays in
`AnyNativeBlockCreator`. Unavailable native capabilities continue to fail
through the original error path before a creation dispatch.

Inspector quote insertion retains the exact provider text escaping, direction,
natural alignment, and after-last-visible-block placement. Its only call-site
change is selecting the closed `.quote` kind.

## Source review and component scope

`source-review.json` is the independent Torah lane review of the exact six
source hashes. Root and editor independently checked the same creation guards,
actor/ownership boundaries and quote behavior without executing tests.

`run_component_tests.py` builds three complete, unmodified UI model files
(the new catalog plus the original marker and writing policies) with the
complete original Engine, Host, Integration and Kit dependency packages.
It executes only the two new model methods. No production function is stripped,
stubbed or replaced in that component. The three UI composition files and
menu view require later Apple compilation and are explicitly outside this
Linux component compile.

The actual component receipt, invocation, source closure, resolved package
revisions and complete original logs are retained separately. Its result is
component evidence, not App, native service or UI acceptance. SwiftPM's actual
transitive resolution is recorded rather than assumed identical to an Apple
product's dependency lock.

## Remaining acceptance

The historical Windows creation receipt `4db6c2f7...` reports 16 cases against
binary `4b110906...`; it is not a current native `8ac407e7...` result. Wave1
coordination retains that distinction. Current native styled creation,
Apple compilation, menu interaction, keyboard/focus, save/cold reopen and
visual acceptance remain required on a later shared product.

The original renderer currently assigns every heading level the same `title2`
font and code the ordinary body font. The catalog stores distinct canonical
levels, but this creation tranche does not claim differentiated typography.
That concrete rendering repair is assigned as a separate future commit using
the original Anytype typography components.

No accepted hierarchy-drag case, historical T5 calls, Quote/Note or Topic/Word
journey is replayed by this tranche. The current 19-method NativeUI source and
the separate future 21-method accessibility source remain unchanged.

The compiler stderr and unified source diff are stored as gzip files because
their original whitespace is evidence. binary-evidence-index.json binds both
original and encoded hashes and verifies byte-identical decompression. The first
Git whitespace-check failure is retained in its original encoded output.
