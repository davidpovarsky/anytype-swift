# Empty Swift Testing selection: original failure retained

Run44970683706 at749edf96e283e759fd7f566e7f9ba26b24289f08 successfully requalified the original ten Kit methods without rerunning them. Its new compiler invocation built successfully and exited zero, but the five-name expression containing word-boundary and parenthesis assumptions selected zero methods. Both target streams explicitly ended with zero tests, and the strict qualifier correctly failed. Any, session and R05 stayed unexecuted.

The corrected selector uses the five unique literal method names, following Swift Testing's ID-pattern substring matching. Actual descriptors, source identities, method and case terminals and run closure still enforce the exact selection. No other product tests were added or repeated. Only the affected selector control was rerun; its original log is in the adjacent observed-results proof. The original failure and all artifact bytes remain unchanged here.

[Original workflow](https://github.com/davidpovarsky/anytype-swift/actions/runs/44970683706)
