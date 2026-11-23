# Export fixture readiness repair

The first original export parent failed before all four export leaves. Its single Register call returned ErrFixedSchemaChanged after real schema activity, and the fixture discarded the returned phase history.

The accepted endpoint run provides the direct precedent: its first actual response returned the identical error after seventeen invoked creations, with the final after-observation ChangedWhileReading and an exact returned identity. Original read-only readiness then preceded one additional creation and one returned type Apply. The original error/observer/creator behavior is unchanged.

Only owned_annotation_export_native_test.go changes. It now uses the same bounded 21-call registration sequence and 30-second read-only native observer/index readiness body. It preserves actual phase identities and heads before schema assertions, refuses uncertain/repeated creation identities, requires eighteen unique actual creates and one returned Apply, and validates final matching native/index state. Phase files are bounded to 21, each at most 128 KiB, with no body, private account key or credential material.

All original export/body/format/nesting/file assertions and AccountStop cleanup are byte-identical after removing the declared setup substitutions and inserted helpers. Both archive source and archive tests remain byte-identical. This is fixture setup only; no existing registrar, production importer, RPC or generated code changes.

The retained hunk and source correspondence prove the exact inverse and copied readiness body. Gofmt completed; no native case has been run on the repaired source. The next reviewed native gate still owes four genuine exports and the thirty-two archive/staging cases. Earlier accepted endpoint and lifetime tests will not be replayed.
