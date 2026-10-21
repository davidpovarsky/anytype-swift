# Torah Inspector screenshot status — 2026-10-21

## Evidence produced by automation

- The TorahInspectorKit iPadOS 27 workflow captures Hebrew RTL Peek, medium and
  large detents from the standalone Demo and uploads the UI-test xcresult.
- Those captures prove only the shared Kit scene. They do not prove the
  authenticated Anytype editor, its live objects, keyboard, or preserved
  sandbox.
- The consolidated Anytype workflow builds the real host and publishes its
  test/build logs and unsigned IPA audit. It does not inject a production
  account or fabricate live Torah objects to manufacture screenshots.

## Still requiring the owner's physical iPad

- Light/dark search in idle, empty, error and real-result states.
- Physical-right RTL sheet at Peek/medium/large, including background
  interaction and drag transitions.
- Commentary/Links/In Documents with real current-document note objects.
- Paired reader viewport before opening detail and after native Back.
- Relationships-root book action, exact verse anchoring and Back chain.
- Selector hide/reveal during real scroll, Dynamic Type and VoiceOver labels.
- Narrow Stage Manager, split view, landscape and iPhone/older-iOS fallback.
- Generic insertion focus versus Torah quote no-autofocus in the live editor.

Until those captures are attached, all corresponding visual assertions remain
`DEVICE_PENDING`; historical screenshots and simulator output are not relabeled
as physical-device proof.
