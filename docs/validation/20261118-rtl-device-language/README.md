# Real simulator language configuration for editor acceptance

The editor lane previously set PINKHA_ACCEPTANCE_DEVICE_LANGUAGE to an expected opposite language without changing or checking the actual simulator setting. The existing receipt kept device_language_verified=false; it was not valid evidence of the mismatched-language acceptance condition.

The controller now configures only the exact disposable simulator already checked against the current run identity. It writes that simulator's global AppleLanguages/AppleLocale, shuts it down, boots it again, waits for boot completion, and reads the actual global preferences back. Hebrew app runs require English device preferences; English app runs require Hebrew device preferences. Missing, malformed, same-language or wrong-locale observations stop the lane before native preparation or UI execution.

The fixture environment receives the verified observation, never an inferred opposite label. The receipt explicitly scopes this check to SIMULATOR_GLOBAL_PREFERENCES_AFTER_REBOOT. It does not claim that reading preferences independently verifies the app override or rendered UI direction; the existing actual UITextView, typing, paragraph, caret, Enter and relaunch assertions remain required. Only language/locale fields and a digest are retained; unrelated globals are not published.

Twelve controller tests pass on the connected Windows Python runtime, with no skips. New cases exercise both mismatch directions, missing/invalid preferences, failure receipts, a read after reboot, and non-publication of unrelated preferences. This is controller evidence only: no Apple simulator command, RTL UI method or physical device test was executed for this source change.
