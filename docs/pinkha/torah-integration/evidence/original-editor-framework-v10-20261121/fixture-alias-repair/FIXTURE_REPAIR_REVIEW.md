# v10 source-control fixture repair

Run 44955835428 at 2b8cb06eede49af0b3f09aa91d87686cb28abe82 passed actual source admission, then executed all 192 Python controls on the Apple runner: 183 passed, five failed, four errored, none skipped. The original framework build, native codesign, public symbol extraction, binary consumer and original app runtime did not run.

All nine controls stopped at the new successful-build import-context boundary because their shared temporary-root fixture recorded an unresolved directory alias while the original driver resolves its actual root. The repair resolves only that fixture root. The production driver, source/signature/public-surface assertions, 120-second extractor limit and original 140/120-minute workflow budgets are unchanged.

Nine original failure identities were reproduced with a real filesystem alias and all nine pass after the one-line fixture repair. A new exact regression exercises the unchanged original whole-driver build/signature/consumer ordering test through a real alias. The previous 183 passing cases were not rerun locally. Discovery preserves all 192 original identities and adds exactly one, so the mandatory Native workflow now requires all 193. These portable controls use explicit Apple-tool doubles and confer no Apple build or runtime acceptance.

The first portable reproduction attempt omitted the existing Amplitude binary fixture for its sixth case; that failed setup is retained in the control evidence. The required immutable fixture and original package pins were then supplied, without changing their assertions. Five already-observed reproductions were reused; the remaining four and all nine repairs actually executed.

The original GitHub artifact and original job log are preserved under native-result-44955835428. The neutral editable-Host SDK draft is not part of this change.
