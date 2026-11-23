# SDK06 early product evidence ? 23 November 2026

## Reason

SDK consumer [45047827580](https://github.com/davidpovarsky/anytype-swift/actions/runs/45047827580)
built the application and native test bundle successfully, then stopped at the
exact enumeration gate before any product test executed. Only a product hash
inventory was retained. The original Products tree and xctestrun were absent,
so that build cannot be asserted as an available reusable binary.

The selector correction already exists in acceptance base
c8839d7ef090c95197443227e4c51fac471a07e6. This change preserves the next actual
successful build before signature, runtime, dependency and enumeration admission
can fail. It does not change those gates or any method/case assertion.

## Change and ownership

All edits are downstream acceptance infrastructure:
- Tools/PinkhaSimulatorGate/early_build_products.py: archive original
  Build/Products, filesystem modes and links, plus the optional original
  Build/PinkhaSourceInputs.json, before admission. The manifest records exact
  archived bytes and original source/run identity.
- run_wave15_acceptance.py: SDK-only capture immediately after successful build.
- Tools/PinkhaNativeDerived/package_evidence.py: include only the three exact
  archive destinations sdk06-early-products, coherent-native-early-products
  and coherent-ui-early-products, each with filename BuildProducts.tar.gz.
  Arbitrary or incomplete archives are not added to the upload ZIP.
- test_early_build_products.py: four new focused controller/transport controls.

The shared capture helper is also available for the separately owned coherent
Release native/UI build call sites. Those call sites are outside this change.
No original Anytype/Hanlin source, generated source, native framework, source
retention map or acceptance assertion is changed.

## Executed checks

python3 -B Tools/PinkhaSimulatorGate/test_early_build_products.py -v:
**4 PASS, 0 failure/skip**, on Linux ARM64 Oracle. Original output is
focused-controls.log; its SHA256 is
d0a6d67db43adf1296378aec67d9e5ece260732b7994ea68d78d120dfbbb89e4.
focused-controls.json binds the four actual source hashes.

The tests cover exact archive survival after later product mutation/failure;
original configuration, executable mode, symbolic/hard-link preservation;
refusal of stale destinations, unknown scope and special files; the actual
packaging script retaining precisely the three allowed archive paths; and
executing the SDK controller until a controlled first admission failure to
prove capture occurred earlier.

These tests exercise fixtures and controller code. **No Apple or application
test was executed here.** Existing selector and other accepted controls were
not rerun.

## Scope of future reuse and next execution

Archived products are labelled observed bytes only:
build_reuse_enabled=false, every_entry_build_origin_verified=false,
native_acceptance_reused=false, ui_acceptance_reused=false.
Signatures, original build provenance, dependencies, source equality and real
test execution still need the existing admission/acceptance checks. Links are
preserved without following them; their targets require review before any
future archive extraction/reuse.

The acceptance branch retains exactly the two shared module trees executed by
coherent Apple producer **45046643716**. Current shared commit
e7fd39b763d3d0244996c207552096f169de85ed contains additional semantic-anchor
changes in PinkhaKit, so the strict module-equality guard cannot admit that
producer directly for current shared. Run this scoped SDK continuation on the
accepted-module branch and record its scope honestly; requalify the current
module combination before claiming current shared/full acceptance.

Next Apple selection after integration/source retention:
- dispatcher torah-inspector-ipados27.yml, route wave15-acceptance;
- lane hanlin-native-shared-editor, device ipad, language en;
- runtime r15-attachment-authorized-current-read-v1, source run 45046643716;
- enumerate exact 23 selected methods/32 terminal cases, then actual component
  execution, acknowledgement7, native preparation1, mounted UI1.

No workflow was dispatched by this implementation checkpoint. SDK06 and full
release acceptance remain open.
