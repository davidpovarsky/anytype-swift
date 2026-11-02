# Stage 1 — native Sources and editable RTL implementation

[נועם | הנדסה] [MAIN_SESSION]. Owner-authorized implementation cycle, 2026-11-02. This report supersedes the proposal-only status of the November 1 artifacts. No Asana changes, merge, release, signing, generated/protobuf/Heart edits or schema migration.

## Identity and preservation

- Existing branch: `pinkha/torah-associations-native-ux-persistence-localization-2026-10-20`.
- Starting local/origin SHA: `05883c5549261cfed022a63a969751900c96744f`.
- Live upstream/develop: `e21834498cd6d8a85e91f69767caec793220a190`; merge base `d5650321577a209505a3277c8437b7608cff1cb9`.
- Initial integration/probe SHA: `32bd67f1d5ce5f2585a5e15f685dc34b24d41453`.
- All pre-existing modified/untracked files were copied to `%LOCALAPPDATA%/Temp/pinkha-stage1-authorized-20261102` before this cycle. No clean/reset/rebase or branch switch. Archives, prompt backups, unrelated line endings and the pre-existing untracked Package.resolved are excluded from staging.
- Scoped host exceptions and rollback: [register](../../architecture/UPSTREAM_EXCEPTION_REGISTER.md) and [exact cumulative diff](../../architecture/STAGE_1_IMPLEMENTATION_HOST_DIFF_2026-11-02.patch).

## Sources composition

The original native FeaturedProperties wrapping stack still renders every existing Property with its original PropertyValueView, style and action. A default-empty trailing slot renders canonical source chips (at most two), remaining count and permanent Sources +, using the same TorahEditorSession and search/Inspector/repository. Source actions resolve document scope explicitly and reject inactive sessions/stale source IDs.

If the original featuredRelations block exists, including an empty property list, that original row owns Sources. Otherwise the native builder caches one downstream system row with stable `Space + object` identity, reusing EditorFeaturedPropertiesView. It observes native properties and source snapshots without a structural editor reload. It does not create a synthetic persisted block, BlockInformation, Property or another source store. Original type/Tags actions remain shared.

### Creation evidence reused from the accepted investigation

The configured middleware is Heart `v0.51.7-nightly.20261014.1`, exact tag commit `d98420b1113536afd08cde6de9a5816f6d27ffff`. Its normal blank template supplies the featuredRelations header via WithFeaturedRelationsBlock; Page creation-state migration installs it before layout selection. Note removes the title rather than this metadata block. Pinkha type/default-template creation uses these native APIs. This explains newly created normal documents, but does not establish repair of an existing/imported tree missing that block; the presentation-only compatibility row handles that shape. No Heart source is changed.

## RTL evidence and limits

The native observation test uses real TextBlockContentView, host styler, original setFocus, physical caretRect before any input and an accepted native first-insertion callback. It separately exercises configuration before and after hierarchy attachment. The original four-callback C1 remains rejected; the historical one-callback candidate is not applied without measured need.

Acceptance diagnostics report actual typing paragraph direction, current responder and caret geometry. Read-only diagnostic notifications refresh the measurements after focus restoration; they never apply styles or alter focus/selection. The test-runner language variables use Xcode's required TEST_RUNNER_ forwarding, rather than assuming shell variables reach the UI-test process.

## Verification ledger

| Gate | State | Evidence / limit |
|---|---|---|
| Windows Swift syntax / source whitespace | PASS | Changed Swift files parsed; patch artifacts retain exact original-context whitespace |
| Portable PinkhaKit baseline | PASS (reused) | 153 tests / 19 suites, including 6 direction-policy tests in November 1 evidence; not native proof |
| Initial native integration/probe | FAIL | [Fast CI 41356934419](https://github.com/davidpovarsky/anytype-swift/actions/runs/41356934419): native app/test build PASS; 66/68 tests per primary device, zero skips; other language pair NOT_RUN |
| Old package CI toolchain | FAIL | [41356934493](https://github.com/davidpovarsky/anytype-swift/actions/runs/41356934493), signal 6 / task allocator under Xcode 26.1.1 |
| Updated package toolchain alone | FAIL | [41368012507](https://github.com/davidpovarsky/anytype-swift/actions/runs/41368012507), same allocator abort under Xcode 26.4.1. Updating tools alone did not resolve this failure |
| Native row 0/1/2/12/0 + narrow LTR/RTL snapshots | NOT_RUN | Fast CI includes the actual hosted native and presentation row test |
| Five successive Enter blocks + relaunch, Page/Note/Pinkha | NOT_RUN | Full Acceptance, separate from isolated UIKit tests |
| Original search/Inspector/block ornament | NOT_RUN for current implementation | Existing native regression suites retained |
| Full Acceptance / unsigned QA IPA | NOT_RUN | Same-SHA Fast CI gate still applies |
| Physical iPad, hardware keyboard, real IME/VoiceOver/Stage Manager | NOT_RUN | Simulator/static/Windows results cannot certify these |

This ledger is updated from actual run results. A successful build does not turn any unexecuted interaction or physical-device case into PASS. Full multi-client T2 remains blocked and outside this cycle.

## First measured failures and correction

Both devices measured the same focused empty-caret failure: configuration before RTL attachment yielded caret x=1 versus view midpoint 160. Configuration after attachment passed this check. The correction is one didMoveToWindow hook applying the cached downstream presentation context at actual attachment. It does not change setFocus or persist alignment. Validation of the correction is pending the next native run.

The baseline programmatic insertText call produced zero native should-change callbacks in both cases; insertionDirection was nil, so that portion of the probe is INVALID, not proof of wrong accepted-input attributes. The unit now names and explicitly exercises the native delegate contract. Full Acceptance separately records the actual host-accepted first empty input before UIKit inserts it, via a diagnostics-only host hook. No behavioral C1 callback is applied.

Sources data counts updated correctly, but baseline standalone-host snapshots stayed at Sources + for every nonzero count. This is a FAIL of displayed refresh qualification. The revised fixture embeds the actual native content configuration in a real EditorViewListCell and diffable collection, keeps the same item and cell, requires no source-driven reconfiguration, and captures the updated visible hierarchy. Pixel differences remain required; this is not yet called a production refresh PASS. Book/overflow remain pending successful displayed and interactive replacement evidence.

## Package CI allocator correction

On Xcode 26.4.1 the four unfinished tests were HTTP status diagnostics, malformed text versus failed HTTP, lexical 404 versus server errors, and topic-cache retry after failure. All four exercise the default SefariaClient backoff after a server error. The same code passed all 153 tests in Xcode 27, while the older compiler aborted before the default delays finished.

This correlates with Swift's documented [cross-module Task.sleep specialization failure](https://github.com/swiftlang/swift/issues/86204) and [default async closure frame mismatch](https://github.com/swiftlang/swift/issues/92017). The downstream correction keeps the default async body in one internal library function and sleeps until a ContinuousClock deadline. The public initializer signature, injected sleepers, retry counts/durations, cancellation and provider errors remain intact. No test is skipped or serialized to conceal the failure.

The complete unchanged 153-test/19-suite package run passed on Windows Swift 6.3.3 after this correction ([local evidence](evidence/2026-11-02/retry-fix-windows.log)). This is not yet a Mac result; native package validation is pending the next push. The correction is kept local while the current native RTL/Sources execution at `f0e6eda5ce4541536b753c8bed10004c9842a455` finishes, avoiding cancellation of its evidence.
