# Actual Any UIKit semantic anchor acceptance

The original `NativeLaunchTests/testActualSemanticSelectionCancelCreateEditAndColdReopen`
passed 1/1 with zero failures or skips on the owned iPad Pro 13-inch (M5),
iOS 27.0 (24A434), in 240.481 seconds. Product source:
`4e1b9baebf00a4e2d6b2de8177989f04539a010e`. Controller:
`0bb9138c184c25543d8864149dd333080c3407e1`.

The real UI selected text, cancelled without a native change, created exactly
one anchor after confirmation, replaced the selected word through individual
UIKit key inputs while preserving the same marker over all seven new characters,
then reopened the same document in a fresh process. PID changed 11725 to 16602;
native owner generation changed; native source bytes and marker identity/range
survived. Twelve original read-only observations compare actual native snapshot
values with actual UIKit attributes. They made no engine calls, mutations or
selection changes. All original UI assertions remained unchanged for this fix.

All 873 original compiled product entries were verified and copy-on-write
retained before any subsequent source change. Original build/test xcresults,
descriptors, commands, source/dependency/native inventories and private UI
attachments remain under `/Users/m1/builds/any-semantic-20261125/ui-typing2/evidence`.
The receipt contains hashes and the owned test's bounded observation values;
private screen recordings and onboarding content are not published.

The separate actual-native controls remain 2/2 PASS at source
`fbb7b19c3b6c7cbdff8343b0397693a762bc1da2`; the controller proves their existing
call paths unchanged. The additive typing policy also passed five source-bound
component methods. This UI uses original Any producer
`31ae2e63890b6e10af8413625534f6234ed263bb` and Hanlin
`6bd6036dbca16c969689a5722550a54bebc1e851`. It does not qualify the newer combined
runtime, pending semantic source-link integration, multi-peer synchronization,
physical hardware, or all of Task E. Those acceptance boundaries remain open.
All prior failing xcresults, including the real range-0/1 typing failure, remain
preserved and are not relabeled as successful.
