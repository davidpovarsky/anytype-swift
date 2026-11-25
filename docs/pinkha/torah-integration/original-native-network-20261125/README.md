# Original Anytype remote-network acceptance — 2026-11-25

Status: **PASS** for an actual two-process, two-repository, bidirectional rich-text roundtrip through the original Anytype default remote network. The successful execution is `job_e8f0acde2861`; both processes disabled LAN synchronization. This is independent native-engine evidence, not a substitute for integrated Maktabah UI, physical-device, compare-and-swap, or 5,000-note acceptance.

## Exact source and execution

The qualified native owner remains `c7e9935eb36a47f73d04cf72ea45472d3f2a8a70`. The existing native 66-case helper and product source were not changed. A read-only Go overlay added `Tools/OriginalEditor/NativeNetworkAcceptance/original_network_peer_test.go` to `core/application` for a real native test executable. `MANIFEST.json` records its actual source SHA-256, original helper SHA-256 and the original export archives retained on the Mac. `network-launch.json` records the executable SHA-256, actual process IDs and fixture path. `compile-command.json` and `compile-result.json` bind the successful compilation to that source.

The producer and consumer use independent application processes and independent repositories, recover the same development account, and operate on the same native object. Only object/space identifiers and expected one-way content hashes pass through control files; neither a body, native export archive nor a database is copied between the peers. The consumer reads the producer’s native rich body, writes a second rich body on that same object through the original native block API, and the producer reads the resulting remote change. Both actual `AccountStop` calls return and both native application instances are absent afterwards.

## Observed outcome

`network-result.json` records both exit codes as zero, an 8.68-second resumed verification phase, real body hashes for both directions, actual account/space/object IDs, and the clean stop result. `readback/` preserves the corresponding selected original export hashes and original text-block hashes. The native ZIP files remain at their exact protected Mac paths and their checksums are listed in `MANIFEST.json`.

The initial attempt (`job_d76dd56aee5b`) stopped because a newly created space had not yet appeared in the recovering peer. It is retained as a failure. The harness was corrected to wait boundedly for the actual original space, and the successful second attempt resumed the existing repositories, account and object. No second identity or duplicate object was created to obtain the pass. An intermediate compile whose input changed during linking was explicitly invalidated and never used for runtime evidence.

Development account credentials remain only in the protected fixture directory on the Mac. They are not included in this report, its source, Git, logs or evidence copies. Do not rerun this completed phase unchanged or consume stale control receipts. A future atomic-update regression must use a new phase namespace while retaining the existing two repositories and identity.

## Limits and next gate

The ordinary native ObjectListExport snapshot in this engine omits causal heads. Its ZIP checksum therefore cannot authorize an atomic update and this pass does not establish compare-and-swap behavior. A separately versioned revision RPC must obtain and compare nonempty native tree heads under the original object lock. Local import completion is never described as remote delivery; remote visibility here is proved by the other independently running original engine’s actual export/readback.
