# Mounted Hanlin test provider

This is a test-owned HTTPS/SSE fixture, not a model implementation or production
provider. It validates the actual application's six provider requests, including
consent-dependent tool visibility and real host tool continuations. It cannot
read or mutate Any storage. It never calls the Any API, replaces a host, changes
application configuration, or installs trust.

## Ownership and private files

`fixture.py start --private-dir <new-or-empty-owned-directory> --safe-result
<safe-output.json> [--openssl <executable>] [--max-age-seconds 3600]` generates a
one-day ephemeral CA/leaf identity and binds one socket to `127.0.0.1:0`. The
selected port remains bound. POSIX private directory/file modes are 0700/0600;
Windows validation uses an owned temporary directory with inherited owner ACLs,
and does not claim POSIX mode enforcement there.

The starter writes `private-config.json` **before spawning the child**. Starter
and child record the same PID, process-creation identity, entrypoint/config paths
and source hash in `child-process.json`. Start success requires a real HTTPS
readiness response verified against the explicit temporary CA. Internal start
failure waits/terminates only its retained Popen child. An external timeout may
prevent finally blocks: cleanup must preserve the private directory unless the
separate stop command proves shutdown. Never remove an uncertain live child's
files, infer ownership from PID alone, or kill a process tree by name.

Private config uses `schemaVersion: 1`, the fixed contract below, canonical UUID
`runID`, `rootCAPath`, SHA256 of public CA DER as `rootCAFingerprintSHA256`, PID,
TLS paths, and a `testRunnerEnvironment` map. It contains private synthetic
credentials and must not be uploaded or printed. The map has exactly:

- `TEST_RUNNER_PINKHA_HANLIN_FIXTURE_URL` — `https://127.0.0.1:<port>/v1`
- `TEST_RUNNER_PINKHA_HANLIN_FIXTURE_MODEL` — `pinkha-hanlin-acceptance-v1`
- `TEST_RUNNER_PINKHA_HANLIN_FIXTURE_KEY` — per-run synthetic model key
- `TEST_RUNNER_PINKHA_HANLIN_FIXTURE_CONTROL_URL` — same origin, `/__fixture`
- `TEST_RUNNER_PINKHA_HANLIN_FIXTURE_CONTROL_TOKEN` — separate per-run control token

Xcode strips `TEST_RUNNER_` when forwarding these values to the XCTest runner.
The UI test types the first three into the ordinary Configure fields. It must
not introduce application launch flags or injected provider/host dependencies.

`inspect --private-config <path>` reports safe current status without requiring
completion. `verify --private-config <path> [--safe-result <path>]` succeeds only
after all six responses and all checks, with no latched rejection. A verification
receipt is **provider-fixture evidence**, not proof of a native page or Apple UI.

`stop --private-config <path>` authenticates shutdown, closes and joins the
fixture's owned accepted TLS connections, and waits for the exact child to exit
and the listener to stop accepting. Windows uses query-only process handles and
creation times, never `os.kill(pid, 0)`. POSIX uses read-only `ps` identity/status.
Stopped receipts are insufficient by themselves. Failed/uncertain stop returns
nonzero and the caller must preserve private material. Successful stop does not
delete the private directory or simulator trust; the workflow owns those steps.

## HTTPS and simulator setup

The leaf has serverAuth EKU and SAN IP `127.0.0.1`. Fixture checks use a default
verifying SSL context with the explicit temporary root. They never change host
trust. The workflow must inspect the actual `simctl help keychain`, validate its
owned simulator receipt, and add only the public root to that exact disposable
UDID. The UI test must then pass an ordinary default-URLSession readiness request
without a trust delegate, ATS exception, or verification bypass. Host readiness
does not establish simulator trust. Deleting that owned simulator removes the
trust addition; a failed setup remains a setup failure.

Primary Apple references:

- <https://developer.apple.com/documentation/xcode-release-notes/xcode-13-release-notes>
- <https://developer.apple.com/documentation/Xcode-Release-Notes/xcode-11_4-release-notes>
- <https://developer.apple.com/documentation/network/creating-an-identity-for-local-network-tls>

## Control API

All routes use the same owned HTTPS origin. `GET /__fixture/ready` is unauthenticated
and returns HTTP200 exactly `{schema:1,contract:"pinkha-mounted-hanlin-provider-fixture-v1",ready:true}`.
Other control requests require `Authorization: Bearer <CONTROL_TOKEN>`.
The model route requires the different model key. There is no reset endpoint.

`POST /__fixture/scenario` accepts one bounded JSON object with exactly these
required keys: `selectedBlockID`, `selectedText`, `unselectedText`, `documentTitle`,
`cancelledTitle`, `approvedTitle`. Optional `objectReference` and `spaceReference`
may be included only when captured from the real UI. The mounted test supplies
the actual object and selected-block IDs, exact owned synthetic texts, and unique
titles. It never fabricates an unavailable native identifier. HTTP201 returns the
current safe status. A second registration is refused; it cannot reset history.

`GET /__fixture/status` returns schema1, contract, runID, scope, state, complete,
phase, providerRequests, responsesDelivered, stopped, registeredObjectCompared,
registeredSpaceCompared, checks, failureCode, rejections and bounded requestMetadata.
It also returns nullable SHA256 fields: scenarioSHA256, observedScopeSHA256,
observedObjectSHA256, observedSpaceSHA256 and observedRevisionSHA256. No raw
request, text, title, source ID, credential, TLS material or error description is
returned. Status phase may lead responsesDelivered by one during an in-flight
flush; wait for both before consuming that stage. `complete` requires 6/6.

After the read continuation, the UI hashes the final native Space-ID line of
each real creation confirmation and compares observedSpaceSHA256. This establishes
continuity even when Space ID is not available before opening Hanlin. Shape-only
scope validation is not mislabeled as a comparison with an unavailable identifier.

`POST /__fixture/shutdown` takes exactly `{}` and returns a safe accepted marker.
CLI stop performs the additional process-exit/listener checks.

## Six request rounds

The test uses exactly three separate Sends with these prompt strings:

1. `Check the available actions without reading source text.`
2. `Read only the selected block, then offer the cancelled draft page.`
3. `Offer the separately approved draft page.`

| Request | Required real input | Fixture response |
|---|---|---|
| 0 | After Share/Cancel: no read tool or A/B text; create tool correctly advertised | `PINKHA_HANLIN_DENIED_READ_CHECKED` |
| 1 | After Share/Allow: exact read and creation schemas, second Send | `call_pinkha_read_selected_v1`, read tool with `{}` |
| 2 | Exact original read call and real selected-block result | `call_pinkha_cancel_create_v1`, exact cancellation title |
| 3 | UI Cancel yields exact sanctioned refusal | `PINKHA_HANLIN_CANCELLED_CREATE_CHECKED` |
| 4 | New Send after cancelled run | `call_pinkha_allow_create_v1`, different exact approved title |
| 5 | UI Allow yields an empty successful tool-content string | `PINKHA_HANLIN_APPROVED_CREATE_CHECKED` |

Every present historical tool call/result is validated; history may be omitted
between distinct Sends because the real UI supplies visible conversation messages.
The currently awaited call/result is mandatory. Unissued/duplicate/changed calls,
results or arguments are refused. Before the read result, selected A cannot appear
anywhere in request JSON; unselected B can never appear, including keys and escaped
JSON tool strings. Requests, JSON depth/node count, headers, connections and lifetime
are bounded. Invalid model requests terminally fail the scenario; extra rounds
invalidate completion. Model requests are serialized through response writes to
avoid rejecting a legitimate next request racing a final SSE flush.

Read schema: `{"type":"object","properties":{},"additionalProperties":false}`.
Read result: exact `PinkhaHanlinTextSnapshot` fields `objectReference`, `spaceReference`,
`sourceRevision`, `title`, `blocks[{reference,text}]`, `coverage`; this test requires
one exact selected block and `selectedTextBlocksOnly`. It is whole-block text,
not a character-subrange claim.

Creation schema: `{"type":"object","properties":{"title":{"type":"string","minLength":1,"maxLength":512}},"required":["title"],"additionalProperties":false}`.
Cancel must return `Host operation unavailable or no longer authorized`.
The same refusal can represent other preflight failures: the real prompt/Cancel
action and native absence check remain independent mandatory UI assertions.
Successful creation returns empty tool content, never a fabricated object ID.
The UI must separately prove the real confirmed receipt, cancelled-title absence,
exactly one approved page in the original Space and persistence after cold reopen.

The 13 always-present check names are defined in `protocol.CHECK_NAMES`; they are
metadata booleans only. The server cannot claim that these independent UI/native
assertions happened. The final mounted named test supplies that evidence.

## Canonical provenance and validation

Canonical Hanlin commit: `116cc6be0654a5d11bc56ba00e0310031107ee36`.
Canonical Swift AI SDK commit: `e7bf34111e603ca977becd007dd4e5bb109af857`.

The SSE translation is tied to `ProviderResponseFixtures.openAIChatTextChunks`,
`openAIChatToolCallChunks` and `sseOpenAI` under
`Packages/HanlinPlatform/Tests/HanlinChatCoreTests/ProviderConformance/`.
Original file SHA256:
`de14c4620dfe2f8b49eb104eb22ca1467efa85ab31ff2968547d0cfb00e9f17a`.

`verify_canonical.py` verifies git-show/materialized bytes, extracts the exact
Foundation-only method bodies without changing them, compiles/runs those original
Swift builders, and compares seven actual outputs with the Python implementation.
It verifies all decoded SSE values, raw tool-argument strings and exact frame/DONE
boundaries. It does not claim JSON escape spelling is byte-identical.

`test_fixture.py --result <safe-json> [--openssl <executable>]` exercises meaningful
strict protocol rejections and actual HTTPS trust/framing/connection cleanup.
`validate_lifecycle.py --repo-root <repo> --output <new-safe-dir> [--openssl ...]`
starts the real CLI child, imports only root's `validate_private_config` function
(no workflow main/prepare/trust action), executes the complete HTTPS contract,
checks incomplete verify refusal and final safe metadata, then proves process and
listener shutdown with an actual keepalive connection still open.

These controls are not a substitute for the mounted application test.

## Evidence allowlist

Upload only fixture source hashes, pinned source/equivalence manifests, public CA
fingerprint, safe readiness/verification/cleanup results, check booleans, counts,
body hashes and bounded timings. Keep private config, environment values, request
bodies/transcripts, raw validator errors, private keys/certificates and recovery
phrase screenshots/AX trees outside every artifact glob. The canonical emulator's
raw transcript is deliberately not reused: ordinary business bodies are retained
there even when authorization headers are redacted.
