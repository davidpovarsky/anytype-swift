# FilesV2 durability consumer boundary

Actual baseline: 15 methods, three intended failing methods and 12 passing methods. The failures reproduced canonically equivalent but unequal account bytes, malformed successful mutation JSON, and an oversized successful mutation receipt. Original failures remain in the baseline console and result.

After the minimal shared HTTP fix, 28 actual XCTest methods passed with zero skips: the same 15 new methods plus 13 affected existing authorization/status/native-rejection/object-recovery regressions. Only AnyHTTPClient.swift changed between those two executions. Native typed writeRejected results and original partial-creation identity recovery remain distinct from uncertain acknowledgments. The original console's started/terminal sets establish the method count; the unrelated empty Swift Testing XML does not.

The additive AnyNativeFileDurability adapter preserves native limited/inflight/durable state and cached availability independently, binds exact account/space/object/file identity, requires a one-shot explicit retry approval, and returns only a scoped204 acknowledgment. It does not delete data, mint quota, retry automatically or mark a requested retry as durable backup.

See ../../architecture/native-filesv2-durability-contract-20261127.md. The adjacent native cloud-quota proof records real cached-byte preservation and persistent provider refusal. It is separate from these component passes. Apple, app integration and full native cloud recovery remain open.

Original console logs are stored as lossless .log.gz files so diagnostic trailing spaces remain exact. Both compressed and uncompressed SHA256/byte lengths are recorded; no test log was edited to satisfy source formatting checks.
