# Heart test-fixture compilation correction

The original [Release run 44954248363](https://github.com/davidpovarsky/anytype-swift/actions/runs/44954248363) failed during test-target compilation. No native preparation, product UI method or postflight executed. The original failure remains a failure.

`SimpleTableTextPersistenceTests.swift:377` supplied an existential `any MarkdownListener` through a nil-coalescing expression to an initializer that requires a concrete `some MarkdownListener`. The correction in `c338989d4c` changes only the fixture parameter and default object to the existing concrete `SimpleTableMarkdownListener`. The eleven test bodies and their assertions are unchanged.

The source Git blob is identical in that failed Release run, SDK run 44956239736 and queued T5 run 44958628074. T5 was therefore cancelled before runner allocation or any step. SDK was already compiling and is allowed to reach its terminal/cache preservation boundary. The failed Release build successfully saved its compatible compilation cache.

Corrected pending runs are [Release 44960843842](https://github.com/davidpovarsky/anytype-swift/actions/runs/44960843842) and [T5 44960856322](https://github.com/davidpovarsky/anytype-swift/actions/runs/44960856322), both at `87a543d81b51ca16d624d2f21f9ce50d70c0ab5b`. Actual Apple validation of the correction remains pending at this checkpoint.

`qualification.json` is a derived review of original artifact 14729590934, with explicit archive/original-log hashes and the exact original compiler diagnostic. Files in `original/` are copied without modification. The complete original archive/logs remain attached to the failed GitHub run. No successful retained test was rerun to create this record.
