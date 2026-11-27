# Attachment presentation scope repair

A failed attachment-list refresh or file-open readback previously retained the visible rows from the last successful read. Synchronous document revocation cleared the preview but left those rows. The UI could therefore continue showing actions whose current access had not been confirmed.

The isolated Pinkha presentation now clears visible file rows and the preview on list/open failure, synchronous revocation and close. Opening a file also requires an idle presentation and the same content in the current visible list, so a delayed action from an invalidated row cannot start another read. The existing Refresh button performs the next explicit read.

This is a future core repair based on immutable source `c95395aec96214dfabd73d55755baa95689cc6d3`. It does not modify the current `8f2c1171` warm retry. The source file is downstream-owned, introduced by `1705d25f415236610e70db210eacd4790115b583`, and absent from protected baseline `586c98bcc17dee425664224e508fc0e8df277678`; no retention-map entry is changed. The patch retains native routes, authorization, metadata/content checks, successful MiniApps handoff and directory cleanup.

Independent source review by the Wave2 editor found no concrete actor, lifetime, handoff or retry blocker. This is source evidence only. Apple compilation, mounted UI error/retry, scope revocation, native execution, visual inspection and physical-device checks remain **NOT_RUN**. The subsequent owned Apple test must demonstrate failure clearing, refusal of a delayed old-row action, successful explicit refresh and unchanged successful file preview/MiniApps handoff; no existing native file or quota result is relabeled as that UI proof.

`source.diff` retains the exact narrow patch; `source-review.json` binds both source hashes and the validation limits. The original source and prior failed builds remain in their existing Git and artifact history. Rollback is an ordinary revert of this isolated repair.
