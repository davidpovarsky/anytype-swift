# Receipt display capacity and the unresolved-write barrier

Review of the f8fadb60 source milestone found that the existing 256 receipt-label guard preceded processing of an uncertain native outcome. The original AgentSession independently rejects another run while a durable tool call has no non-uncertain result, but the presentation must also keep Send, Retry and Continue disabled independently of display capacity.

The presentation now uses one bounded receipt-state value. It validates the original session/context and deduplicates retained receipt identities, records new uncertainty before the optional display-capacity guard, and exposes one sticky run gate used by Send/Retry/Continue. A later successful result or a full display list cannot reopen that gate. The error banner is updated even when no further label can be appended. Close does not erase the original SDK/native effect receipts.

The added controlled-event method runs with each engine namespace and fills exactly256 display entries, exercises replay and foreign-account rejection, then delivers the257th original-session uncertain result. It verifies that the shared run gate closes, the retained identity count remains256, and subsequent events cannot reopen it. The new UI projection suite therefore contains five methods/ten parameterized cases. These are controlled-event policy tests, not native provider/write/UI evidence. Their actual Apple compile/run remains NOT_RUN until the separately admitted build.

No canonical SDK change or rerun of the unaffected385 cancellation seven cases is required for this source fix. The canonical source remains f3afac65296e843ced1f7ddd7a55c2452e90b270; the first shared application freeze remains unchanged on SDK385.
