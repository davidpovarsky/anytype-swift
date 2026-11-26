# Shared editor focus after actual collection presentation

Status: source-reviewed candidate; no new Apple test pass is claimed in this checkpoint.

The original App14 `app14-editor-ipad-he-light-02` ran the real native preparation and failed one method (exit65; 17.403 seconds, two issues); the four original UI methods were not run. Execution SHA256: `54ecaae75fbab655045cdd92833a87d3e43b0a405ad52688323daae3f4a4c4ce`. Original log SHA256: `65230a6bb91f06345f295a0e89b416f24a28de297939be3709233994dfbc9a3f`. All27 command process groups were absent; this is a product preparation failure, not the earlier EPERM controller failure.

The inserted empty row retained the current initial focus request and recorded one scheduling event with zero native responder attempts and zero cancellation events. The old observations did not record whether that callback returned at a readiness guard. A row can finish its own layout before its ancestor cell becomes visible; neither that later visibility nor diffable insertion completion previously resumed the pending request.

The common editor now observes actual cell display and diffable completion. Each visible current cell resumes only an existing request that has never reached the native responder. The queued delivery retains the original UUID and rechecks all existing ownership, permission and UIKit readiness guards. Native refusals are not repeated by display events; the original key-window/scene readiness policy is retained. No timer, new focus request, direct test focus repair or relaxed acceptance assertion was introduced.

Two additional UIKit methods (three cases) cover an actual collection with an empty input and an animated ancestor presentation, a newer cursor that must retain ownership, and a native delegate refusal that display cannot replay. Existing focus tests and the original real editor preparation must run against the new application. Read-only diagnostics now distinguish queued delivery, window deferral and presentation deferral, and report bounded final UIKit readiness without text or document identifiers.

The original full xcresult, logs, disposable account and controller evidence remain under `/Users/m1/development/anytype-root-active-20261125/app14-editor-ipad-he-light-02/`. This checkpoint does not close F, T5 or release acceptance.
