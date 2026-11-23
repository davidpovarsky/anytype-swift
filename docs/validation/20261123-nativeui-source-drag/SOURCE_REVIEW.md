# Source-drag fixture lifecycle repair

The original iPad simulator method failed while waiting for the inspector close button at line 618. It had already passed the quote/body equality, distinct block identity, canonical source badge, unchanged target, two-block count, insertion order and zero-keyboard assertions.

The unchanged collapseInspectorForBackgroundRead helper performs a real sheet-header gesture. Its explicit accepted outcomes are a peek sheet or a completely dismissed sheet. Requiring a close button afterward is incompatible with the dismissed state. The next operation is the method's existing cold reopen, which terminates and relaunches the owned app from either supported state.

The repair removes only that redundant close action. Every drag, native/content identity, source badge, ordering, keyboard and cold-reopen assertion remains. Shared helpers and product source are unchanged. The original failed method log and exact result metadata are retained; the test source at this repair's base matches the original executed source byte for byte.

Swift frontend parsing and diff checks passed. No XCTest was executed for this repair on Linux. The exact failed source-drag journey still requires one actual simulator execution. Previously passed methods must retain their original evidence rather than run again solely because this method changed.
