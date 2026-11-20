# Apple37 reviewed consumer branch admission

Before dispatch, root source review found that the original verified Heart installer had a closed branch allowlist containing the earlier Apple16 ref only. The first Apple37 preparation ref was pushed but never dispatched. It is retained unchanged at cd8c6f1ffd6622c12d30358340a842d82aa5620d.

The new reviewed consumer ref is codex/otzaria-original-editor-owned-apple-v2-reviewed-20261120. The only Heart installer change appends this exact ref to the original argparse choices. All seven pre-existing choices, default branch, exact current-branch equality, inventory/patch digest, artifact source, framework slice verification, no-overwrite rule and installation code remain byte-identical. The profile and reusable workflow now require the same new ref.

Actual argument controls reproduced rejection of the first preparation ref, admitted the new ref and old Apple16 ref through the real parser, and rejected an unrelated ref. Accepted parser controls stop at an intentionally absent inventory before archive reads or installation. They do not claim a Heart build or installation. All 74 host controls were rerun: 72 passed, 2 Windows POSIX skips, zero failures.

The application source, all 37 Swift declarations, original SDK and Heart producer pins are unchanged from the first preparation. Apple37 remains NOT_RUN here. Raw controls and exact inverse proofs are sealed below. The first preparation docs retain their historical ref and results; this correction selects the consumer ref used for the subsequent actual workflow.
