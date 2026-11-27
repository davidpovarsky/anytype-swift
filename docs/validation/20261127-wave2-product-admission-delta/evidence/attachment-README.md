# Native attachment storage status and explicit retry

## Concrete missing behavior

At integrated source `6581508faffa748ca51d97e6ea51ecf6400fef35`, the Attachments panel lists and opens real native files, but presents only the metadata `durable` Boolean and a generic unverified-backup message. It does not consume the already-published `AnyNativeFileDurability` status/retry API. Users cannot distinguish native `inflight` from storage-limit refusal or explicitly request the existing native retry from this panel.

This isolated downstream change adds those interactions to `Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeAttachments.swift`. It retains the current `b9d51cc5…` preimage, including root's stale-row/preview correction `426f17d2…`. There is no Native, Host, file-upload, MiniApps, editor or final-integration-branch change.

## Resulting behavior

Each existing row gains **Check storage status**. It reads only the selected file; it does not poll every row or add an unbounded background queue. The native typed response determines the displayed `durable`, `inflight` or `limited` state. `cached` separately determines local availability. The durable label says that storage was confirmed; it does not infer a network receipt for an inline file. Private `lastErr` is never rendered or logged by this presentation.

A **Retry storage** action is available only after an actual nondurable status was observed and the mounted document can mutate without pending edits. The ordinary native UI buttons use the existing Library's borderless multi-action-row style. Original preview, private download, content comparison, MiniApps handoff and close/drain function bodies remain byte-identical.

The retry action consumes one UI-owned approval at the existing typed API's dispatch boundary. A native HTTP 204 only records that the retry request was acknowledged. A separate native status read supplies any new visible storage state. If that later read fails, the acknowledgement notice remains distinct from the error; stale rows, status and preview are cleared. An uncertain request is never repeated automatically. Refresh/check-status is a separate explicit read; each later retry requires a new user action.

## Scope and authority

The reference is constructed from the existing document's account, Space, object and selected file. `PinkhaAnyEngine.AnyNativeFileReference` is explicitly qualified because the Host package contains a separate same-named migration value. No account or Space override is accepted from a UI argument.

The existing `AnyApplicationSession` supplies the real engine-run lease. Every new status request rechecks that lease, current mounted owner, current listed file and canonical target read authority. The chosen file's existing metadata/content-identity comparison brackets the operation. Retry additionally reads fresh native write authority through the existing `AnyHTTPTorahTargetAccess` and rechecks mounted/canMutate/no-pending-edit immediately before consuming the one-shot approval.

The concrete target-access implementation was read from the same integrated source. It reads `members/me` for active membership and the allowed role, then requests the native canonical target proof for this object, excluding Bin/templates. These checks are existing API behavior; the presentation does not invent a transactional ACL proof or replace native authorization.

One existing presentation task and `busy` guard serialize operations. Synchronous revoke and close clear statuses alongside the original visible rows/preview. The existing close operation cancels and drains that task. Late results require the same active mounted owner and current row before publication. Acknowledgement does not override a later session, metadata or permission failure.

## Source evidence and limits

The target file is downstream-owned, originally introduced by `1705d25f415236610e70db210eacd4790115b583`, and absent from protected baseline `586c98bcc17dee425664224e508fc0e8df277678`. No upstream/Native contract or retention-map entry changes. `changes.diff.json` retains the original diff bytes as Base64, including its context whitespace; `source-inverse.json` retains the exact full-file inverse. The first local packet assembly/preparer is also retained. This evidence encoding leaves the normal Git whitespace gate unchanged. Original sources, prior failed builds and root's `426f` evidence remain preserved.

Torah's independent source review checks actor isolation, one-shot authorization, acknowledgement/late failure semantics and the unchanged original open/close/authorization bodies. The concrete native-access source read and root's UI/scope review are recorded separately. Source review is not compilation or runtime acceptance.

No compiler, cache, XCTest, native call, file upload/retry, simulator, visual check or physical-device operation was performed for this source preparation. The original engine status/retry test source was read, not rerun; its prior results are not promoted to acceptance of this new UI. The next actual shared App must include this exact source before mounted acceptance.

## Required affected acceptance

Use a real owned file fixture coordinated with Wave1 and the one matching product scheduled by Wave3. Keep its actual native scope and receipts; do not substitute a fabricated row or a fixture from a different native source tuple.

1. Read a native limited-but-cached file in the panel: exact status and local availability are visible, content remains accessible, and the read dispatches no retry.
2. Press Retry once: retain one original native POST, its acknowledgement, and the separately returned status. An acknowledgement with a nondurable status must remain visibly nondurable.
3. Retain a native acknowledgement followed by a failed status/metadata read: show the acknowledged request separately, clear stale state, and require an explicit next read. A lost-confirmation/uncertain result must not dispatch a second POST.
4. Change/revoke authority or close the mounted document during the read/retry: retain the original failure, reject the stale row action, and prevent late status publication. A reader may inspect status but cannot schedule retry.
5. Reopen/refresh the same owned document and recheck current status. Verify original file preview, local download and successful MiniApps handoff remain functional.
6. Inspect the resulting real UI and AX at the required Hebrew/English, iPhone/iPad and light/dark cells, including large accessibility text. No current visual or physical-device acceptance is claimed.

Existing accepted hierarchy drag and historical T5 calls are not affected journeys. File creation/upload and broader FilesV2/companion workflows remain separate obligations; this change does not establish them. Rollback is an ordinary revert of this isolated source commit.
