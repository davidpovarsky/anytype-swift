# Bookmark6 missing-two continuation2 — source proposal

**Source prepared for independent review; not published, uploaded or executed. There is no runtime grant.** This is a finite successor of the published `e01176b6a15bdb6a8ff7fedbca5c880634a773ef` controller, SHA256 `0e8fa197…`. It reuses the already-qualified Integration runner and test library. No SwiftPM, compilation, product copy or old-method replay is introduced.

## Exact corrections

The original direct continuation failed with child exit **69**, empty stdout/stderr and no observed test events. Its nine original files, 495,425 bytes, remain unchanged. The separate primary-source diagnosis `c8e1fe1d…` establishes two command defects against official Swift Testing 6.4.3 commit `ba0861fb203553caf2e21dd0479d2c0169307021`:

1. Test filtering operates on `Test.ID.description`. These parameterless function IDs include a mandatory source-location suffix. The old filter stopped at the method name or `()`, excluding both generated IDs. The successor fixes the module, suite, exactly two complete method names, exact source basename, and positive source line/column:

   ```text
   ^PinkhaAnyIntegrationTests\.AnyHierarchyTests/(?:creationOverrideRejectsAnotherWorkspaceBeforeDispatch|creationOverrideAndDefaultCreatorShareTheExistingMutationQueue)\(\)/AnyHierarchyTests\.swift:[1-9][0-9]*:[1-9][0-9]*$
   ```

2. The unchanged strict result reader requires the named suite form containing `(aka 'AnyHierarchyTests')`. Official output emits that form at positive verbosity. The successor adds **`--verbosity 1`**; it does not relax the result reader.

The fixed command remains the exact existing Integration executable with `--testing-library swift-testing --no-parallel`, the explicit verbosity and the fixed filter. Neither the Host product nor another Integration method is selected. Runtime discovery and actual positive test output remain unobserved by this preparation.

## Retention and output ownership

The sole new output is:

```text
/mnt/development/projects/evidence/pinkha-wave2-bookmark6-20261127/continuation2
```

The original physical-path and existing-output refusals remain. TMPDIR follows that new directory through the unchanged environment helper. No existing directory is reused or removed.

All nine original `continuation1` files are now fixed inputs in the existing before/after/final witness. Their names, sizes and hashes are literal constants derived from the actual retained originals. The prior receipt must remain FAIL/exit69 with no `testResult`, its original controller/product/completion bindings and its retained positive absence record. Historical groups are never supplied to a process helper. The expected immutable path set becomes **438 existing paths + nine historical files = 447**; the original source inventories and 102 Crypto custody checks remain intact.

The new receipt identifies continuation2 and references continuation1's unchanged failed receipt. It cannot rewrite either the original six-method FAIL `4441afb9…` or continuation1 FAIL `fe4dcf30…`. The four observed XCTest passes remain separate. This controller can qualify only the two missing Swift Testing methods, with two exact start/pass pairs, one named suite, exact positive two-test total, and zero XCTest/other/failed/skipped/parameterized events.

## Preserved process and resource policy

The exact `58624c3f…` owned-process helper, one new `Popen(start_new_session=True)` path, first-error retention, guaranteed cleanup, absence latch and final evidence checks are unchanged. Only `retained_witness` and the receipt metadata/argv portion of `main` change. Fifteen other function bodies remain byte-identical, including the original ten helpers and the strict 3,008-byte result function with its final newline, SHA256 `6f284780316ece9027b1a14f9e7a69693518f87205009a51e0a336c2acc13d6f`.

The existing limits remain **300 seconds for the child, 360 seconds for the outer dispatch, 256 MiB for the whole owned namespace with its 1 MiB final-evidence reserve, 2 GiB root and 512 MiB development live floors, 32 MiB admission margin, and 512 MiB available-memory floor**. The exact executable/library remain `c5334175…` / `5eac3963…`, and the original compiler/source/Crypto qualification remains mandatory. There is no automatic retry or assumed capacity grant.

## Reviewable files

- `run_missing_two.py`: 37,159 bytes, SHA256 `d7b0eb74a542290f67d1d6a68c7dc3f0ee87773ca9c7f82cfb109666a4edce54`.
- `source-inverse.json`: complete forward and reverse byte proof to exact 0e8; all other bytes and fifteen function identities retained. `source.patch` shows the finite changes.
- `continuation-plan.json`: fixed command, source/product pins, output and unchanged budgets; publication and runtime story are null.
- `prior-continuation-retention.json`: exact nine actual input pins and original closure/FAIL references. Original runtime bodies are referenced in their existing custody directory, not duplicated here.
- `originals/run_missing_two.0e8.py`: exact predecessor controller.
- `source-review-notes.json`: author source inspection; independent review remains separate.
- `local-inspection-stop1.json`: preserved metadata-only preparation stop caused by comparing function spans with different final-newline conventions. The source did not change and no parser/controller was executed.

The diagnostic, 16-file official-source manifest, root diagnosis review and required primary bodies remain under `../exit69-source-diagnosis/`. The manifest binds those exact references for a later compact packet. Existing source/result publication and runtime approval are separate steps. No host, process query/signal, Swift, test, controller, result parser or candidate selection-filter execution occurred during this preparation.
