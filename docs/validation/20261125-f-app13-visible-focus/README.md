# App13 original F preparation: visible input lifecycle

App13 e540cd7e01b497f1b3173ae2e68b43ade0b00b6f, native410b, SDK86 built successfully. The original prepareRealApplicationState() actually ran once and failed; the following four UI methods did not run. Its native input readiness predicate passed. The one initial empty-area action created the empty editor row, but native focus arrived while an ancestor remained hidden. UIKit refused eligibility, so becomeFirstResponder() was never invoked. The retained request had only window/key/scene wakeups; these conditions were already satisfied.

Original log SHA256: a19a95136923b0bfded406a7cd0e4e69573d2132c24ac9ad5d6df79e4206d94f.
Original lane receipt SHA256: a5088fe7f2d753ee51ada4fda705ba31bc48b1c4327a46e791f08f100178754c.
Original evidence: /Users/m1/development/anytype-root-active-20261125/f-app13-first-editor-attempt1.
The owned simulator remains Shutdown with its account retained. This run did not reach the previous direction assertion and does not determine whether e006 fixes it.

## Candidate

TextBlockContentView now waits for actual nonempty input bounds and a visible ancestor chain. A real layout transition to visible schedules only the still-current request. UUID coalescing prevents overlapping layout/attachment callbacks. Unchanged visible layouts after native refusal do not cause repeated attempts. Existing editor state, request ownership, lifetime, composition and caret protections remain.

Two additive UIKit methods cover three cases: current hidden input becoming visible; a superseded hidden input preserving another actual responder; and repeated visible layouts after native delegate refusal. All original methods remain intact. Independent source review found no blocking lifetime/reentrancy issue. The current app must still prove its real layout transition and original F preparation/UI outcomes.

This record is source retention and failure diagnosis, not an Apple build, UIKit pass, complete F acceptance or Release acceptance.
