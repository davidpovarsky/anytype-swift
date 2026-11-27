# Ordinary attachment recovery: qualified Engine/Host handoff

This change fixes upload transport completion and preserves the original scoped acknowledgement through cancellation, journal failure and authorized recovery. It is a Wave 1 Engine/Host change. Wave 2 owns caller-intent persistence, UI/session wiring and Apple protected-journal acceptance; Wave 3 owns application integration and distribution.

## Source behavior

- The single upload operation completes only after its task-completion and session-invalidation delegates have drained through the original serial delegate queue. Its first outcome is latched against cancellation.
- The existing attachment creator reserves one of 64 bounded acknowledgement slots before dispatch ownership. Unknown outcomes remain unresolved; they are not evicted or resent.
- Validated native acknowledgements stay bound to the original intent/account/Space. An opaque module-minted recovery receipt can be handed to the correctly reopened original journal owner, which must already contain the matching reservation. A bare caller file ID cannot mint a receipt or a new upload.
- A durable verified journal state precedes the final current-authority/task-cancellation fence. No actor suspension follows that fence.
- The existing object creator reuses its attachment creator and journal for its own lifetime. No second journal owner or parallel attachment subsystem is introduced.

There are six replacements relative to e96ba072887e7581ed6de20fdd81e0897c83763d: three Host source/test files, two Engine source/test files and the detailed attachment contract. The remaining paths are immutable qualification sources and public evidence. The source manifest binds the five Swift replacements to the actual compiled component inputs. All undeclared repository paths must remain byte-for-byte at the parent tree during publication.

## Actual evidence and attribution

| Receipt | Actual execution | Acceptance |
| --- | --- | --- |
| components-attempt1 | Original missing-source compile failure | Preserved failure; no passing method inferred |
| components-attempt2, 4b24eb81 | Original build; 17 Host + 6 pure passes; HTTP fixture setup failure | Reuse 23 passes only; original overall FAIL retained |
| http12-attempt1, 0526d95b | 12 HTTP passes, 26 fixture closures; final source-audit deadline failure | Reuse 12 passes only; original overall FAIL retained |
| http12-completion1, 02fa0059 | Exact source/Crypto/Products/modes/fixture final audit, zero child commands | Qualifies the combined 35 unchanged methods without replay |
| native-attempt1, 5b017bdc | Physical compiler-input key mismatch before every child/account/test | Preserved zero-execution preflight failure |
| native-attempt2, 8b7a4dd4 | One previously unrun Swift method; two actual original-native attachments and cold OS-denied reads | PASS for this narrow local native route; four owned groups exit zero and positively absent |

The final native method passed in 0.18 seconds; its controller job8295f2fcaea8 completed in 8.84 seconds on 27 November 2026. It used the qualified 1607-source native producer e26587d9 / binary1b25764f without rebuilding. It created one fresh account, an empty inline file and a 12,420-byte full-tier PNG, checked native-resolved metadata and byte digests, then shut down and reopened the native service under the same outbound OS denial. Both original identities and contents survived. Swift used the admitted loopback endpoint; native init/warm/cold processes were independently OS constrained. No retained private account was opened or copied.

The full-tier file was cached but not durable. This result does not claim cloud custody, a new cross-account transfer, a crash scenario, production protected-journal persistence or Apple/UI acceptance. Those existing and pending gates retain their own source and scenario boundaries. The original network/ACL/P2P and migration counts are not rerun or relabelled by this package.

## Reuse and operational locations

The exact public receipts are copied here without JSON reserialization. Two immutable review patches and the original failed compile log are losslessly stored as deterministic GZip members so their original whitespace is retained while the normal source whitespace gate remains unchanged. The source-provenance mapping records both encoded and original hashes and lengths. Original retained outputs remain under `/mnt/development/projects/evidence/pinkha-ordinary-file-upload-20261127`; their full source and product inventories remain at the original pinned paths. The actual compiled-source admission de642b7c covers 32 production files, four compiled test files and the fixture source. It binds original project12e49 and original TorahInspectorKit9058, not a later integration checkout.

Qualification source snapshots live in `Tools/AnyEngineValidation/ordinary_file_upload_recovery_20261127`. Their frozen source manifests and README status describe the state before their executions; this receipt chain records the actual later results. They intentionally retain exact Oracle evidence locators and may not be rerun on retained accounts or over existing output directories. Reproduce only a changed-source or still-missing acceptance scenario in a new isolated namespace.

The source-only publisher performs a normal new-branch commit and ordinary push, checks the complete unchanged parent tree, and uses the existing shared Git group for Git children. Before push, an ordinary ubuntu/group actor reads all newly reachable objects, the exact new ref and the complete candidate tree. This retains private evidence permissions while preventing new root-only objects from blocking Wave 3 integration. No force push, reset, shared cache cleanup or final integration branch mutation is used.

See `docs/architecture/ordinary-file-attachment-contract-20261127.md` for the typed API, unresolved-outcome semantics, exact evidence hashes and remaining Apple/cloud boundaries.
