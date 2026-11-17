# Editor and Properties wave-15 review — 2026-11-17 UTC

## Working tree and scope

Isolated worktree: `C:/Users/DAVID/Code/anytype-swift-chatgpt-editor-20261118`.

Branch: `codex/chatgpt-wave15-editor-20261118`.

Base revision: `5f023e9dc8d33cad7fac73103acd763cdcba8730`.

The restart/handoff documents, Maya typography and Kit reports, repository instructions, upstream integrity policy, design guidance, and the three installed simulator/testing skills were read. Old worktrees remain read-only. No Codex Desktop agent or extra engine was created.

## Properties correction

A source review found that `PinkhaTorahNativePropertyCatalog.nativeProperties(spaceId:)` stored retry failures and then overwrote them with first-attempt failures if the retry returned no rows. A two-line change returns the existing first-attempt fallback at that point. Verified rows remain available, while `lastLookupDiagnostics` retains the actual most recent lookup failure.

The original Anytype property catalog, type/object targeting, duplicate descriptor rejection, and hidden property behavior are unchanged. The already-integrated Add Property typography remains in place.

Validation performed: the actual changed Swift file passed `swiftc -frontend -parse`; the source diff passed `git diff --check`. This is syntax and diff validation only, not Apple typechecking or runtime acceptance. Native retry execution remains unverified. The archived unified patch preserves blank context lines, which a whitespace check over the evidence file reports as formatting.

Patch SHA-256: `4c8f2339ac780006430f77f6e4333fcab94119e6ef0105706ddbf0adc9f9d089`.

Source SHA-256 (Windows working-tree bytes): `b37ab033893975da3c692e10d0c9cb90bc3132c7ed0b0d230d1578130c49467b`.

## Existing implementations retained

- RTL adapter already protects marked text, uses native text alignment/caret behavior, distinguishes automatic from explicit alignment, and preserves existing metadata semantics.
- Quote insertion already calls the native block path with `setFocus: false`; insertion without an existing block uses the direct native block service without requesting the first responder.
- The quote association path already reports partial insertion as uncertain when body insertion succeeds and metadata storage fails.
- The current Stage1 Enter test creates five alternating HE/EN lines in distinct blocks, verifies empty next-block caret/direction, and checks the same block IDs after relaunch.
- Current Properties tests already cover native picker chips, Set membership/relaunch, Page/Note/custom types, canonical linking/unlinking, and hidden/show behavior.

No speculative RTL or quote/drop rewrite was made without a reproduced failure.

## Existing acceptance tests to execute after Home is ready

`PinkhaStage1AcceptanceUITests`:

- `testMultiBlockEnterCreationAndTypingLifecycle`
- `testAppWideDirectionPersistenceAndInteractiveBack`
- `testOriginalPropertiesCanonicalLinkUnlinkAndRelaunchForAllWritingTypes`
- `testNativePropertiesPickerChipsSetMembershipAndRelaunch`
- `testUniversalPageNoteCustomPropertiesAndMixedSet`
- `testRemainingNativeSourceFilterEditing`
- `testRemainingUniversalTypePickersAndMixedSet`
- `testDocumentSourcesEntryOpensExistingSearch`

Native test coverage includes `PinkhaTextDirectionUIKitAdapterTests`, `PinkhaTextDirectionPersistenceTests`, `TorahNativeUIParityTests`, and the production native derived-product pipeline.

The manager owns `AnytypeComprehensiveAcceptanceUITests.swift`; it was not edited. No broad UI matrix was run while Home readiness was unresolved.

Remaining acceptance includes real title/body/trailing-block entry, IME, explicit alignment and Undo/reopen; no-autofocus external copy/internal move and partial failures; property lookup failure with original catalog available; and mounted iPad/iPhone HE/EN interaction. Existing coverage is not evidence that these acceptance cases passed now.

## Handoff

`properties-diagnostics.patch`, `properties-parse.log`, `properties-parse.json`, and `handoff.json` capture the current working-tree change and validation.

The user subsequently explicitly authorized git add, git commit, git push, and integration between the codex/chatgpt-wave15-* branches. Before publication, the current production source hash was rechecked against properties-parse.json and matched. The tasks remain open because full native/UI acceptance is pending.
