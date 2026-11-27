# Live-authorized attachment receipt recovery — separate UI successor

This is a local source-only successor over fresh primary App `2e312d361f6782ca7365d4bacc1e231b27571cd4`. The three relevant original files match the previously audited `af63f6209c38bddf6ed851f0b894e2f627a671af` byte-for-byte. It requires the published Wave 1 Host contract `063d3ef0b16392f67e5044faa81cf8689a75dab2`. No shared branch, runtime, Native account, compiler, Apple test, or publication has been touched.

## Exact scope

The reviewed carrier precursor is copied unchanged: IntentStore `ff24dab542c153ad6e9dcd87e27f39d7cc2ec0f1e8a6a02f3de43f07ea17fb98` and full tests `c6abeef1c9bfc83e60f364d5a1598d15dfa371642bc7ee1c8d16779fdd78f85f`. Its root review `54ab066174efb6b888b8bbe68b22b354daa4be3afe86b6efcee24f8fade7c309` and independent review `320c84a38b62aeafce8b06ce3cf5c29987a4dd389640d4ae307d214256a4f2e2` remain separate and unchanged.

Only three literal changes are added to the original `AnyNativeAttachments.swift`:

1. Await the existing Host attach call inside an error-preserving catch. If that same task remains uncancelled, attempt to retain a genuine opaque ACK using its original creator and the existing exact `authorizeRead` closure. The Host rechecks cancellation/scope/current authority; the carrier rechecks the claim and original pending intent. A failed retention never masks the original attach failure.
2. The user's existing Check reads a retained token under the same claim/pending intent. If present, it invokes the current creator's published `resume(intent,recoveryReceipt:authorizeRead:)`; otherwise it invokes the original resume overload. Both paths retain original authority and readback. A missing original journal record still reaches the unchanged unresolved/no-resend branch. Other failed recoveries may retain the current creator's genuine token while authority remains live, preserving the first error.
3. Add one nonisolated async helper for that awaited best-effort capture. It creates no Task, journal, creator, process manager, or alternate authority. It explicitly returns immediately for a cancelled task.

After a Host attach/resume returns its verified result, only the volatile carrier is consumed. The durable pending intent remains until the original actual FilesV2 list read, exact returned-file reconciliation, final current lease check, and original outer verified removal complete. A list failure or later cancellation therefore cannot clear the unresolved caller intent. The Host's durable verified record remains the read-only recovery authority when a token has already been consumed.

## Ownership and cancellation ordering

The existing single presentation task owns the whole operation. Its existing native session owns the current lease; `authorizeRead` still validates the lease, mounted document owner, exact current target access, then the owner and lease again. Upload still uses the original one-shot write approval. The existing caller filesystem claim stays held through the awaited capture and every original native/verification action. `withUploadClaim` releases only after those awaits settle; `close()` cancels and awaits the same task. These original function bodies are unchanged.

This successor does not retain an original creator across a retired journal and does not export an ACK after owner retirement. If cancellation/revocation occurs before a live token can be retained, the original unresolved intent stays. Simultaneous close/cancel plus failed durable ACK remains an explicit gap pending Wave 1's response to HQ51 `1220959686858131`; W3's independent source-only response `1220959750821663` identifies the same boundary. Process death still loses all volatile tokens.

## Preservation and validation status

`source-inverse.json` reverses all three new UI changes to the exact original 39,091-byte source. `ui-only.patch` isolates this wiring; `source.patch` also includes the unchanged reviewed carrier/test precursor. `preserved-bodies.json` binds the exact original lifecycle, authority, claim, file reconciliation, fingerprint, error, and View bytes. All original format-1 JSON and protected filesystem bytes remain unchanged through the copied carrier proof.

The four appended carrier methods/four declared cases remain the previously reviewed unexecuted source; no additional UI method or test target is added here. The existing tests exercise the live-authorized carrier/Host API, not this SwiftUI wiring or physical protected-journal reopening. Actual typecheck, carrier test execution, mounted live ACK-failure/Check behavior, Apple journal lifecycle, visual review and matching shared-product admission are **NOT RUN**. No previously accepted Wave 1 or Host2 method was replayed.
