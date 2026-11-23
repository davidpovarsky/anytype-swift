# Native inline-file process recovery

Status: source frozen; product execution not yet performed.

This isolated Linux fixture covers actual SIGKILL recovery at the original reservation/root boundaries and a real lost HTTP commit acknowledgement followed by crash/reopen/retry. It preserves all qualified native production sources and old controls.

- [Frozen source manifest](../../../Tools/AnyEngineValidation/prepared_inline_file_recovery/source.json)
- [Exact fixture protocol](../../../Tools/AnyEngineValidation/prepared_inline_file_recovery/PROTOCOL.md)
- [Original candidate reconstruction](source-reconstruction.json)
- [Original preparation-only gofmt-path failure](format-path-original-failure.json)

The original Any/SDK worktrees retain their intentionally staged overlays and ignored SDK checkout unchanged. New isolated worktrees were reconstructed from the exact upstream pins; their full candidate trees match the immutable source manifest exactly.

The two new methods are TestPreparedInlineFileActualProcessCrashRecovery and TestPreparedInlineFileActualLostHTTPAcknowledgementRecovery. Their private child helper is not an additional product acceptance method. No prior HTTP/native or Swift method is selected.

Read-only independent review of the original frozen fixture found no demonstrated ownership, post-commit acknowledgement-loss or native-readback blocker. The following narrow source commit only records and validates actual PGID and preserves raw WaitStatus. Source review and compilation alone do not qualify either method.

New runtime acceptance is recorded separately with actual source/binary identities, named events, original process/transport receipts and explicit limitations.
