# Editor insertion: current collection editing state

The exact-source editor run [44426302049](https://github.com/davidpovarsky/anytype-swift/actions/runs/44426302049) built successfully but stopped in native preparation before UI execution. Its original focus request was retained and then cancelled with interaction disabled, while the owning collection was already editing and unlocked. No native first-responder attempt occurred.

New EditorViewListCell instances now receive their weak collection owner before any state or content configuration. Their editing state reflects that current owner; other consumers retain UIKit's default when no owner is assigned. Reuse clears ownership. No retry, polling, artificial tap, or relaxed focus cancellation was added.

A parameterized Swift regression inserts the initial focus request before first display. Editing=true must acquire focus. Editing=false must cancel it permanently across a later editing-state change; a new explicit request must then work. All prior lock, reuse, rebind, detach, and supersession cases remain.

The source-bound core manifest contains54 methods and80 literal cases, including12 focus methods and18 cases. The focused Python controllers pass19+17 tests. The independent source review has no blocking finding. **Apple compilation, native UIKit execution, and Hebrew editor UI acceptance remain pending at this commit.**

See validation.json for source hashes and original run facts; independent-review.json for review scope; the two final control logs for executable controller evidence. The initial aggregate fixture expectation was corrected from28to29 additional cases after adding the new parameterized method; the failed initial local log is preserved outside the committed final logs.

The baseline is586c98bcc17dee425664224e508fc0e8df277678. Upstream develop was observed at d857b23ea540be33d6faab4f7a7a1a260ab578c1. Changes to the two existing upstream UIKit extension points are deliberately narrow and do not mix unrelated upstream work. The active any-engine migration uses its own worktree and is unaffected.
