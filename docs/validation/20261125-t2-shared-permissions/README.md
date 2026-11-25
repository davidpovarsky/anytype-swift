# Shared permissions and invitation management — 2026-11-25

## Product change

One PinkhaSharing module supplies validated membership models, confirmed actions,
invitation and join presentation, English/Hebrew localization, and account-lifetime
ownership. Heart and Any adapters call their existing native membership APIs;
neither manufactures an ACL, invite token, write ACK, or optimistic role change.

Heart's original participant subscriptions, member rows, profile sheet, RPCs and
Hanlin account fencing remain intact. Its new sharing owner drains before account
transitions. Any uses its existing workspace lease and original signed ACL endpoints.

The HTTP client exposes the original response status without changing its existing
JSON API, cancellation/authorization checks, account revalidation or uncertain-write
handling. A native 202 join response is never presented as completed membership,
even if the original body contains an active status during asynchronous loading.

## Observed evidence

- Shared authority/lifetime controls: **4/4 PASS**, no failures/skips.
- Actual finite loopback HTTP controls: **3/3 PASS**, no failures/skips:
  preserved 202 versus 201, original body API compatibility, account switch after
  mutation response, and partial native rejection.
- The first HTTP fixture inherited a blocked SIGTERM and took its finite 45-second
  exit path. The original successful log and original fixture are preserved.
  The corrected fixture installs/unblocks its own SIGTERM handler; a distinct
  owned-process shutdown control passed in 0.324 seconds with SIGTERM initially blocked.
- Actual Apple Swift 6.4 / Xcode 27 SwiftUI package build: **PASS**.
  The exact final package snapshot includes explicit member/role confirmation text.
  Original source manifest and compiler log are preserved.

These are component, HTTP-boundary and package-compilation observations.
They do **not** prove native coordinator invitations, mounted Apple permissions UI,
mixed-engine synchronization or physical-device behavior.

## Remaining acceptance

The main app needs the shared product dependency and the Any host navigation hook,
followed by actual compilation of both engine adapters and mounted UI acceptance.
The existing native two-peer ACL evidence (run 45430971070) remains valid for its
original scope, but it does not establish coordinator invitations or all T2 scenarios.
Run the original real multi-account invitation, role, offline/reconnect and concurrent
update cases against a qualified network, then verify the shared management UI.
T2 stays open.

Source and evidence SHA-256 bindings are in source-and-evidence.json.
