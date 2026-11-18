# Embedded Inspector search acceptance source

The existing standalone source-search smoke methods do not exercise the optional in-Inspector search route. This adds one separate inspector-search lane, using the existing fresh native preparation and the already registered UI test file.

The test opens the original source chip, enters search within the same Inspector, searches Genesis 1:2 from the real provider, opens its real text, returns through the existing native Back control and verifies the query/results survived. It closes the panel and verifies Open did not change document source identities. A second pass explicitly links the same provider result to the document, requires canonical association readback, checks the original chips plus exactly one new chip, and reopens that chip. It rejects a second standalone search, a wrong block target, duplicate/replaced document sources, provider errors and unwanted editor keyboard focus.

Two accessibility identifiers were added to the existing Open and Link buttons. Their handlers, labels, style and permission conditions are unchanged. This does not recreate search, change Kit navigation or introduce direct test writes.

Local evidence: Swift5 product syntax, Swift6 UI syntax, seven lane-control methods and the exact selector/fixture/YAML checks passed. Apple build, this actual UI method and independent review remain NOT_RUN/PENDING at initial publication. This is not full Inspector, topic/word search, physical iPad or release acceptance. The source deliberately keeps the existing process and final PID checks.
