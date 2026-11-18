# Linux native transport and current-read authority evidence

[Run 44216678261, attempt 1](https://github.com/davidpovarsky/anytype-swift/actions/runs/44216678261)
completed successfully on 2026-11-18 at 01:34:12 UTC (run metadata update time).
The exact published integration source is
`8ba9728e00d6d09f2d1a8546b0598de66aececc1`, including native host `12bef033a3fd217b67c0e9f2af77e242b487fad6`
and the current-read guard `b815465f096b1786bb41d21c25248e9986db25ee`.
Heart is `d98420b1113536afd08cde6de9a5816f6d27ffff`, Go 1.26.5 linux/amd64.

The downloaded artifact ZIP digest matches GitHub's artifact metadata.
All eight Go-source hashes in the receipt were compared with the exact published
Git blobs, and the raw log hash matches the receipt. Files here are byte-for-byte
artifact copies; no local rerun or generated replacement log is used.

Result: **19 top-level tests + 39 subtests passed, zero failures**.
The two helper entry points are skipped in the parent test binary and executed
in their intended subprocess tests. Total runner time was 25.393 seconds,
including compilation. Read-authority tests passed for an unrelated key and for
real Reader/Guest admission followed by locally verified signed removal and
read-key rotation, with an existing projection left intact.

The actual two-process AnySync protocol proof also passed: independent native
stores, generated SpaceSync DRPC over TCP loopback, native CID/signature/ACL
history verification, offline merge and conflicts, observed removes,
concurrent replacements, committed-process exit/retry and projection recovery.
The log records final native-change counts A=13 and B=13; B saw eight DRPC
requests, eight responses, 11,881 payload bytes and eight signed changes.
Tampered wire data was rejected with an incorrect-CID error.

## Acceptance boundaries

- This proves current **locally known** read authority. It does not claim
  knowledge of revocations not received by an offline client.
- Writer-revocation follow-up `29238ab189a2b1f3a203d1dbe27bcbcce804eb14`
  was published after dispatch and is **not included** in this source or count.
- The native protocol proof is isolated and uses two devices of a disposable
  account. Production peer authentication, ACL transport/coordinator acceptance,
  middleware, hidden SmartBlock lifecycle, search/export/cleanup, target-block
  races, RPC/Swift/iOS and full T2 acceptance remain unproven here.
- No user account data was changed and no application capability was enabled.

See `manifest.json` and `receipt.json` for immutable source, artifact and
per-file hashes. Existing task acceptance remains open.
