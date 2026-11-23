# Original UI timeline evidence extraction

This change exports evidence from original failed run 45087682296 at source 7293e4fd0bcabdcdb643d5768b777b8e87ff1b73. It does not build, launch, or test the product.

The original attachment exporter remains byte-for-byte unchanged from 59d87891d7235429187599bd02d7ed8178ea8c22. Its first completed artifact (14783341999, run 45096076370) remains preserved separately. The additive exporter reuses its exact archive identity and hash checks.

The original XCTest log supplies both method start timestamps, completed workspace-setup action, connect/drag action, and failure boundary. Exactly two stills per case are selected well after onboarding. Recording names provide whole-second start times; the millisecond test timestamp refines their alignment. The media helper rejects inconsistent recording duration or decoded frame timestamps outside the permitted action/failure interval. Original recording hashes and requested/actual media timestamps are retained. No recording is published.

For the failed backup toggle, only numeric synthesized-event fields and switch rectangles/values are published. Labels, ancestor trees, binary payloads, and arbitrary strings are discarded. No backup screen or recovery phrase is exported. Backup decoding follows independent still rendering so a format issue preserves useful, safely bounded media evidence while the overall receipt still fails truthfully.

Five new controls passed. Both actual original log timelines parsed successfully. Swift syntax parsing passed on Oracle; AVFoundation compilation and media extraction require the single Mac export-only execution and remain pending. No old controls or product tests were rerun.

The existing generic diagnostics route for other run IDs is unchanged. For source_run_id 45087682296, the new artifact is Any-Original-UI-Timeline-Evidence-45087682296.

Apple documents the media generator's requested and actual times and configurable time tolerance: https://developer.apple.com/documentation/avfoundation/creating-images-from-a-video-asset . The helper checks both values rather than treating the requested offset as proof of the frame returned.
