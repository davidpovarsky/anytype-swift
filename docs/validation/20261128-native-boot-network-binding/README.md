# Native boot network binding — W1 source delivery

## Acceptance state

This commit contains reviewed implementation and test source. It has not been compiled or run. The actual Oracle preparation only transferred exact source, joined before-images to the current source manifest, and formatted seven Go files. The source receipt and manifest are retained beside this document. Existing Native8ac and Navigation26 acceptance does not qualify these changed inputs.

The problem is an identity gap during host startup: the Swift owner needs an expected network identity from the exact native boot before it can admit account/run-bound HTTP results. Taking the expectation from that HTTP result would make the comparison circular.

## Implementation

The existing native configuration parser resolves nodeconf once, after the original push and P2P defaults are applied. The bound-start path fixes those exact YAML bytes in the config sent to the original shared lifecycle. It returns the exact network identity with the successfully bound address. Failures, including an already-running engine, return an empty binding.

The legacy embedded.Start, gomobile StartWithResult and AnyLibStartResult ABI remain available. Additive exports provide the new identity:

- embedded.StartBound returns BoundStartResult.
- gomobile StartBoundWithResult returns BoundStartResult.
- AnyLibStartBoundWithMode returns the new AnyLibBoundStartResult struct.
- AnyEmbeddedSession.expectedNetworkID is an immutable, nonoptional String.

The new Swift runtime uses the new exports and validates their returned identity before publishing a live session. Invalid address or identity causes native shutdown. No second YAML parser, account lookup, HTTP-derived expectation, default network constant, or optional identity fallback is introduced.

## Native source composition

Seven native source/test files are carried under Tools/AnyEngineValidation/native_boot_network_binding_20261128/overlay/any. Their paths are relative to the existing Any native source tree. The current base source manifest is 8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b. The original embedded.go before-image is retained and must match exactly before composition. The six other native files are additions.

W3 owns composition with the separately qualified N24 backend, creation of the successor unified source manifest and framework, updating its exact source/version profile, and Apple integration. The old 8ac framework does not export the new symbols. The two changed Swift module files require the matching successor artifact.

## Required verification

The planned Go scope contains six new parent tests plus one affected retained legacy method:

- Four new embedded tests cover native-parser identity, unchanged official/custom defaults, ten invalid-input cases before filesystem access, and real account-free managed start/health/stop/restart.
- The existing embedded.TestStartAddressStop is affected by the shared lifecycle extraction.
- One gomobile-tagged wrapper test checks success and failure identity propagation.
- One C-archive Go-core wrapper test checks success and failure identity propagation.

These are seven parent methods and ten named subcases. They are not seven or seventeen observed passes. The C-core wrapper test does not prove the exported C ABI or generated Apple bindings.

The existing Apple test AnyEmbeddedRuntimeTests.testRealManagedRuntimeLifecycleAndControlBoundary gains two assertions: the expected identity from the initial custom launch and the identical expected identity after restart. The changed method requires execution with the matching new framework. All unaffected accepted evidence should be retained without replay.

No original migration operation, account, network scenario, FilesV2 workload, Apple build, or runtime test ran during this source preparation.
