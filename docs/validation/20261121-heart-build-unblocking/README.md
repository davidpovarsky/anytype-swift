# Heart acceptance preparation: original failures and narrow corrections

## Actual evidence, 21 November 2026

- Release run [44948101231](https://github.com/davidpovarsky/anytype-swift/actions/runs/44948101231) at c6ecc8ae89891b335434faec36f40b3b63e79334 completed the App/native-test build. Its strict source gate then stopped at a changed App Package.resolved. All three native preparations, six UI methods, and the Properties postflight are NOT_RUN.
- The original lock is 12076 bytes/SHA256 5b2dc85295e14c33e750d9a9b33e2422ef0a56af8049cdc4638b8508c8ddfb07. The generated lock observed by the gate is 12595 bytes/SHA256 e40f48f7844bdd7c1d2423532934a4016e47dc459d1ba4dcf70eee263fd08df8. The original build log includes swift-markdown and cmark-gfm; both are absent from the published lock. No lock byte or origin hash is invented from that log.
- Artifact14725673626 outer SHA256 0cea58461c08c752cb714c176a38c138fda7117cc1aed9e9afe93d51289f9a79; inner SHA256 19d874c26fd3c80bd3aba5b8afeae21363e67f0112d870c119ea65367d3a56b9. Both original downloads were independently hashed.
- The separate resolve-only route generates the exact lock for review without an App build or test execution. Its first run is [44952889349](https://github.com/davidpovarsky/anytype-swift/actions/runs/44952889349). Existing dependency revisions must remain fixed; only the two observed additions are allowed.

## SDK06 shared editor selection

- Run [44948419091](https://github.com/davidpovarsky/anytype-swift/actions/runs/44948419091) at a257332b274a7b2252d3645ebeb58af0d64bb3b3 successfully built and linked the Debug App and test executable.
- The original shared-editor xcresult reports totalTestCount=0, passedTests=0, failedTests=0, skippedTests=0, result=unknown. Its actual log says the Swift Testing suite opened and executed zero tests. The CLI method identifiers without Swift Testing signatures selected no cases.
- The wrapper now selects the one declared suite, matching the established native selection convention. The unchanged source declaration and original raw-case validator still require exactly10 methods and15 argument cases. No empty or incomplete result is accepted.
- Only the affected controller method was rerun locally: PASS, with both original summary representations (10 methods or15 cases). This is controller evidence, not Apple test execution.
- Native acknowledgement7 and the SDK06 native preparation/UI remained NOT_RUN after the zero-test stop. The next necessary Debug App build will combine the pending components with the new table cases, rather than add another component-only build.
- Artifact14726135226 outer SHA256 fa961b3f5e2df8998255def961b320556a731961b3785ac89e299d4207d0b73b; inner SHA256 627ebf13059a7df71f27db14fcc9ef492646d79302fe4d55774a446490b96b07. Original raw summaries and test log were inspected.

These are scoped build/controller findings. Editor persistence, Properties, SDK06 and physical-device acceptance remain open until their actual tests pass.
