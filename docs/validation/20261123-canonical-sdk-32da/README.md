# Anytype canonical SDK upgrade to 32da9e31 — 2026-11-23

## Result and source boundary

The actual Anytype selected SDK installation and its existing strict `prepare_sdk.py --check` both passed at Hanlin revision `32da9e314e22bbf22391fcf8902302acfbb281e2`. The source-only host upgrade is commit `6b815a06a0f584c70a94cc2f7e3c41170706ec31`, tree `5fa8eebd8ff6d684412818f208e7f1f3285a4cd4`. Its two tracked changes are the immutable lock revision and the corresponding lock Git blob in the existing source-retention map. No Anytype application, native adapter, UI, controller, test selector, permission, runtime or workflow source was changed.

The existing native/UI workflow [45163976036](https://github.com/davidpovarsky/anytype-swift/actions/runs/45163976036) remains bound to host `aefb9740c0ac8d52aa2dbd89d389930851396104` and SDK `d49a4fd4115b8335105d2991bf74ab4d7f6aad2d`. Its checkout and source admission had completed before this later local upgrade. It was still running when this receipt was prepared. No native or UI execution at the new SDK pin is claimed, and no additional CI was dispatched for this upgrade.

## Canonical installation

The unchanged eight products are HanlinHostContracts, HanlinPlatformContracts, HanlinAgentCore, HanlinPersistenceAdapters, HanlinChatCore, HanlinScriptUI, HanlinChatUI and HanlinPresentationKit. They use the same fourteen canonical source directories under `Dependencies/Hanlin`, with no binary targets or managed native runtime targets. The sparse checkout uses the shared canonical installer; there are no copied package forks.

The generated selected `Package.swift` is byte-identical before and after: SHA-256 `518f91d40d3433a88ab6255c252bc2c81fa1e2199dad0322b4136bb7f2d6f20c`. The generated provenance JSON is refreshed from the new aggregate package inputs, so its hash legitimately changes from `bc4259b94a0fbb0774b22287eea64ed6858ab5dda6a868b499ddf0edcc32e5ee` to `d45a4dcd07327cd173902c550ac5818a0c1b9cd6ef95683146c33f26fe956752`. A preliminary receipt assertion incorrectly required both generated files to remain identical and stopped before staging. The canonical install and strict check themselves passed on their first executions; this receipt records the corrected distinction.

The original source markers and the refreshed markers are retained here. Of 546 prior selected source/resource entries, 544 are unchanged, two canonical sources changed, and one original shared source is newly public, yielding 547 selected entries:

- `HanlinAISDKProviderFactory.swift`: repeated endpoint query keys now use the reviewed deterministic value policy instead of trapping.
- `HanlinScriptUIReconciler.swift`: the reviewed duplicate reorder admission correction.
- `HanlinComposerDraft.swift`: the original retained draft object is shared publicly by the SDK.

The atomic registry store and legacy permission-grant modules are outside this selected product closure. Their separate native acceptance is not attributed to this host profile.

## Verification retained without replay

The original source-retention gate passed against baseline `586c98bcc17dee425664224e508fc0e8df277678` and the exact upgraded tree: 5,790 baseline files, 5,692 unchanged and 98 explicitly mapped, with no unreviewed changes or inventory errors. The lock blob is `3953c89787a1d2d11161b7bd104b53d87ab05a18`; only its prior shared-source map entry changed.

All 29 original native-controller source inputs remain byte-identical. The existing strict source-bound verifier passed at the new host commit, executing no controller or product tests. Its 69-method catalog consists of 68 retained original proofs and one method requalified in the preceding observer-budget repair. The separate two-method/five-case timing proof is retained under its existing hash. Nothing here converts prior failure, a missing live-provider run, or an unexecuted new-pin native gate into a pass.

`files.json` seals the original install logs, complete source markers, installation metadata, exact source-retention result, unchanged-controller evidence and commit receipt. The generated installation directories remain ignored; these documents record the verified result without changing source admission.
