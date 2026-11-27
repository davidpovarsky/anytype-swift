# Exact hosted RTL components — prepared, not executed

This additive profile selects the two new UIKit suites: numbered markers
(two methods/four cases) and native empty paragraphs (four methods/six cases).
The original focus suite remains a separate 22-method/34-case lane. The
profile does not run a build, create a simulator, admit an application or
grant UI/RTL-matrix acceptance.

## Source and compiler binding

The source changes are published separately as marker commit `4d3e2a8c` and
native-empty commit `087b6894`. `rtl_hosted_profile.py` pins the two test files
and all three affected production files. Its source-only inventory is not
sufficient to start tests.

After the one shared qualifier admits the selected Wave 3 producer, use:

```python
contract = rtl.source_contract(
    source_root,
    source_commit=admitted_source_commit,
    native_compilation_proof=admitted_producer_receipt["nativeCompilationProof"],
)
```

The proof must have schema `pinkha-exact-native-compiler-inputs-v1`, the exact
admitted source commit and the original non-execution status. The two test
files must occur in `requiredSources`, with their exact synchronized
physical source path, size and SHA-256. The profile re-reads the retained
native SwiftFileLists and the pinned original build log. Each selected file
must appear exactly once in a genuine `AnytypeTests.build` FileList; each
recorded compiler witness must match its exact log line and an actual
`swiftc -module-name AnytypeTests @<original-filelist>` invocation.

The next Wave 3 build admission must therefore include both paths in
`selectedNativeTestSources`:

- `AnyTypeTests/Pinkha/PinkhaTextBlockLeadingMarkerTests.swift`
- `AnyTypeTests/Pinkha/AnyNativeEmptyParagraphDirectionTests.swift`

UI-target or package-target compilation does not satisfy this requirement.
The existing package `PinkhaAnyUITests/AnyNativeTextRendererTests.swift`
remains unchanged and is not selected here. Full source, Native manifest,
SDK, generated UI and complete product checks remain in the shared
qualifier. No a089/App16 preparation is repinned or relaxed by this module.

## Existing host integration

The module adds no host fork. The next reviewed host materialization needs
one `rtl-hosted-only` lane with `kind == "rtl-hosted"`:

1. Build the contract above from the admitted producer receipt.
2. Route `invocation_selectors` to the new module's same-named helper. It
   selects the two complete suites, preserving the original Xcode27 Swift
   Testing workaround. Direct display-signature filtering is not used.
3. Route `host_validation_module` to this profile. Keep the original native
   descriptor inverse, enumeration, command/result-bundle retention,
   runtime/device checks and product integrity checks unchanged.
4. Demand the exact six compiled method signatures in enumeration and the
   six methods/ten distinct literal cases in actual result data. Re-read
   `source_contract` before issuing the final lane result and require it to
   equal the initial contract.

The result and argument functions call the original
`run_host_tests.validate_results`, `wave15_core_profile.validate_arguments`
and `shared_editor_existing_build.enumerated_identifiers`. The declaration
parser is also unchanged. The original native result validator still
requires the owned OS27 arm64 **iPad**; this component lane is separate from
the iPhone/iPad, Hebrew/English, light/dark actual UI matrix.

## Portable qualification

Four portable controls pass against synthetic compiler/enumeration/xcresult
payloads. They reject changed source, a missing selected test, a package
target, a fabricated compiler-log witness, a different source commit,
incomplete/extra/disabled enumeration, missing argument cases, unexpected
methods and a wrong component device family. They also reject suite
filtering with a source-only declaration contract. The original first
control receipt is retained; the second includes the Xcode27 suite-filter
integration check.

These controls launch only Python and a temporary local Git index. They do
not invoke Swift, Xcode, XCTest, an app or a simulator. Their logs and
receipts are explicitly labelled as portable synthetic schema controls.
No actual native compilation proof or current-product XCTest result exists
in this package; those must come from the coordinated shared build.

The Wave 2 Torah agent independently reviewed the source, compiler witness,
suite selection and result binding. The review found no concrete evidence
binding or integration blocker. It was source review only; that reviewer
did not rerun the portable controls or any Apple tests.
