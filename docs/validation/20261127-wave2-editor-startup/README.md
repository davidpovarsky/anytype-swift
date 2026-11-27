# Editor startup: exact localized warning continuation

Separate source delta above `782e918ea95731822427495a56598b9b933d8dc7`.
The preceding six Torah lanes remain English-only and their original 13-method
inventory remains unchanged. This delta enables the same test-only startup
contract for the **four original editor UI methods** already selected by the F
consumer; it creates no additional editor method or product behavior.

The original top-level `waitForPinkhaNativeNavigation` Boolean return and
`XCTAssertTrue` remain. Its single editor caller now supplies the test case and
actual fixture Space. The shared helper keeps the same 120-second deadline;
caught errors retain a text attachment and return false. The existing mounted
editor fast path now requires no alert, so an obscuring startup modal cannot
bypass readiness. Original routes, editor identities, editing actions, source
search, Undo/Redo and engine-switch assertions remain intact.

The exact `Warning`/message/Continue/Logout tuple is selected from **one bound App
language**, Hebrew or English. It never accepts whichever language happens to
match. Values are copied from the actual
`Modules/Loc/Sources/Loc/Resources/Auth.xcstrings`, SHA256
`8ee4b81dfe98236853f6ba3949148ca2c2c8ca78aefdaf676c40aa128aa33161`, independently read
in this worktree and by root/editor. Exactly one original alert and exactly two
actions remain mandatory. The no-loaded-account one-button warning and unrelated
alerts remain rejected; Logout is never invoked.

The original Stage1 preparation and `pinkha-stage1-acceptance-state.json` remain
unchanged. The controller-bound raw fixture must contain the same nonempty,
distinct `pinkhaObjectId`, `noteObjectId` and `pageObjectId` as the original UI
environment, in the exact Space. App language must match the admitted selection;
direction must match it, and device language must be opposite. The existing
consumer's real simulator-language readback is still required. UI environment
comparisons alone do not prove actual OS settings. Canonical Properties console
evidence remains empty for the editor lane. No new native echo is claimed.

The four existing editor selectors remain:

- `PinkhaStage1AcceptanceUITests/testAppWideDirectionPersistenceAndInteractiveBack`
- `PinkhaStage1AcceptanceUITests/testMultiBlockEnterCreationAndTypingLifecycle`
- `PinkhaStage1AcceptanceUITests/testDocumentSourcesEntryOpensExistingSearch`
- `PinkhaStage1AcceptanceUITests/testUnifiedEngineSwitchRetainsHeartDocumentAndColdReopen`

Validation is source/portable control only: exact inverse of the three-file
delta restores the first published tranche, and ten Python synthetic control
methods pass (the previous seven plus editor identity/language negative and
positive controls). Swift parser output, if present, is syntax only. No Apple
typecheck, simulator launch, UI run, screenshot acceptance or physical-device
acceptance is claimed. Both 22-method/34-case focus coverage and the actual four
editor UI methods still require the coordinated shared product execution.

The additive F consumer must supply `startup_environment(lane="editor", ...)`
after the same original successful preparation, owned fresh simulator and exact
private fixture read. The common Wave3 product qualifier remains authoritative;
there is no new build or permission to substitute old source/product pins.
Neither T5 nor Page154 warning/continuation code is changed.
