# Remove notification permission query from the account-state consumer

## Evidence and cause

The retained Page154 run 45450456097 failed `home-not-ready` with the original App and UI products. The zero-build local diagnostic `1795544704330173000`, controller source `8db28ea73f2643396d0da3ebeea01360621fc851`, independently admitted the original products and enabled only the existing closed startup observer. Its completed native preparation passed; its original UI method failed with its original assertion and deadline.

The 14 closed phase events show authentication returned, `ApplicationStateService.state` was set to `home`, and the view model was still `launch` when notification registration began. The system notification-settings await never returned before the original UI deadline. This prevented the sequential application-state consumer from finishing `.launch` and consuming `.home`. Full evidence is in `docs/validation/20261124-page154-startup-observation` at donor `7ca06e40ac21211d25ad86546cf7893196f64e79`; diagnostic results grant no acceptance credit.

## Product change

Account selection schedules notification registration in one tracked task and returns to the state consumer. The task weakly references the view model; account-state transitions away from home cancel it. Registration checks cancellation on MainActor immediately before calling UIApplication, so a delayed OS response cannot cause a cancelled task to register later. The notification authorization policy, prompts, selected account, state transitions and UI acceptance assertions are unchanged.

## Validation

`syntax-only.json` records successful Swift 6.4.3 Linux parsing of both modified source files and their exact SHA-256 values. This is syntax evidence only: no Apple typecheck, App build or acceptance test has run for this product change.

Next: freeze this source with the focused RTL repair, preserve Debug-Anytype and native154, build the Page App/UI once, then run the original native preparation and Page154 UI method on a fresh owned simulator. A separate coherent Release build will include this same product source. Do not replace the home assertion, increase its wait, or credit the diagnostic as acceptance.
