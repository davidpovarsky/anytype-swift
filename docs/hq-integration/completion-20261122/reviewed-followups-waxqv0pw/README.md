# Reviewed original editor followups

This branch integrates four reviewed source packets on `bbd11635598a77d98e7ffcb336fafee9a75eba10`. It changes 26 existing source files. Apply the four packets in the recorded order: History (15), Widgets R2 (4), TypeProperties (7), shake undo (1). History and Widgets share one Settings file.

History uses the original version editor and restoration service through actual source/owner boundaries. Widget actions use independently acquired actual widget documents and the original service delegates. Type property reordering retains the original two RPCs and reserves the existing owner before the asynchronous drop action. Shake undo now uses the existing action handler reservation helper.

The complete patches were read by root and peer reviewers. Their exact existing syntax receipts are retained and bound to final bytes. No passing syntax, portable control, Native test or CI job was rerun for this join. Patch application, final bytes and the resulting Git index are checked when publishing.

This is source integration evidence only. It does not qualify an Apple SDK binary, original editor Native interactions, save/reopen, permission revocation on device, or release acceptance. The independently coordinated producer must incorporate these source bytes deliberately and refresh its immutable source closure before producing the next SDK. Do not replace its current shared branch or discard its newer build/dependency fixes.

The original manifests are preserved as historical artifacts, including their then-pending labels. `JOIN_MANIFEST.json` and the later publication receipt describe the completed join; raw syntax receipts are authoritative for syntax results.
