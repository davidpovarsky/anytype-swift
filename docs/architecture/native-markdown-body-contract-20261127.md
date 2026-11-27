# Native Markdown body contract — 2026-11-27

## Qualified engine primitive

`AnyNativeMarkdownBody` adds a scoped body operation over the original Any
native Markdown API. The accepted source is
`Modules/PinkhaAnyEngine/Sources/PinkhaAnyEngine/AnyNativeMarkdownBody.swift`,
SHA-256 `7097c7c5f7bbf67eba21a961986a892064a1833425ff74b053917a0d4e11e4af`.
It uses the existing `AnyHTTPClient` authority and account fences. The client,
native Go sources, Markdown parser and native write path are unchanged.

| Operation | Existing native route | Result |
| --- | --- | --- |
| Current read | GET `/v1/spaces/{space}/objects/{object}/editor/editor_blocks/markdown` | Body, exact UTF-8 digest/length and opaque native version |
| Conditional replacement | PUT to the same route, `content` and nonempty `ifVersion` | Native version and exact inserted/updated/deleted block IDs, followed by same-version authorized readback |
| Stale replacement | Same PUT with an obsolete version | Typed HTTP 409 `markdown.conflict`; no second PUT |

## Consumer integration

Wave 3 owns Hanlin/MiniApps router, consent, journal, worker and cancellation
integration. This primitive does not create a page or update those applications.

1. Bind `AnyHTTPClient` to the active account and create
   `AnyNativeMarkdownReference(accountID:spaceID:objectID:)` from the live Host
   session and the retained original creation receipt.
2. For a new save-message page, durably retain its creation receipt before any
   body operation. Read that same page through `read(_:authorize:)` and require
   an empty body. An unexpected body requires reconciliation with that page.
3. Create `AnyNativeMarkdownWriteIntent(reference:requestID:expectedVersion:content:)`
   with the read's version and a Host-owned 32-character lowercase hexadecimal
   request correlation. Retain the original reference, correlation and content
   digest in the same journal.
4. Invoke `replace(_:authorizeRead:authorizeWrite:)`. The read callback is a
   side-effect-free live consumer lease check. The write callback consumes the
   one-shot write authorization once. Every post-response delivery rechecks the
   account and read lease without consuming the write approval again.
5. Record the returned acknowledgement and saved-body digest against the
   original page. The same request correlation is not native deduplication.

There is no automatic retry, unconditional PUT fallback, replacement page,
implicit account selection, new native schema or new persistence store.

## Identity, bounds and canonical content

The account, Space and object are compared as exact UTF-8 bytes. Empty IDs,
ambiguous path components and IDs over 4,096 UTF-8 bytes are refused. Versions
are opaque nonempty ASCII values up to 1,024 bytes; the Host must not parse them
or reuse one across a native-process replacement. A fresh authorized read
supplies the current version after reopening.

The body limit is 262,144 UTF-8 bytes. Successful acknowledgements must contain
all three arrays, unique disjoint block IDs, a nonnegative unchanged count, and
a saved version. Acknowledgements exceeding the bounded 10,000-ID contract or
the 2 MiB JSON response limit are not promoted to success.

Native Markdown stores structured blocks and can canonicalize syntax.
`exactRequestedBytesPreserved` compares submitted and saved UTF-8 digests and
lengths. A normalized but successful save returns its actual current body and
digest; consumers must not substitute the request digest. A concurrent
readback with a different version cannot certify the earlier acknowledgement.

Body and native-version text are redacted from the description/debugDescription
of snapshots, intents, receipts and failures. Consumers still own any explicit
logging of their public fields.

## Uncertain effects and recovery

| Outcome | Adapter result | Host handling |
| --- | --- | --- |
| Valid native ACK and same-version authorized readback | `AnyNativeMarkdownWriteReceipt` | Retain native ACK and actual saved digest on the original page |
| Documented stale CAS, block-size validation, strict request validation, or native write-authority refusal | Existing typed engine error | Keep original page/journal; expose the precise refusal |
| Transport uncertainty, malformed/partial ACK, late authority/account change, undocumented native status or server error | `uncertain(context)` | Keep original reference and digest; reconcile without another create or automatic write |
| Native ACK known, but readback unavailable/revoked/cancelled | `acknowledgedReadbackUnavailable(ack)` | Keep the known durable identity; withhold private readback and reconcile after current authorization |
| Native ACK known, current readback version differs | `acknowledgedReadbackChanged(ack)` | Keep the original ACK; resolve the concurrent current body |

The native `sp.Modify` call can precede an error describing a rejected
operation. Consequently a generic native 5xx or partial successful response is
uncertain, not proof that no write occurred. The adapter never retries it.
Successful native block-ID receipts and original creation identities survive
Host cancellation/account-generation changes through the caller's original
journal. This engine primitive does not claim a completed application journal.

## Actual evidence

The complete published qualification is
`docs/validation/20261127-wave1-markdown-body/result.json`.

* Eighteen new component methods passed: 14 actual loopback HTTP methods and
  four identity/schema methods. Original console records 18 starts, 18 terminal
  PASS, zero failures and zero skips. They cover one-shot approval, post-response
  authority/account fences, stale CAS, canonicalization, uncertain partial/5xx
  writes and unavailable/changed readback.
* The first component run compiled successfully in 19.71 seconds but failed
  its finite deadline because the new Python fixture inherited a blocked
  SIGTERM. Its original receipt, log, old fixture and exact owned-process
  cleanup remain retained. Only fixture signal-mask/graceful-close handling
  changed. The accepted retry reused the same compiled products with
  `--skip-build` and completed in 10.47 seconds; XCTest took 6.031 seconds.
* Two actual Swift native methods passed against the unchanged qualified Any
  binary. An exact isolated copy of the retained semantic source account was
  opened under OS TCP/UDP denial; the original account/archive was not modified.
  One new page received one conditional body write with exactly 262,144 UTF-8
  bytes, including Hebrew, as 256 native blocks. Its returned block IDs were
  unique. An explicit stale second PUT was refused with native 409 and the
  original committed body remained unchanged.
* After actual acknowledgement and readback, the owned native process was
  intentionally SIGKILLed. A different native PID inherited NoNewPrivs=1 and
  Seccomp=2, had zero peers, and the second Swift method read the same original
  page/body/digest with zero new writes. All native/test/probe groups were
  positively absent afterward. Native controller duration was 12.806 seconds.
* Original accepted 28 HTTP/durability methods and the 182-operation migration
  were not rerun. Their source closure was checked unchanged. No Go, Apple or
  replacement Swift build was performed for the native phase.

This qualification is a body engine boundary and real local crash/offline
proof. Peer delivery of this new body, Heart's separate body RPC, Hanlin's full
two-stage save journey and Apple application integration remain their own
acceptance scopes.
