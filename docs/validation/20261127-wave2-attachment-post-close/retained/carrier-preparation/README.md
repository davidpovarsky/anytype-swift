# Live-authorized attachment receipt carrier — isolated source preparation

This two-file candidate is not published, UI-wired, compiled or executed. It covers only the contract-independent process-local carrier. The simultaneous cancellation/close recovery gap remains open pending Wave 1's answer to HQ51 `1220959686858131`; neither original-creator retention nor post-close token export is implemented here.

The exact preimage is App `af63f6209c38bddf6ed851f0b894e2f627a671af`. Building this candidate requires the actual Host source `063d3ef0b16392f67e5044faa81cf8689a75dab2`, including its opaque receipt type. The current preimage alone is not a matching build. No Host, Engine, Root, Document, presentation UI, durable format, project, package, controller, admission, or timeout file is changed.

## Product scope

`AnyNativeAttachmentIntentStore` is already the one actor lazily owned by the existing account/Space `AnyNativeLibraryRecovery`. The added in-memory dictionary holds at most 128 original opaque receipts and exact encoded intents. It never evicts or replaces an unresolved receipt.

- `retainRecoveryReceipt(for:from:authorizeRead:claim:)` requires the current claim and matching durable pending intent before invoking the real original Host API. That API validates scope and current read authority and mints the token. After its awaited checks, the store rechecks cancellation, the exact claim, durable pending intent and capacity before insertion. No creator reference is retained.
- `recoveryReceipt(for:claim:)` returns a token only under the current claim and matching pending intent. The token grants no authority: use still requires the current Host's unchanged original-reservation, current-read, metadata and content validation.
- `consumeRecoveryReceipt(for:claim:)` is for a caller that has just received the current Host's verified result. It preserves the durable pending intent. The final complete UI successor must place this call only at that confirmed boundary.
- Existing verified caller-intent removal clears its matching volatile entry only after the original durable CAS removal succeeds. Normal claim release, cancellation, error or missing journal record does not clear it.

The private Codable record and the entire `AnyAttachmentIntentFiles` suffix are byte-identical. `source-inverse.json` records the three exact store insertions and complete inverse. The only new retained data is process-local; there is no receipt encoding, guessed file ID, URL, plaintext copy, new journal or POST fallback.

## New focused test scope

The complete original 8,725-byte test file remains an exact prefix: three methods/four declared cases unchanged. One appended suite adds four methods/four declared cases:

| Method | Boundary exercised |
| --- | --- |
| `originalOpaqueReceiptSurvivesClaimReopenWithoutEnteringDurableJSON` | No capture without pending JSON; genuine Host token minted while original owner is live; claim release/reacquisition; original modeled journal close/reopen after export; current Host verifies the token with no second upload; explicit consumption; a new caller store has no volatile token; JSON stays exact. |
| `currentClaimExactIntentAndFreshHostAuthorityRemainRequired` | Stale claim insertion/read/consumption; canonical-equivalent but byte-different intent; foreign account/Space/object; wrong Host workspace; revoked export and revoked token use; preserved original entry. |
| `claimRetirementDuringHostAuthorizationCannotInsertALateToken` | The original Host authorization suspends; claim retires and is reacquired; late insertion fails; current retry succeeds. The owned task has bounded start observation and is released/cancelled/awaited on failure. |
| `fullPendingCapacityPreservesAllOpaqueReceiptsWithoutEviction` | Fills the actual existing 128 pending-record capacity with genuine Host-minted tokens; refuses the 129th caller request before another upload; all 128 tokens remain; verified caller removal does not leak the old token to a new intent. |

The capacity method is one declared case with 128 controlled component replies, not 128 test cases or Native calls. Its Host verifies each prior receipt to release the Host's own 64-slot memory while the caller receipt remains pending, a possible boundary when caller consumption has not completed. The negative 129th admission is the existing on-disk record limit; the new carrier also has its own explicit identical finite bound. The test does not relabel that disk refusal as an execution of the new dictionary's defensive overflow branch.

Tokens are minted by the unchanged real Host class through its existing internal component initializer (`@testable import PinkhaAnyHost`). The fixture supplies a controlled ACK callback, metadata and digest, and models journal state transitions; it cannot establish actual Native transport, Apple protected-journal locks, or UI list reconciliation. No production test seam or token constructor is added. The original suites and their time limits are unchanged; only the new suite has its own two-minute bound.

## Evidence status

Source generation, exact full inverse, original test-prefix preservation and filesystem/Codable-record byte comparisons were performed locally. Swift syntax/typechecking, four new methods, old methods, Native HTTP, Apple, UI, cancellation-close and final shared-product admission are **NOT RUN**. Existing Wave 1 35-method/Native2 and Wave 2 Host2 evidence are untouched and not replayed.
