# Original annotation SDK byte budgets — source preparation

Base: `257c49a5871c62611d88fab00a8124c7ff072166`.
Owned branch: `codex/otzaria-original-annotation-budget-20261123`.

This packet prepares four existing original framework files for the approved annotation payload policy. It grants no account, Space, source, permission, import, or native write authority. The active Stage B application qualification remains a different source and run.

## Exact boundary policy

| Boundary | Bytes | Role |
| --- | ---: | --- |
| Untouched original native ZIP A | 1,048,576 | Independent raw archive bound |
| Canonical snapshot header H | 16,384 | Original aggregate header bound, unchanged |
| Frame prefix | 16 | Original magic + version + header length, unchanged |
| Complete framed body B | 1,064,976 | Exactly 16 + H + A |
| Complete annotation JSON J | 2,097,152 | Separate Host owner; includes unknown/private metadata |
| Generic ActionWireCodec | 65,536 | Unchanged in the separately owned Host work |
| Ordinary FileDownload qualification | 65,536 | Unchanged SDK caller and helper restriction |
| ZIP member / expanded limits | 512 / 8,388,608 | Unchanged original parser limits |

The canonical policy bytes are copied unchanged from native source `c067f5c5d5afc5d2679bdc371163d3018cc71a7b`, path `native-owned-annotation-contract-20261123/bc-original-import-design/ANNOTATION_PAYLOAD_POLICY.json`, SHA256 `818bd440374cd49072f018065d300209bd2dafc506ec16d8c2c686736bde7077`.

## Four product changes

- `AnytypeOriginalEditorSnapshot.swift`: the same public explicit `maximumBodyBytes: Int` API may admit up to B. A caller that supplies 65,536 retains that exact smaller cap. Both decode and frame enforce A independently; decode checks the slice length before allocating the archive slice. Capture bounds its original owned file read by min(caller body limit, A). The ordinary file reader keeps its existing 65,536 limit through a private bounded implementation shared with the ZIP reader.
- `OriginalAnnotationNativeArchiveLayout.swift`: one internal immutable annotation budget enum and the archive-size reference. All original ZIP parsing, local/central reconciliation, descriptor/path/extra-field validation, contiguous layout, member and expanded-size guards remain exact.
- `AnytypeOriginalEditorNativeBodyReadback.swift`: historical snapshot decoding uses B; its actual original export read uses A. All original identity, provenance, report and comparison guards remain.
- `AnytypeOriginalEditorRestoreQualification.swift`: both original owned ZIP rereads use A. The original import, original identity checks, byte equality and cleanup remain. This existing qualification route is not promoted into a production importer.

No new public API, generated method, native library pin, workflow, host project, account initialization, selection or auth path is added. The public declaration lines are unchanged. Complete Host and attachment fixture files remain byte-identical to the base.

## Actual affected controls

One execution on Oracle used Swift 6.4.3 for aarch64 Linux, Swift 6 language mode, and -O for the two small Foundation executables:

- 10 candidate cases, 1,214 assertions: canonical policy correspondence, legacy and invalid/extreme caller limits, independent A/H/B boundaries, four authentic complete ZIP inventories, an ordinary synthetic ZIP exactly at A, and its one-byte-over counterpart.
- 4 **new** controls of the unchanged original layout source, 8 assertions: each authentic export exceeds the original 65,536 cap and the actual original parser rejects it with `sizeLimit`. These are new executions on these original export inputs, not reused historical passes.
- Four unprojected Swift syntax parses. Only the complete original Foundation ZIP-layout file and owned control harnesses were compiled. Snapshot's CryptoKit/Darwin/Protobuf/Lib composition was not compiled or executed.
- A full reverse application of the four-file diff recovered all four exact original blobs.

All 11 child commands exited zero, had empty stderr, avoided timeouts, and ended with the child reaped and its owned process group absent. Exact streams and command receipts are in `controls/run-1/`; RESULT SHA256 is `d22db898a6ffab6a573205401a9319babcae7f683979c27dc3ea391997aa7a55`.

The four genuine ZIP copies are from authenticated native run 45130249062, retained upstream evidence commit `9357b53ff8230128d1f3340118ec152770feb12a`. Their complete inventories are 67 / 67 / 68 / 87 members and their bytes are 79,989 / 80,271 / 81,382 / 103,617. All source admission ZIP CRCs and indexed member hashes matched. The actual native producer leaves later failed their body assertion; these bytes are authentic exports but are **not native archive/body qualification**. This packet qualifies only the original portable ZIP framing and budget logic.

Synthetic ZIPs and compiled executables remain in the owned reproducible diagnostic directory, with hashes and the deterministic generator retained in this packet. No authoritative provenance/header/snapshot was fabricated for a capacity test.

## Preserved evidence and scope

`preparation-1/` retains the initial untested four-file afterimages and diff. The final source moves the new raw archive-length guard before `subdata`, matching the approved allocation order. No control result is attributed to those initial bytes.

`SOURCE_CORRESPONDENCE.json` is the actual control driver's receipt. `SOURCE_SEAL.json` adds static correspondence for the unchanged report validation, canonical header encoder, SHA256 helper and frame integer codec. Exact before/after files and full diff are included.

No previous 245/38/71 source controls, original SDK producer, signed EN/HE consumer, Apple application build, Stage B UI journey, native import, restore, persisted-body readback, cold reopen or device qualification was replayed here. The prior signed SDK PASS cannot qualify these later source changes. The separately owned Host typed JSON/SQLite migration and native importer must be composed and qualified with this source before production acceptance.
