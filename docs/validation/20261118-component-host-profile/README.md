# One fresh build for the Wave-15 component contracts

The additive `wave15-component-tests` dispatcher route selects the `wave15-components` profile. It performs one fresh Debug-Anytype build and one actual XCTest execution containing the existing SDK, editor and UIKit/Properties suites. Individual profiles remain available and keep their original behavior.

| Component | Reviewed methods | Declared argument cases |
| --- | ---: | ---: |
| SDK06 | 67 | 68 |
| Quote insertion editor | 10 | 12 |
| UIKit direction, gestures and native Properties | 41 | 57 |
| Combined source contract | 118 | 137 |

These are source inventories, not Apple results. The actual run has not been dispatched. The known journal failure must be diagnosed and fixed first.

The combined profile invokes each original source validator independently. Editor and Core retain their exact argument validators and the Core source manifest. The SDK budget method additionally requires the original `budget: Int` declaration and the two literal expressions corresponding to 1048576 and 8388608. The actual argument names are bound to the original SDK63 xcresult tree, whose SHA-256 is recorded in `source-validation.json`. That older execution failed ten methods and does not prove SDK67.

The raw xcresult summary is preserved once. Original case nodes provide separate component details; no component summary is fabricated from the aggregate. The total must equal either the actual method count or the complete source-bound argument count. Unknown descendants, missing methods, aliases that duplicate a method, failed/skipped arguments, altered budgets and a forged 999/999 aggregate are rejected.

Source SHA, run/attempt, actual OS27 ARM64 iPad, exact dependency pins, signed App/test executable hashes, r14 runtime bytes and post-execution source verification remain the existing gates. DerivedData must still be fresh. No stale product cache or omitted native build is introduced.

Root validation completed 49 controller tests: 47 passed and two real POSIX process controls were explicitly skipped on Windows. Independent source review identified the aggregate-count issue; its exact counterexample was repeated after the fix and rejected. No additional shared-state collision between SDK/Editor and Core was found in that review. This does not assert global serialization of Swift Testing suites.

Native UI, real account writes, provider networking, synchronization between App clients and physical-device guarantees remain separate acceptance requirements. Original raw Apple results will determine any component acceptance.
