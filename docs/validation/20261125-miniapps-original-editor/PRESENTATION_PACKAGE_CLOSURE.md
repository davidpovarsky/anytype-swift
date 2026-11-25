# Original SDK presentation dependency closure

The actual E5 strict resolver correctly selected the reviewed Markdown revision
then stopped before compilation because A2UI was missing from the historical
lock. The current shared presentation manifest declares A2UI and SwiftSoup.
A2UI's reviewed manifest requires swift-json-schema and Yams.

The SDK lock adds only these four records, copied byte-equivalently from the
committed Hanlin lock at `9ef80a6ddfc997724360a9a34bb1d05cbf7cad40`
(Git blob `16d1cb345e17f600c765f95b8badddb2ca104809`, SHA-256
`a8eaac8c61e6dcf43d3441d0801942958d8eb10b7f70877d9aaa1477cda0a6f9`).
All 52 preexisting records are retained, giving 56 exact pins.
The four source manifest blobs and exact versions/revisions are recorded in
`framework_profile.json`. SwiftSoup and Yams declare no remote dependencies.
The schema library's SwiftSyntax and Collections requirements admit the
already retained original versions; no broad lock refresh is authorized.

This source update grants no native acceptance. The normal SDK runner still
requires the committed exact lock blob and an actual strict Xcode resolver,
then the complete framework, exported API and external consumer gates.

## Original ZIPFoundation compatibility

The original Anytype PBX object `2A685D582B7B854200456E08` requires exact
ZIPFoundation 0.9.20. Its source and the corresponding lock entry are preserved.
HanlinPlatform previously required exact 0.9.19, creating incompatible constraints.
Shared commit `6f525c67f5f62587e46085da56e6a8c2a406cee4` supplies a
patch-compatible >=0.9.19, <0.10.0 requirement in both the root manifest and
Packages/HanlinPlatform/Package.swift. The producer retains its reviewed 0.9.19
lock while this original consumer retains 0.9.20. This exact shared commit is
bound in Tools/Hanlin/source.json and the native source profile. The nested
manifest is the only changed file among the three consumed shared packages.

Upstream's original 0.9.19...0.9.20 comparison contains ZIP64 extraction fixes,
readChunk memory leak and file-resource fixes and a privacy manifest reason
correction. Rolling the original consumer back would discard these changes.
No MiniApps JavaScript runtime package is added to this consumer closure.
