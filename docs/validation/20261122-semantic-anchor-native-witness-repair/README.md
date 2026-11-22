# Native semantic anchor storage witness repair

## Observed failure and exact preserved evidence

Run [45050652738](https://github.com/davidpovarsky/anytype-swift/actions/runs/45050652738), commit `4e76dba6f6ff714e3d25e382013495a11ac9267a`, compiled all three selected native packages. The four `stext` methods passed all 14 terminal cases. Three lease methods passed all 11 terminal cases. The remaining lease method, `TestPinkhaSemanticAnchorLeaseRetainsNativeLocksAndOneCallStoredWitness`, failed at its positive stored-change acknowledgement. The core method was not executed after that package failure.

`original-evidence.zip` is the verbatim 56,906-byte artifact 14765710346, SHA256 `cfb8bb71b4f35ea8fa057848d6d74b283114580a16009277b7cd6127ef427a30`. `FAILURE_AUDIT.json` binds all 27 files. The failure remains a failure; only the exact seven passing methods and 25 terminal cases are retained.

The original runner checked all 148 candidate source hashes after every compilation and after the successful `stext` execution. The failing lease package prevented its later source guard from running. Its retained methods are tied to the recorded compiled binary, exact original execution log and unchanged reviewed declaration paths. This package has no claimed post-execution source guard. Original test binaries were not archived, so the continuation compiles current lease/core binaries rather than claiming binary reuse.

## Cause and narrow product change

The pinned upstream [`any-sync v0.13.8` storage implementation](https://github.com/anyproto/any-sync/blob/v0.13.8/commonspace/object/tree/objecttree/storage.go) persists a tree ID but omits `StorageChange.TreeId` when hydrating a record in `changeFromDoc`/`Get`. The original witness treated that unhydrated field as mandatory and rejected the valid stored change. The copied upstream file is bound to Git blob `550289c524dc2ae67c52dbe2fcb39d9141a3ee98` in `UPSTREAM_SOURCE.json`.

The repair binds the actual native `Storage.Id()` to the locked tree before reading the record or heads. An absent hydrated `TreeId` is allowed; a populated conflicting value is rejected. The stored change ID, native heads, signed bytes, parent heads, author, read key and current ACL head checks remain in place. Qualified139, generated wire, native module pins, application lifetime, document/settings locks and legacy text paths are unchanged.

The originally failed method keeps its positive real signed-storage path and adds five controlled negative checks: foreign storage handle, conflicting record tree metadata, foreign returned change ID, changed signed bytes and foreign storage heads. These are assertions within that method; they are not five additional native test methods. The successful original three lease method bodies, their fixture/ACL helpers and the witness's initial authority-denial prefix remain byte-identical. `SOURCE_REVIEW.json` records these exact paths and hashes. A separate read-only peer review found no concrete blocker in this repair.

## Continuation and retained checks

The reusable workflow obtains fresh metadata for the original failed run and passes `--component-run` to the native runner. `resume_native.py` requires that exact failed run, commit, branch, repository, original ZIP digest, qualified139 map, original candidate source map and the two exact reviewed native file changes. It validates the original whole `stext` pass and explicitly checks that the lease log has precisely one excluded failure and all expected remaining passes. It rejects missing, repeated, skipped, foreign or relabelled outcomes.

The continuation compiles only lease/core and executes exactly:

- `TestPinkhaSemanticAnchorLeaseRetainsNativeLocksAndOneCallStoredWitness` after repair.
- `TestPinkhaSemanticAnchorNativeEntryRejectsInvalidOrCancelledBeforeAccount`, which was not previously executed.

The final receipt separates original7/25 from current2/2 and reports a qualified total of9/27 only if both new executions pass. It carries both origins and preserves the original failed ZIP and original logs in the new evidence artifact. The existing main dispatcher route remains `semantic-anchor-native`.

Three new Python continuation controls passed once. `continuation-controls.log` and `continuation-controls.json` preserve their original output and exact source/input hashes. They check the retained selection, incomplete/relabelled original outcomes, original producer identity, unreviewed source/input changes, changed original ZIP bytes and overlap that would rerun passing methods. They did not execute Go or Swift tests. The CI retainer validates these original three results without rerunning them.

The original four Python controller methods are retained with unchanged validation code and an explicit three-input review: the two repaired native files and their exact source inventory. All other original inputs remain byte-identical; selected method names and counts remain9/27. Original five pure Go contract controls and portable20 Swift controls are retained unchanged. The new formatter invocation parsed the two repaired Go files but did not compile their native packages or execute tests.

`STATIC_REVIEW.json` records Python parsing and the workflow's exact three-edit delta. Static review is not native execution. At bundle freeze, the repaired/missing two native methods remain **NOT_RUN**.

## Acceptance boundary

These component/storage controls do not complete EDITOR-02. Actual production Page Apply and payload/cold readback, account lifecycle races, generated wire integration, native split/merge/copy/cut/undo behaviour, and mounted Apple acceptance remain required. The app capability stays **OFF**. Production139 runtime identity and its already qualified Apple evidence are not relabelled as this additive candidate.
