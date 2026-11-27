# Original Hanlin save-message protected journal — source milestone

Status: source authored and reviewed; Apple compilation and the new filesystem tests are NOT_RUN. No native document save, body conversion, catalog capability, UI action, physical device, Release, or TestFlight acceptance is asserted here.

## Source closure

The owned SDK branch normally merged frozen shared source `6aab20344fcf1c645d7c96e0b9ec034ef07003a9` into published message UI/cap fix `b24cafef39751b12d49b18d2e8d4b8962c0c257b`. Result `4b3fab3ba1649c7f1665e13d9a69d9bace09a662`, tree `b2990f2010df90427323fd5550777cfdc201de91`, was clean and matched the pre-merge tree; existing sparse configuration was unchanged. The first shared Mac source remains the immutable6aab milestone with SDK385/native8ac.

The sibling's exact original save plan/progress/event contracts `29b0761947099f7961106fbc6d0c738f53cc9573` were normally merged as `6e130d6a46730e3a3ef1a2ef33fd1129455518df`, tree `79d4115b0cc0810ebf8273c72611f18b655b2c12`. The original journal before this patch is blob `829c8e1a2733e06e33298506da50c83e5cba133c`; original known-incomplete-object sidecar is blob `4fb3668590460eed354af117dd06506da2f20156`.

## Behavior

The original `PinkhaHanlinWriteJournal` now implements the sibling's typed progress store. It retains the original namespace directory, exclusive file lock, data-protection policy, 0600 modes, no-follow/exclusive-create writes, original reservation, full flushes, account-removal lifetime and irreversible final receipt. Existing v1 entry bytes and their 16 KiB per-file bound are unchanged.

Each save has one canonical initial manifest and a contiguous, append-only event history. Loading reads sorted records one at a time and validates original reservation identity, canonical encoding, exact sequence, previous/resulting-state hashes, immutable manifest and the original semantic readback expectations. Missing, foreign, reordered, forged or oversized records fail closed without repair, deletion or reinterpretation.

The initial record is bounded to128 KiB; ordinary events to4 KiB and the single complete-body event to32 KiB. Only exact private save filenames receive the larger limits. The owner reserves the entire worst-case event budget, derived from the manifest's at-most64 blocks, before the first effect; retained save budgets cannot exceed64 MiB. These are metadata byte bounds, not native storage or process-memory claims. Loading uses a finite file/byte bound and does not retain event bodies in a second in-memory history.

Root creation/verification alone cannot produce a generic committed receipt. All ordered blocks and the complete semantic body readback must already be durably retained. The generic committed reference must match that exact aggregate root. Reopening independently enforces the same rule, including against a syntactically valid forged root-only committed file.

`closeSaveMessageDispatch(for:)` closes dispatch atomically within this same owner. A late original worker may persist known IDs/readback after close, but cannot start another root or block. A committed complete body remains committed. Known-incomplete-root sidecars must agree byte-for-byte with save progress; both remain metadata, not current-account read/write authority. Explicit account data removal revokes this owner before late operations can write.

## Authored verification

`HanlinSaveMessageJournalTests`:8 methods/12 parameterized cases, NOT_RUN. The fixtures cover required original reservation and namespace; root/block-only commit denial and unchanged v1 bytes; Stop-versus-receipt CAS, cold reopen and no later dispatch; complete late-body reconciliation; missing/changed sequence/digest preservation; forged root-only committed file rejection; cross-sidecar root mismatch; and account removal for both engine namespaces.

These tests use the real protected-file owner under a disposable iOS test directory. They are not native engine writes or document-conversion proof. Existing SDK385 cancellation7-case receipts remain scoped to their exact unchanged source; they do not qualify this new journal or consumer UI.

## Next dependent milestone

Use the same original worker for strict save plans, metadata reservation, synchronous per-effect cancellation authority, atomic dispatch close and final aggregate delivery. The sibling owns new original-parser conversion and native binding files. Keep the save action/catalog absent until supported Markdown converts without loss, actual native body readback matches the manifest, and the shared consumer receives real Apple compile/runtime evidence.
