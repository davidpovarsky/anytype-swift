# Qualified coherent continuation controls

The four-method controller scope is qualified through three original passed methods plus the repaired fourth method. No simulator, native, App, UI, build or old control suite ran.

| Original execution | Actual selected scope | Outcome |
| --- | --- | --- |
| attempt1, controller9abf690, source3a6 | Four new methods | First3 PASS; fourth FAIL with5 assertion-type errors |
| attempt2, controller8954bf, sourcead05 | Only the failed fourth method | 1 PASS,13 passing subcases, no failures/errors/skips |

Attempt1 remains FAIL. Its positive subcases within the failed fourth method are not counted as a complete method pass. Across both attempts there were five actual method executions. Distinct complete coverage is four methods and27 subcases:14 retained subcases from the first three methods plus13 from the repaired fourth.

The corrected test changes exactly two assertion expressions covering the five original failure scopes. It expects the existing RuntimeError from the canonical-module, intent and admission guards; Snapshot's other ValueError expectations remain exact. The full test file reverses to its original bytes, the first three method bodies are unchanged, and no production source changed for the retry. The original four-method wrapper remains unchanged; a separate pinned wrapper selected only the failed method.

## Exact receipts

- Original attempt1 execution SHA-256: e9e566eb8c19a972c146a6b24583d5c1dc0a03e7ae826e54e5aa94e23a59df2d.
- Original attempt1 seal SHA-256: ddd18e031df3a4c4070939a040e3358d0f83905e03ee0dadec26cd934e4c0764.
- Repaired attempt2 execution SHA-256:45e4c2d8d0132f6ff5646129d8ade28ecb779b1f0b8f13082b409837eb12de7f.
- Combined qualification SHA-256:b3592ba2899703a58147b72bb4b3ae7e81901cf7c919c5897dcd4490ee723647.

All63 attempt1 originals and18 attempt2 originals were copied byte-for-byte into their separate original directories. Both diagnostic attempts and launcher records remain intact. Source before/after is identical for all70 original bindings and all79 failed-only bindings. Actual loaded repository modules were22 to26 in attempt1 and22 to22 in attempt2; the actual production preload/Git-admission subcase independently admitted47 sources in each run.

## Source and integration boundary

- Corrected production/controller source:3a6f932925a7cadd37490b91eed59c27f58da446.
- Test-only expectation correction:ad05ea15beb10b98feb74ab5ec705e18535fa8ba.
- Failed-only frozen controller/input metadata:8954bf6304d58b5a5eb6379cb965a0a3b2b18747.
- Retained dependency baseline:75bd6d7af18dfd511e85582ce7f994d2801b7703.

The new source contains owned-construction receipts, an exclusive attempt-only first-selection journal, mandatory actual preparation plus positive post-container read, coherent outer cleanup profile forwarding, and a live canonical/Git-admitted cleanup snapshot with exact construction command roots. Default paths, deadlines, original Products/App identity, process-group policy and product acceptance gates remain unchanged.

The dependency overlay commits carry already-qualified baseline copies; they introduce no new Release behavior. Integration must preserve root's current SDK helpers and package_evidence policy. This branch never changes package_evidence; existing .log/.json policy retains every newly referenced construction output. Static source-review contains the exact current-policy-only comparison and whole-file inverses.

This closes the bounded controller qualification. The eleven original actual kernel observations remain a separate retained scope. Actual pending Release native/UI acceptance still requires root-owned publication and dispatch against the original Products; no such acceptance is claimed here.
