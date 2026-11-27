# Retained production account storage-limit observation

## Observed result

A single native `GET /v1/account/limits` on the existing synthetic production test account returned:

- Storage limit:0 bytes.
- Storage usage:21,070 bytes.
- Storage answer timestamp:2026-11-27T05:42:45.579472201Z.
- Shared Space limit:3; answer timestamp:2026-11-27T05:42:46.340108716Z.

The observation took3.787 seconds and retains its original receipt in `original/result.json`, SHA-256 `aa61aadca348b2c89bc0321f6239a299c4d2fb3d62014366e1c4b707defef100`. All nine exact HTTP responses are included. The account is the retained test identity bound in the receipt; this is not a statement about the user's main account or billing plan.

| Original file | Bytes | Locally cached | Durable |
| --- | ---: | --- | --- |
| BEaHYwGfZiM, small binary |8192|true|true|
| YhnuHkqoHza, image |49363|true|false|
| AXSnqoZ52w3, large binary |8388608|true|false|
| ahKeFKn7uta, thumbnail variant |12420|true|true|

The image and large file both remained `limited` with native `filestatus: storage limit exceeded`. Fresh status rows each reported attempts1; this is recorded as observed and is not used to infer durable retry-counter continuity across earlier process/copy scenarios. Every retained CAR file had exactly the same bytes, size, allocated blocks, and hash before and after this read.

## What remains open

`cloudQuotaRecoveryAccepted` and `originalFourFileCloudCustodyAccepted` remain false. This observation does not raise a quota, claim cloud recovery, or replace the prior actual four-file failure. The prior receipt `84810888ba0be79546278f90286ff4da9e0a6052daf83922e787132ad628b59c` remains a FAIL for quota recovery with qualified local preservation and refused nondurable offload. The separate accepted two-small-file cloud transfer is unchanged; it cannot establish large-file or original-image custody.

No explicit upload retry, file creation, offload, invite, or account creation was called. The original P2P-disabled production configuration and native source were unchanged. The process exited0 and its group was absent. A read request does not imply the native account service performs no background protocol work; both observed local/global peer counts were zero and production-node sync was observed separately.

## Consumer interpretation

See `docs/architecture/retained-cloud-file-quota-contract-20261127.md`. Expose the actual reported allowance/usage and freshness, preserve locally cached bytes while a file is nondurable, and retain the native limited status. Do not turn an accepted retry request or a cached read into a cloud-custody claim.

The exact executed controller is `Tools/AnyEngineValidation/native_file_durability/read_cloud_account_limits1.py`, SHA-256 `f934b734522c6feae41c80f313fe6405bef69438e42b9f4e33e092da45248238`. It is an exclusive one-time read qualification against the retained account, not a scheduling or repeated-retry instruction. Private account directories and credentials are not published.
