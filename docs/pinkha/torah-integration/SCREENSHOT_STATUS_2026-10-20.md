# Screenshot status — 2026-10-20

## Production UX correction

- The locale-aware Kit change is pinned at
  `1ebbbd2d43e1ba078e50408ce518d739fe6ca94f`; its 25 package tests passed in
  Anytype CI run `39469048720`. This run did not manufacture a new authenticated
  app screenshot.
- The Anytype block badge is a real UIKit cell accessory feeding the existing
  Kit system Sheet. No authenticated screenshot is claimed before the owner
  installs and opens the update on the existing iPad account.
- Document/block persistence visibility, editable-text gestures, Stage Manager,
  orientation and locale switching remain **DEVICE PENDING**.

## Historical trial evidence

- Kit demo Hebrew RTL Peek/Medium/Large screenshots remain historical Kit-only
  evidence from run `39350598474`, artifact `12233133803`; they are not evidence
  from the owner's authenticated Anytype sandbox.
- Actual authenticated Anytype app screenshots: **NOT VERIFIED**. CI starts in a
  separate empty sandbox and this implementation does not inject, clone or copy
  a production account/session merely to manufacture screenshots.
- Physical iPad orientation, compact-window and sheet-to-editor drag captures:
  **USER TEST PENDING**.

The lack of an authenticated app screenshot does not become a PASS. Use
`IPAD_TRIAL_CHECKLIST_HE.md` for the safe in-place update procedure and attach
real captures to the acceptance record.
