# Attachment-safe Heart source and runtime preparation

## Scope

This change composes two explicitly named runtimes from immutable Heart source
`d98420b1113536afd08cde6de9a5816f6d27ffff`. It fixes ordinary edits accidentally
attaching projected Torah Properties, while preserving every r15 lookup source
change. It does not rewrite existing r14/r15 approvals or artifacts.

The native correction is authored once in
`Tools/TorahNativeDerivedSpike/prepare_heart_integration.py`. The new composer
extracts its exact three already-tested patch sections: `details.go` and the
two attachment fixtures. Every other base patch section is retained byte for
byte. There is no second implementation of the fix.

| Explicit variant | Complete native patch SHA256 | Native lookup |
| --- | --- | --- |
| r14-attachment-v1 | d055933d365d3f0453ad42ce4eb4463a25deceac3d0df11162d460896810a6b4 | Absent |
| r15-attachment-v1 | 595f8142f00035da2fff4925c8fe125fa7cf36de9ae124b528a9d2130b2a9bf6 | Preserved |

The corrected r14 inventory has 37 files. It reproduces the complete proven
candidate source exactly. The corrected r15 inventory has 44 files: its 42
original files remain, only `details.go` changes, and two fixtures are added.
All seven r15-only files and the other r15 lookup implementations remain intact.

The runtime version contains the exact complete patch hash, the lookup marker
only when that implementation is present, and a separate
`pinkha-torah-attachment-v1` marker. Neither corrected variant can be installed
or reported as original r14/r15.

## Existing evidence and its precise limits

[Native attachment run 44610974453](https://github.com/davidpovarsky/anytype-swift/actions/runs/44610974453)
at `be6cc5d8b5e65ee78f46e09b3105e3360eec894f` passed 48 actual top-level native
tests, 250 records including subtests, in the basic/detailservice packages.
The same four ordinary-edit cases failed for the expected attachment assertion
when the exact original r14 `details.go` was substituted. The complete original
verification is retained in
`docs/validation/20261119-wave15-qualified-results/VERIFIED_ORIGINAL_NATIVE_ATTACHMENT_44610974453.json`.

This source proof applies exactly to the composed r14 correction. The identical
three source files also justify the port to r15, but the 48/250 result is not
relabeled as a test of the combined r15 tree. The new r15 build executes only
the two affected fixture methods, six parent-and-subtest records, in that
actual combined tree. A missing, failed, skipped, duplicated or extra test
record cannot qualify.

Original r15 did eventually build successfully:
[run 44393343388](https://github.com/davidpovarsky/anytype-swift/actions/runs/44393343388)
at `83c40f97c30a428a8c9c362f0847a2edcfec08ec` produced artifact 14479264981,
`Pinkha-Universal-Verified-Heart-r15`, on November 18. Its native patch is
`5a0906158569d47642d9fc978932cdf254550a31c864a1fb34bd1f8e4e7c10f2`,
so it predates and excludes this correction. The earlier failed builder run
44259388061 is historical; its repaired dependency preparation is reused.

## Builder and dispatch

The existing builder's default remains the original r15 patch, version,
artifact name, dependency guards and proof boundaries. Corrected variants are
opt-in via `--attachment-variant`. The original r14/r15 build and acceptance
routes remain available and retain their identities.

Dispatch the existing `torah-inspector-ipados27.yml` workflow with the explicit
route `t5-r15-attachment-runtime`. It calls the separate
`pinkha-t5-attachment-runtime.yml` workflow with fixed
`variant: r15-attachment-v1`. Only this corrected r15 is built by that route.
The corrected r14 profile is available to a reviewed workflow caller if an
actual older-capability compatibility pair is needed; it is not built by default.

The corrected runtime uses the existing exact Go 1.26.5, pinned gomobile,
Tantivy and generated-module dependency checks. The actual original generated
module manifest must still match the reviewed complete declaration, and all
three live generated architecture graphs must pass. Evidence distinguishes the
reused dependency baseline from the actual corrected native source.

The archive is
`Pinkha-Universal-Verified-Heart-r15-attachment-v1.tar.gz`.
It retains the complete candidate inventory and all three exact binary-slice
hashes. The proof archive also contains the generated patch/inventory, source
composition, original commands, module receipts and affected native fixture log.
A successful build alone still reports AppGetVersion, account pairing and full
T5 acceptance as not executed or unproven.

The 15 focused Python controller controls passed locally. Their raw log, actual
subprocess exit and source hashes are preserved beside this document; those
unchanged controls are not repeated on the Apple builder. They are controller
checks, not native or simulator acceptance.

## Retained app and efficient remaining validation

Both revisions use the same Heart commit and existing protobuf/RPC signatures.
The r15 additions are internal lookup/index behavior and guards preventing
private lookup metadata being installed as public Properties. No source-level
ABI change prevents the retained Heart app from using corrected r15. Actual
application compilation/linking and runtime execution remain the proof.

1. Build corrected r15 once, checking the two affected native fixture methods
   and all three architecture slices.
2. Admit that exact named variant in the installer and runtime observer. Verify
   full version markers, archive/source/inventory identity and original slice
   hashes. Keep the original r14 admission path unchanged; do not substitute a
   label or merely search for any generic derived marker.
3. Compile the current retained app against the corrected artifact and run the
   pending mounted editor, Properties and SDK06 journeys. Reuse the isolated
   editor ownership/UIKit results already obtained from unchanged component
   inputs; those do not establish this runtime's application acceptance.
4. Run the actual corrected-r15 account/reopen, canonical/public preservation,
   indexed-target freshness and T5 UI journeys. Bind every observation to the
   actual runtime version and shared source. Reuse the same build/account
   phases where the existing contracts permit.
5. Build corrected r14 only if proving the mixed-capability downgrade/recovery
   sequence is still an acceptance requirement. Distinguish that corrected
   pair from compatibility with unmodified legacy binaries.

T5 lookup remains disabled in product builds until the required acceptance
gates pass. Existing Swift runtime capability admission must be extended to the
exact corrected identity before T5-enabled acceptance; default app editing
does not require enabling that lookup flag.

## Legacy and mixed-version safety

An original r14 or r15 binary cannot acquire this source correction from a
new archive's label. The retained original counterexample and old-edit failure
remain valid evidence of attachment drift. Do not mark unmodified legacy
writer compatibility passed or weaken the canonical/public equality assertions.

Already attached public Properties cannot safely be deleted on upgrade merely
because they match Torah keys: the stored links do not distinguish a user's
explicit attachment from the old accidental attachment. The correction
prevents new automatic attachment, preserves all existing explicit links, and
leaves intentional attachment via the native attachment service unchanged.
No migration, canonical rewrite, silent cleanup or destructive repair is added.

## Current status

Source composition and controller controls: PASS.
Corrected Apple framework, actual AppGetVersion, retained app compilation,
same-account/mixed-version behavior, UI navigation, full T5: NOT_RUN here.
No CI was dispatched by this change's author. No product feature was enabled.
