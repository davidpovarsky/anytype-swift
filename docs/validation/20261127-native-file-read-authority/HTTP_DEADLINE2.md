# Actual HTTP deadline qualification — 27 November 2026

The two synthetic HTTP deadline controls passed on Oracle. This qualifies the
absolute request deadline used by the pending current-authority HTTP controller.
It does not qualify the SDK read-authority fix, the native executable, or the
original removed member's file access.

## Actual result

| Item | Recorded result |
| --- | --- |
| SentinelX job | `job_dcebf6555a68` |
| Time | 2026-11-27 11:45:22–11:45:23 UTC |
| Outer receipt | `0a2da3fdb8c1d962a0e6d74e750292dc934ff5c826c0b025bb38702717394db6` |
| Status | `PASS_TWO_ACTUAL_HTTP_DEADLINES_AND_OWNED_CLOSURE` |
| Actual methods | 2 run; 0 failures; 0 errors; 0 skips |
| Slow body | 350.355 ms; 11 successful 30 ms drip writes |
| Slow headers | 350.348 ms; 11 successful 30 ms drip writes |
| Socket operation timeout | 100 ms in both controls |
| Absolute deadline | 350 ms in both controls |
| Owned process groups | 1; exit 0; positively absent; no forced cleanup |
| Native/account/compiler operations | 0 / 0 / 0 |
| Replayed lifecycle controls | 0 |

Both controls require the actual absolute-deadline exception while successive
socket operations continue to make progress. They verify that a deliberately
blocked alarm signal is unblocked for the request, the prior signal handler and
mask are restored, the owned timer is cleared, no alarm remains pending, and
the synthetic peer thread has joined. Neither peer recorded an error.

The exact original command log is retained on Oracle with SHA256
`b9ce51c1fb0859f12d55ee6680bfd4511e5fae602c1b86a8a1b180f50313d196`.
The nested control receipt is
`c4f82233c59a4025cf5236cc8f0c601fb72c2084beaa4e220fc30ad03b793213`.
The outer receipt includes both control results and the complete command
closure row. Oracle evidence remains at:

`/mnt/development/projects/evidence/pinkha-current-authority-http-controls-20261127/attempt1`

The observed Python executable was `/usr/bin/python3.12`, version 3.12.3,
SHA256 `c86f21d0da9290ece2d7d49a3f7ed52aed59cb029abdf0ea25c79634f6cbe960`.
Peak owned output was 20,480 allocated bytes. The original 2 GiB root and
512 MiB development live floors remained in force.

## Exact source and reused evidence

| Source | SHA256 |
| --- | --- |
| `verify_current_authority_http.py` | `26ed736be9e5ddb8def2af26de6648bba4ab8ad85f55be91bc045dc215de4b84` |
| `http_deadline_controls.py` | `4ffd006042ede3f0cb494ea3fa89ece8b3f68bce0c4873887b9d9d27ccfee876` |
| `qualify_http_deadlines.py` | `77a6556a4b4da6cdecf3b8db5df621752b69547e638870b30a75e808d8f778f0` |
| `owned_swift_commands.py` | `f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56` |

The owned-command helper reuses the five actual lifecycle controls already
recorded in receipt
`040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d`
and published by the cutover lane in commit
`1aaff678cb75c86f356626817244c57529b36f4f`. Those controls were not repeated.
The deadline qualifier binds the helper and original controller bytes before
and after execution. The helper retains the child leader unreaped until its
group has drained and latches positive absence before returning.

## Remaining product acceptance

The original native revocation failure remains unchanged:
`ecd4e58378cbb82731926536e82fca655da64ee156057ba411a242c95942c2ab`.
Its removed member received a successful canary response from the old native
product. This new deadline receipt is not a correction of that product failure.

The source-only continuation requires a separately qualified native product
from the exact 1,607-member public source union. Its prerequisites are the
21 signed ACL/lifetime methods with 14 named subtests and the two new actual
SDK `Files.Open` methods. Those SDK/runtime gates are not asserted as passed
by this document. After the product qualifies, the original-pair continuation
has fourteen strict `403 / acl.forbidden` checks across online and fresh
OS-offline processes, with no role, invitation, upload, retry or restoration
write. It stops before reading any unexpected successful file response body.

No retained private account, key, database, signed-record export or old snapshot
was accessed by this deadline qualification. The native continuation's main
function was not invoked.
