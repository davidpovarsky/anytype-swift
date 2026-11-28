# Heart Notes tool visibility

Status: source correction independently reviewed; actual Apple compilation and UI acceptance remain NOT_RUN.

## Problem and change

The original Heart editor supplies the real Torah Notes repository and host actions to the shared Inspector, but its configuration advertises only Commentaries, Links and Related Documents. The existing Native caller advertises those same tools plus Notes. The correction appends `.notes` to the Heart caller's existing `availableTools` list. It keeps all three original tools and the original `.anytype` theme.

The product change is exactly eight bytes in one line of `Anytype/Sources/Pinkha/Torah/UI/TorahEditorHostModifier.swift`. It changes no action, repository, factory, selected-tool binding, presentation lifecycle, locale propagation, layout modifier, accessibility observer, Type or stored property. Notes continue through the original shared Kit presentation and the existing canonical Heart services.

## Exact source

Base commit: `b8521ca8d9d88f62aeb8e246de2c1ae2dd798588`.

| Body | Bytes | SHA-256 | Git blob |
| --- | ---: | --- | --- |
| Original Heart host | 5,356 | `e36b7b7dbde28bbfc431a40dfbf59a49a05d973217f2b7be46a61e6cb1334bbf` | `bf6063cbc59ab5f689486d29c9dd1661b44173bc` |
| Updated Heart host | 5,364 | `adf601dc09bd2abee727fce05b3141f7e9344dfb2dd45b8731f99461cc7caf99` | `a7d778a5827efd573800f96e14fdc60fd58b5fc7` |

Before:
```swift
availableTools: [.commentaries, .links, .relatedDocuments],
```
After:
```swift
availableTools: [.commentaries, .links, .relatedDocuments, .notes],
```

Replacing the new literal once with the original literal restores the complete original source byte for byte. All unrelated product files remain unchanged. The current Kit pin stays `26beca175d64a4d34e3567f2bbb4bf308d714478`; this patch does not install Kit414's optional navigation hooks.

## Acceptance still required

This source correction has no runtime acceptance credit. W3 owns the matching App source intake and actual Apple product. Preserve the first acceptance order: the 22 focus methods / 34 cases, original real-application preparation, then the four original Stage1 UI methods. Do not change those methods, fixture gates or deadlines.

Run mounted Notes/Inspector acceptance through the existing real application routes to verify that the Notes tool appears, loads the selected source's existing notes, and runs the original Add/Open/Unlink actions with the correct document, source, anchor, account and Space. This bounded packet does not establish a current named automated mounted Notes method; the hosted service methods must not be relabelled as UI coverage. Check cancellation and presentation retirement, read-only refusal, error display, cold reopening, Hebrew/English and the required phone/tablet, light/dark and accessibility cases on the actual product. Retain screenshots, xcresult and native readback; source review cannot substitute for them.

The existing `TorahNoteRepositoryAuthorityTests` remain two methods / ten declared cases, Apple NOT_RUN. They must be selected in isolation because the synchronous Factory override is global. Keep f9f86c7's original authority/source evidence and the accepted T5 historical 36+9 calls unchanged. No test was added merely to mirror the one-line configuration change.

## Source review and limits

`source-assessment.json` records the finite current Kit26, shared-session and real Notes-service trace, including the existing focus/request-token cancellation and repository invalidation mechanisms. `independent-owner-review.json` separately binds the actual session/open owner and the association-policy installer. The policy model requires matching Space/object and its weak-document callback checks current relation-edit permission and read-only state. This change neither installs nor bypasses that policy. Its exact installation timing in a mounted journey remains an actual UI obligation.

The source assessment remains unchanged with its original proposal-only status: publication does not retrospectively turn source inspection into execution. Its separate persistence is a data-only operation. The original Note and related-document guarded services, canonical association identities, three separate Torah document Types, original native Properties and all existing tests remain untouched. External-change freshness and full Space/permission isolation are not established by the shared repository cache or request-token source trace.

The inspected existing Kit selectors are `torah-inspector-tools`, `torah-inspector-add-note`, `torah-inspector-note-<actual association id>`, `torah-inspector-note-unlink-<actual association id>` and `torah-inspector-related-add-note`. Use the actual retained association identity in variable selectors; the tool's visible localized title still requires observation on the mounted product.
