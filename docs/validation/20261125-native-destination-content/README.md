# Native destination content qualification — 2026-11-25

## Accepted scope and source

Product commit: `087d79680c7f1f32c92910edc9c59dcdd0091135`.
This is actual destination-executor/content verification against the separately launched original Any CLI. The immutable source is explicitly labelled **component input**, with two generated documents; it is not a live Heart account witness and it does not admit the blocked 156-object captured space.

Original native source: Any `548f5cd0430a723bd26ea724daeb99991f68b9c9` (874 files), SDK `e195f6c07a053c6588e39ffe72ee4fc44cf3d953` (709 files). All 1,583 files match the source receipt before and after the retained continuation. Reused binary SHA256: `bc73441d05a502e3e77df479f54279540489869b00ca1aecf4e1e9f681fa0f49`. No Go compilation or replacement runtime was used.

## Actual results

| Phase | Result | Original log SHA256 |
| --- | --- | --- |
| First execute attempt | FAIL: transport timeout, retained unclassified | 3e973cca6c72a18516ec812348150ef8675cce9a1cbccb6782dcbbcb95ba7019 |
| Resume original journal and compare content | PASS, 1 test, 0 failures/skips | 650cc85d94693416d452cf61afd77c0dcf258f4a166e0bcc9e1ab6e3f18803f6 |
| New-process OS-offline reopen | PASS, 1 test, 0 failures/skips | 7862032c443bdcf42d23bda0305c6d62d71f2e2a623db9f3746bdb0bbbb4b3f9 |
| Real changed-content refusal continuation | PASS, 1 test, 0 failures/skips | 37bc4b882d742adadebf21f70ba58e520268cbe64bd489c840f99b4415956fe5 |
| Compiled schema order/identity control | PASS, 1 test, 0 failures/skips | c4a40ee20e1ce7aeaf42f0ef8e32a01ca28203dafe79844a6ea066cd541040a2 |

The native method is invoked in three distinct phases; this is not three distinct test methods. Fourteen distinct component controls are accepted across the retained component runs: eight original executor controls, five new content controls, and the compiled-order control. Initial missing-`try` test compilation and invalid plan-ID fixture failures are retained. Only their affected control was rerun after correction.

Seventeen prepared native operations create a type, collection, four properties, a part with editor and records datasets (two fields/one index), two documents, three hierarchical editor blocks, two files and three deferred property updates. Verification checks original native receipts and allocated identities; exact definition/compiled dataset metadata; complete owned record/property/file census; Unicode/Markdown content; empty versus absent values; collection membership; explicit datetime wire semantics; and actual file plaintext hashes.

Both A→B and B→A relations are also read through the original native links and backlinks APIs. These are genuine relation descriptors and indexed edges, not text that merely resembles an object link. The complete initial and cold content reports are byte-identical, SHA256 `8ab1bd0e6002c2e36f24400a9cdf2a423e9d9ab05f827dc87bdf7025ea693e0b`. The two native cycle-index reports are byte-identical, SHA256 `92cc2e4a67aa575fcb5136a7941755fb8f9af4583a56df47a3f6115348ba271b`.

The inline file has 36 bytes, SHA256 `2b9f35094f017f95d5feb8f3ac14dfbaf7f3c02a18ef9da5b8f11b0d9c61dd3b`; the encrypted full file has 8,192 bytes, SHA256 `163621fd8c5c092ea4e22dddef5eaf02ebcb9c968670f6c05a485f21f8e55dda`. Full-file content is verified through actual native Range/206 downloads. It is cached locally and reports **durable=false**; this proof does not assert cloud custody.

## Lifecycle and retained failures

Initial native PID72860 and cold PID94135 both exited0 without forced kill. The OS profile denies outbound network. A reachable baseline TCP listener and sandboxed TCP/UDP probes establish EPERM (errno1). The cold native reports offline and zero network/local/global peers. Reopen refuses to supply original file payloads, so passing cannot hide a reupload.

The external native lifecycle controller later reached its 1,800-second deadline while awaiting the final handshake, after the cold XCTest had already passed. Its result remains **FAIL**. The separate SSH-forward controller also expired and is not relabelled PASS. A bounded continuation reopened the same account/store under the same OS policy (PID99215), performed one actual ordinary name mutation, and proved the verifier refused that changed content. Its automatic finish/forward cleanup completed; native exit0, no forced kill. Sources were rehashed unchanged afterward. No new account, migration, IDs or payloads were allocated in the continuation.

The first execute timeout remains unclassified. Read-only diagnostics established all 17 native receipts committed and ordinary metadata/content routes healthy afterward. Independently, native compiled part ordering was reconciled with original SDK compile.go: fields/indexes declared in one signed change are key-ordered after preserving their original allocated IDs. The expected projection implements that documented ordering; actual returned arrays are still compared strictly. A focused control refuses changed order, allocated identity or required flags. Initial/passing source manifests are retained, including this projection change and added path-only failure diagnostics.

## Limits and retained data

The verifier observes a bounded series of current native reads, with original receipts and revision/definition rechecks. It does not claim a globally atomic space snapshot, imported history, ACL migration, live Heart source authority, UI migration acceptance or full-space completion.

The actual 156-object source inventory remains blocked: non-Basic builtin/media layout adapters, schema-owned read-only metadata, seven source-qualified compiled resolver descriptors, retained settings/collection semantics and the non-null default contract still require closure. Inventory files retain exact capture hashes and counts; files=0 in that capture, which must not be confused with this independent file fixture.

Original private account databases, seeds, native logs and prepared journals remain outside Git under the scoped Mac/Oracle evidence directories. Only whitelisted generated component inputs, public IDs, content hashes, current receipts, commands, test logs and source-bound reports are included here. Private native log content is represented only by SHA256 receipts.
