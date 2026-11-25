# F selection repair — 25 November 2026

Run45535451242 at406fd73 compiled the current App, native target and UI runner successfully, then stopped before any acceptance command. The original Xcode27 descriptor has one configuration with DeepLinksTests, AnytypeCoreTests and AnytypeTests, and omits OnlyTestIdentifiers. The controller incorrectly required a one-target descriptor and an explicit nine-suite filter.

The repaired controller selects exactly one enabled AnytypeTests target, binds an omitted filter to the hashed original successful nine-suite build receipt, rejects explicit wrong/empty/duplicate filters and any skip filter, retains the exact target environment and host/bundle checks, and proves an inverse to the original descriptor. Original product assertions and enumeration/result requirements remain unchanged.

Seven affected controller methods passed; the recorded tool response is retained in controller-observation.json. This proves controller behavior only. The complete original native/UI products were captured before admission and uploaded in artifact14987446860; recovery is underway, with no original pass invented and no build source relabelled.

A separate completed-run retention helper moves only the current coherent run's four owned build roots after the original cleanup check and explicit cache save. It refuses symlinks, active path users, foreign run/source identity and existing destinations. This preserves full products for future retries without authorizing reuse on its own.

Actual F/T5 execution, final integration and distribution remain open.
