# Actual source-generation preparation failure: run 45052270280

The original generation gate failed before any generator was built or executed. This packet retains the original failed run and its finite observer; it does not claim a generated RPC, message compilation, native test, SDK build, or runtime acceptance.

## Exact run and failure

- Repository: `davidpovarsky/anytype-swift`.
- Run: `45052270280`, attempt 1, job `137299807140`, push at `65dae331936645cf807349f1fcd10db2ba973f9b`.
- Control source parent: `fa022fdffa25ec93d8c8c324f20889e526fdf498`.
- Frozen execution manifest SHA-256: `800c0745ddc36537c443e17f9d984c98a11fd22c4d825c4a935ffa4f8d264ee3`.
- Commands 1–7 succeeded. Command 8, `baseline-clone-swift`, returned 128 after 0.566 seconds without a timeout.

The local `git clone --no-hardlinks --no-checkout` tried to serve the SDK's sparse/promisor repository through upload-pack. Git reported that lazy fetching was disabled and that promisor object `aa9f7c5d1b62e822814328e66427878993025f63` was missing. This is a source-copy preparation failure. It provides no evidence that an original generator or RPC source failed.

The exact executed `actions/checkout@v4` revision was `11d5960a326750d5838078e36cf38b85af677262`. Its original source selects `filter=blob:none` when sparse checkout is requested. The SDK input retained the six reviewed sparse scopes; the failed local clone attempted to pack objects outside that materialized checkout.

## Retained evidence

`Heart_Schema_RPC_Generation_45052270280.zip` is the unchanged GitHub artifact `14766048443`, 866,386 bytes, SHA-256 `9e12af3ae19e07b06cc3ee4215d218b62e0092525921cece5c81759aac802b01`. All 30 indexed payloads and the evidence index are retained in it, including all 16 command streams and 11 failure-time original native generated files. Those 11 files are old tracked source copies, not fresh generation.

The independent verifier and root review recomputed the archive CRC, payload sizes, SHA-256 and Git blob identities, command streams and eight process-group cleanup outcomes. `VERIFIED_RESULT.json` records the actual failure. `ROOT_FAILURE_REVIEW.json` is the independent root review, retained unchanged.

The sole finite observer `job_771b8c66be59` completed successfully at 18:06:40 UTC after retaining the failed run and verifying the same archive. Two earlier read timeouts remain in its history. `WATCHER_NOTIFICATION.json` records its actual terminal job; `WATCHER_RESULT.json` records its exact observed result. Observer success means failure evidence was retained, not that generation passed.

All eight owned command groups drained, and the runner removed its owned work directory. The immutable input checkouts and evidence remained available to the action's ordinary cleanup. No additional native or app tests were selected; all earlier passed results remain unchanged.

The actual probes recorded Go 1.26.5 on Darwin arm64, Xcode 27.0 build 27A266a, and Apple Swift 6.4. No pinned generator archive download or generator executable probe was reached.

## Next bounded correction

The next source candidate will correct only the copy of the already materialized SDK checkout into separate baseline and candidate lanes. It must preserve the exact original source scopes, tools, generator routes, proto afterimages, fresh-output requirements and limited compilation acceptance. This failure packet itself contains no correction or activation.
