# Root-controlled shared App build

This control closes over the reviewed Wave2 producer from commit
`204f8fbb25c3b21f419fc1a8818eb46ed492e561`, SHA256
`9b1405ea44ba9cce3fca47a88127fc798fedab3d1b05f6e3728da3597d19929c`.
The controller source and admission are separate from the exact compiled App
commit. The templates are deliberately **not ready for staging or building**.

## Preserved original behavior

The adapter expands the exact producer with explicit input-pin and output-root
substitutions. A reversible delta restores every original producer byte.
`run_phase` and `source_state` remain byte-identical. Original native runtime
identity, both native slice receipts/commands, framework inventory, canonical
SDK check, Package.resolved, exact source before/after, owned process cleanup,
full Products inventory, original focus compiler checks, and original App/UI
build commands remain required.

The producer builds the main App and native tests, then the complete UI runner.
It runs zero product tests. Debug build success is not Release, physical-device
acceptance, or TestFlight acceptance.

## Additional compiler proof

Every selected native test source is matched to its exact source-before bytes
and an actual AnytypeTests SwiftFileList. This includes the two original focus
sources and MiniApps native preparation, plus the complete list chosen at the
root freeze. Every copied UI Swift source is required, including T5 and MiniApps.

Each accepted FileList must occur as an `@<absolute path>` input to a real
`swiftc -module-name <target>` command in the corresponding original phase log.
`WriteAuxiliaryFile` or a retained stale FileList alone cannot qualify. The
original FileList bytes are retained with its original path, SHA256 and required
source paths. Case-normalized paths must resolve to the same actual file.

UI copied files are checked before and after compilation. The entire generated
project and scheme inventory (file bytes, permissions and directories; symlinks
rejected) must remain identical. Each invocation witness records a one-based
line number and SHA256 of that exact UTF-8 line **without its newline**.

The original receipt gains these fields:

- `originalUICopySHA256`
- `uiCompilationProof: {path, sha256}`
- `nativeCompilationProof: {path, sha256}`
- `sourceBeforeSHA256` and `sourceAfterSHA256`
- `controlAdmission`, binding the root admission, adapter and original producer.

The successful status remains
`PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE`.
`controllerSHA256` identifies the actually executed expanded producer, with the
proof helper bodies embedded, rather than the orchestration adapter.

## Forward staging

`stage_wave3_source.py` requires an exact plan SHA and accepted App SHA. It first
revalidates all retained original source/Products bytes, modes and links against
the immutable Wave2 preservation receipt. It checks that shared App Products
still match their preserved original and that the old queue/compiler is absent.
It then fetches the exact local bundle and performs `git merge --ff-only` into
the clean physical main14 source. It never resets or restores an old source.

If the canonical SDK pin changed, the old materialization is moved to a new,
retained directory after identity validation. The frozen source's original
`prepare_sdk.py --source` materializes the exact canonical revision and
`--check` verifies it. The supplied producer Git source remains read-only. No
native binary is rebuilt or replaced; the existing native framework must match
the admitted full inventory. The UI DerivedData clone is private to the new root.

The stager writes a draft build admission with actual staging, cache and SDK
receipt hashes, keeping `readyForBuild: false`. Root verifies it and supplies the
final accepted source/pins before execution. Failed stages preserve their
observed source and evidence; there is no automatic reset or retry.

## Measured resource admission

The physical main14 App compiler intermediates and SourcePackages are absent.
Original App15 intermediates occupied 3,713,556,480 bytes. The existing reviewed
App estimate is 6 GiB, including package checkout/relink allowance; the UI phase
estimate is 1 GiB, sequentially. These are estimates, not a measured future peak.
The unchanged producer requires each phase's allowance plus 512 MiB concurrent
growth and its existing 2 GiB emergency floor. App admission is 9,126,805,504 bytes.
The original monitor records actual free space and can terminate only its owned
build process group. There is no automatic queue or cleanup.

The SDK cancellation cache is protected while its owner finishes the bounded
EOF/drain follow-up. Sources, Products, binaries, dSYMs, test results, archives,
signing material, accounts and simulator data remain protected.

## Commands after root freeze

Use the installed Python 3.12; the system Python 3.9 lacks `hashlib.file_digest`.
Fill every template field with verified values and retain each input file SHA.

```sh
/opt/homebrew/bin/python3.12 -B stage_wave3_source.py \
  --plan ROOT_PLAN.json --plan-sha256 ROOT_PLAN_SHA256 \
  --accepted-source ROOT_APP_SHA

/opt/homebrew/bin/python3.12 -B wave3_shared_build.py \
  --admission ROOT_BUILD_ADMISSION.json --admission-sha256 ROOT_ADMISSION_SHA256 \
  --accepted-source ROOT_APP_SHA \
  --original-producer EXACT_204F8FBB_BUILDER.py --output NEW_CONTROL_OUTPUT
```

The second command prepares the exact expanded producer without invoking Xcode.
Adding `--execute` to a fresh output preparation explicitly invokes that producer;
there is no automatic resource wait or launch. Both the adapter output and the
producer build evidence root must be new. Root owns that invocation decision.

`test_wave3_shared_build.py` tests only admission/evidence controls, including
stale, missing, duplicate, changed-source and wrong-module compiler inputs.
Passing those controls is not App or UIKit acceptance.
