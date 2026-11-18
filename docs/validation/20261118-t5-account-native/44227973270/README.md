# Native account retry 44227973270

The original GitHub artifact14393424478 was downloaded once and verified against its published SHA256. All38 archive files are retained byte-for-byte in github-artifact/. This run used e95fc4e391afa42efd66d4b8e6b6a92b96862412 and the Note-install fixture from9dac4ef.

Both exact native RPC binaries compiled. The initial process created all three Page/Note/custom documents and retained Page JSON and Protobuf exports, then failed its ordinary-title assertion before any phase could pass. The loop reached Note after the Page exports. Native WithNameToFirstBlock removes the requested Note name detail; the corrected fixture records the actual post-creation name, preserving the existing exact-name checks in later phases/exports. The raw failure is not replaced or counted as a passing test.

Counts:2 compiled native binaries;1 started process;0 passing phases;3 original created documents;2 retained actual export files. Full24-export/four-process compatibility remains open. AccountStop follow-up and Apple Swift pairing are NOT_RUN for this artifact. No product flag is enabled.
