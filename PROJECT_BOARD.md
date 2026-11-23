# Project Board

This is a living working-memory document for this repository.
It is intentionally lightweight. Humans and coding agents should update it when useful discoveries, ideas, plans, optimizations, problems, or follow-up work arise during normal development.
Do not turn this into a duplicate issue tracker or a dump of temporary thoughts.

## Inbox

Quick captures that still need classification.

## Ideas & Opportunities

Potential improvements, features, optimizations, or architectural ideas.

## Discoveries & Tips

- 2026-11-23: Canonical Hanlin uses one pinned selected-product checkout. Keep the existing SDK06 source marker API, but verify original Git blobs, complete source-directory membership and regenerated manifest before trusting it. A self-reported hash must not admit a modified dependency. The integration branch leaves enumeration, quiescence and native runtime qualification with their existing owners.

Useful technical discoveries, undocumented behavior, shortcuts, implementation tricks, platform behavior, or reusable knowledge discovered while working.

## Experiments / Investigations

Things worth testing or researching before deciding whether to implement them.

## Open Questions

Important unresolved questions or uncertainties.

## Planned / Todo

Concrete work that is worth doing but is not part of the current task.

Use Markdown checkboxes where useful:

- [ ] Example item

## Done

Completed items that are still useful to retain because they document an important decision, discovery, or implementation.

Example:

- [x] Example improvement
  - Implemented: YYYY-MM-DD
  - Commit/PR: ...
  - Notes: ...

## Archive

Older completed/superseded items that still have historical value.


## 2026-11-23 — Canonical Hanlin SDK producer repin

The isolated canonical SDK candidate now selects published Hanlin d49a4fd4115b8335105d2991bf74ab4d7f6aad2d, including the shared aggregate JSONSchema resource correction. Actual sparse installation and immutable source proof passed for the original eight products (579 original files,14 directories,zero native targets). Host implementation, package configuration and active-owner controllers are unchanged. Prior four source-guard controls are retained without repetition. Evidence: docs/validation/20261123-canonical-hanlin-sdk-repin. Native acceptance remains NOT_RUN and requires coordination with the existing SDK06 owner; no CI dispatch by this lane.
