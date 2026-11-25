# Current shared Hanlin SDK integration

Both engines resolve the single immutable canonical SDK at 30e5f09f8494d913fa36e75f877b541020c92ee0. This integrates cache/composer c72, MiniApps08ef, the tool-continuation cancellation fix and the existing strict MiniApps/account boundaries. SwiftAI is pinned to abf0921c6e89e6521cc2b510ff11016b45a0ef08.

All 959 canonical files were verified against the Git archive. The existing prepare_sdk script materialized the same 959 hashes; the previous SDK44 snapshot is retained separately.

On the Scaleway Mac the unchanged original affected core suites passed 48 actual methods: 44 ChatCore/PlatformContracts methods and 4 original SwiftAI producer methods. The process exited 0, all canonical sources and dependency pins remained unchanged, and all 48 individual pass lines plus the exact 4+44 process totals were independently qualified. The initial observer parser omitted the optional “in N suites” phrase and reported a result-parsing failure after the successful execution. Its original receipt and error are retained alongside the unchanged compressed log and qualified result; no test was rerun or weakened.

The complete original target source closure was used. This is native component evidence, not application UI acceptance or provider billing evidence. The final Pinkha rebuild and affected Hanlin UI tests remain required. An actual independent MiniApps producer compatible with the final pin remains required; no producer identity check was removed.
