# Quote test compilation correction
The original Inspector attempt 44236416541 failed during Release-Anytype build-for-testing. Native preparation and all five selected UI methods did not execute. The verified original artifact and unchanged raw compiler diagnostics are identified in verified-failure.json; the full archive remains on GitHub and on the connected host.

Four actual diagnostics identify two private inspectorDidDismiss calls and two subscripts on optional customMetadata. The tests now use the existing hostActions.onClose callback, assert that it cleared the selection, and use optional chaining whose comparison still requires the exact snapshot text. Production access levels and behavior are unchanged. The existing ten methods and twelve argument cases remain required.

The new SDK attempt 44245129998 referenced byte-identical quote test source. It was still queued when cancellation was requested, so it provides no SDK functional result. This correction requires a new Apple build; local controller checks are not Apple acceptance.
