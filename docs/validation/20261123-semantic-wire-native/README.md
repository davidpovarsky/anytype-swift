# Original semantic capture wire recovery

The three byte codec sources in `Tools/PinkhaSemanticAnchorWire/native` are copied from the original 22 November candidate. The audit verifies all 27 recovered files against their Windows SHA-256 hashes and verifies the original result receipts against the named Go JSON events. It executes no product tests.

## Evidence and boundaries

| Original execution | Actual result | Reuse boundary |
| --- | --- | --- |
| `pinkha-semantic-wire-controls-h21u4r3w` | Three methods; 26 terminal cases passed | Original wire SHA `60425d6c...`, exact contract SHA `f15e9c49...`; standard-library command-line files only |
| `pinkha-semantic-wire-unicode-49d4cdvz` | One method; 12 terminals passed and two failed | Current production wire SHA `7105112f...`; the complete failed execution is preserved |
| `pinkha-semantic-wire-unicode-repair-116iipgg` | Eight selected terminals passed | Same production wire; corrected fixture SHA `a4c0e2c9...`; six unaffected Unicode terminals were retained without a rerun |

The Unicode fixture initially replaced the first `text"` token, which was the JSON field name. That made the two valid replacement-character requests invalid for the wrong reason, and it also meant six invalid-escape cases did not exercise their intended value. The repair targets the complete text field/value pair. Exactly those eight cases ran again. The other six cases were unchanged. The resulting current-source Unicode evidence is fourteen distinct passing terminals, with their two original runs preserved.

The production difference from the first execution is one strict UTF-16 escape preflight and its two helpers. The audit verifies that removing this addition exactly reconstructs the earlier codec. The original 26 passing terminals retain their original source scope; this is not a claim that those methods were rerun against the later source. The reply controls use explicitly synthetic response-event bytes and do not demonstrate native execution.

The codec accepts versioned named fields, rejects duplicate/unknown/null fields and invalid scalar offsets, preserves all ordered native marks, and refuses unpaired Unicode escapes before the JSON decoder could substitute U+FFFD. Replies carry only fixed outcomes; an applied reply requires a native receipt and bounded opaque native response-event bytes.

## Compatibility

The contract compiled in all three original executions is byte-identical to the currently committed `Tools/PinkhaSemanticAnchor/native/pkg/lib/pinkha/semanticanchor/contract.go`. The original codec commands compile only that contract and the wire/test files; all imports are from the Go standard library. They do not compile the recovered service wrapper or the Page/account harness.

All nine current component source files are checked against commit `e7fd39b763d3d0244996c207552096f169de85ed`. This preserves the repaired lease SHA `598e2fc9cd1173414f6e2afc1cd54672b7ec6fe72d1c4eda9a9687949677b814`. The older archive's stale lease is not used. The frozen nine-file manifest and its 148-file native route remain unchanged; the codec is a separate additive overlay.

## Next actual native gate

The originals also contain the unchanged service entry and two previously unexecuted Page methods:

- `clientlibrary/service/pinkha_semantic_anchor.go`
- `clientlibrary/service/semantic_page_test.go`
- `clientlibrary/service/semantic_page_account_helpers_test.go`

The intended new candidate is the qualified 139-file patch plus the current repaired nine component files, three codec files, one service file and two Page test files: 154 paths. The original qualified service inventory contains two unrelated wire tests and generated `service.pb.go`; the candidate uses new filenames. The Page helper declarations still require a complete package collision and compile check.

The first Page method creates a disposable LocalOnly account and real Page, checks three refusals, performs capture through the byte service, verifies the actual ObjectShow result, response event and signed stored payload, then stops the account. The second method must run in a different process, recover that disposable account, verify the exact durable block and stored change, reject a duplicate capture, and stop the account.

Neither Page method, the service wrapper, public HTTP, Apple SDK binding, mounted editor flow nor process reopen has executed in these receipts. The app capability stays OFF. No protobuf/schema regeneration or CI dispatch was performed.

## Reproduce the read-only audit

```sh
python3 -B docs/validation/20261123-semantic-wire-native/audit_original.py
```

`--write` refreshes only the deterministic audit report. The retained original failures and raw source/log files are never rewritten.
