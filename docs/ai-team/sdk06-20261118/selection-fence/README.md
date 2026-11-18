# Selection lifetime fence

The real editor publishes every editing-state value through `@Published`. `selectedBlocks` is not updated by every transition, including Done. The host now observes the emitted state synchronously, preserving the current-value emission and comparing ordered UTF-8 identities. Any mismatch permanently revokes both execution and navigation fences. It does not read the manager again from the sink, schedule delivery, debounce, or rearm a fence.

Four new component methods in the existing `HanlinHostAdapterTests` are explicitly required by the SDK source inventory and by actual result matching:

- `nativeSelectionCurrentValueIsCheckedWithoutSkippingFirstEmission`
- `nativeSelectionDoneAndReselectCannotRestoreEitherFence`
- `nativeSelectionChangedOrderAndUnicodeAliasCannotRearmAuthority`
- `nativeSelectionTableAndNonselectionModesUseTheEmittedValue`

The SDK profile now requires 67 methods (32 adapter, 12 write, 17 read/write, 6 consumer). Editor remains a separate profile; integration retains its independent Core profile. The four tests use the same production subscription with real Combine publishers and both one-way fences, covering initial mismatch, A-Done-A, A-B-A, order, UTF-8 aliases, simple-table selection, and nonselection modes. This is component coverage, not a claim of actual native UI gestures.

33 Linux Python controls passed; raw log and hashes are retained. Any mock execution receipts printed inside that log are synthetic controller fixtures. Swift parsing, Apple compilation, these four component methods and the selected-block UI remain NOT_RUN until exact-source Apple execution. Pending SDK63/UI22 runs retain their older immutable source and cannot qualify this delta.
