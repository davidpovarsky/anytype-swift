# Native inline-file process recovery

Two new Linux native/HTTP acceptance methods passed once on 2026-11-23. The exact original event stream reports two named starts, two named passes, zero failures and zero skips. No previous native, HTTP or Swift method was rerun.

| New method | Actual result |
| --- | --- |
| TestPreparedInlineFileActualProcessCrashRecovery | PASS, 0.67 s. SIGKILL after the original durable reservation and again after the native root commit; three distinct child PIDs; same original intent/specification/IDs after each reopen; one final native row with exact metadata/plaintext. |
| TestPreparedInlineFileActualLostHTTPAcknowledgementRecovery | PASS, 0.49 s. The real commit handler completed; independent native readback succeeded before the actual TCP connection closed without response bytes. The client received EOF with no HTTP response, then a SIGKILL and distinct-process reopen retained the same original complete receipt and one exact native row after retry. |

The original Go package execution took 1.218 s. The two final orderly closes are cleanup only. Five child helper starts and two normal helper passes remain component evidence; they are not additional product acceptance methods.

## Exact source and retained production code

- [Frozen fixture/source manifest](../../../Tools/AnyEngineValidation/prepared_inline_file_recovery/source.json)
- [Protocol and execution boundaries](../../../Tools/AnyEngineValidation/prepared_inline_file_recovery/PROTOCOL.md)
- [Original candidate reconstruction](source-reconstruction.json)
- [Production/source retention](attempt2-original/source-retention.json)
- [Actual qualification](qualification.json)
- [Original evidence audit](attempt2-original/audit.json)
- [Original named events](attempt2-original/named-events.json)

The qualified native fixture commit is b2cebd7ddf7f62379e59427b2f0f64d980b8fd9e, tree 6d392a7857a4082cc918267302ff92977049ffe4. Its only additions to candidate tree 0445217b25b4f4fcf4d2ce86e3a4eecfcfc5cd10 are two Linux opt-in test files. All 850 original candidate Any files and 683 SDK files remain unchanged. SDK tree 8b9df2cdcefb5aee3973df11a326652f5a2378f4 is exact.

The original intentionally staged Any/SDK worktrees were not edited, committed or cleaned. New isolated worktrees were reconstructed by applying each complete candidate patch once to its exact upstream pin. The existing source manifest retains its original unqualified-candidate status; these separate runtime receipts carry the new acceptance.

## Original process and transport evidence

The audit reads the actual two-method Go event stream, all safe nonce-bound records and the five private original child-log hashes. It verifies:

- Five distinct actual PIDs, with each observed PGID equal to its owned PID.
- Three signaled WaitStatus9 exits, completed waits, exact-PID absence and no orderly-close markers.
- The actual real-handler 200 response, native complete/committed readback before connection closure, a genuinely written client request, client EOF, no HTTP response and no first response byte.
- Ten explicit independent native observations across reservation/root/complete stages, plus the separate native post-commit observation at the lost-response boundary.
- Original specification hashes, all immutable receipt identities, exact 4095-byte plaintext and Unicode metadata, and exactly one final row in each owned Space.
- Two normal final cleanup exits, explicitly excluded from crash proof.

Keys and raw SDK logs remain in the private owned directories; they are never copied into this evidence package. Safe receipts contain only original raw-log hashes and narrowly selected helper run/pass counts. The retained compiled binary is also separate from Git evidence.

## Compiler and preservation

Actual compiler profile: Go 1.27.4, Linux ARM64, GCC 13.3.0, glibc 2.39, GOMAXPROCS=1 and -p=1, using the original task caches with GOPROXY=off. The successful compilation took approximately 52.9 s and executed zero methods. The preserved binary is 94,666,781 bytes, SHA256 cca90784568f7f2e551d4266bf3cc1c90082fea76eceafcc2dce6b6a15e73084.

[The original binary build information](attempt2-original/binary-buildinfo-original.txt) records 145 dependency modules and the exact local SDK replacement. All 1,535 tracked Any/SDK input hashes are unchanged across the original before-build, after-build and after-execution inventories. The binary also remains unchanged.

The first compilation failed on a name collision between a new fixture method and its inherited-pipe field. [Its original source/log/command](attempt1-build-failure/failure.json) is retained with zero executed product methods and zero spawned native children. The repair only renamed that new method and its two call sites. No product source or runtime semantics changed. The earlier preparation-only gofmt-path error is also retained separately.

## Acceptance limits

This closes only the two new Linux native/HTTP recovery scopes within the already bounded original inline-file domain. It establishes no physical power-loss durability, Swift/App client behavior, Apple simulator/device result, notification-outbox delivery, remote recovery, whole-Space snapshot/census, general-file migration or full migration. Default runtime gates, general-file capability 0 and networkVerified=false remain unchanged.
