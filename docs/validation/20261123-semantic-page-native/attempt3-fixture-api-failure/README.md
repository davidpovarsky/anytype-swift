# Original Page fixture API mismatch

The Go 1.26.5 ARM64 profile passed dependency and Tantivy preparation, then reached service-package test compilation. The original Page fixture used the generic cache.Do helper with clientspace.Space, but the generic ObjectGetter interface additionally requires GetObjectByFullID. The actual Space interface provides Do/DoCtx, with the same native GetObject and object Lock/Unlock behavior required by these two read-only observations.

The correction changes those two fixture calls and removes the unused cache import. All assertions, actual native service calls and storage/readback verification remain unchanged. All other 153 native paths and both module files are unchanged. No product source changed and no method had executed. The original source remains preserved in the wire recovery originals.
