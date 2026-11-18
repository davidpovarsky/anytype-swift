# Actual native component-store compatibility pass

Run 44217298120 at integration c8e5a0e148021662dd943f93faeb3195c6086888 completed COMPONENT_STORE_PAIR_PASS. Two exact native ELF test binaries executed four separate passing processes on the same original on-disk component store. Old-create PID 9790; new-upgrade PID 9811; old-edit PID 9832; new-recover PID 9853. Each closed its native handles before exit.

Canonical payload/unknown fields and public document-only projection remained equal across all phases. The two new-runtime phases executed indexed document+block lookup; each transition recomputed four cache entries. Old runtime phases did not attempt expanded lookup even where stale private rows could persist.

The original evidence zip SHA-256 is 33807a55ef2b0d26f1ef2e16f5d72b187cfd507ebb9cb7eef122a618db75f038 (GitHub artifact 14389765034). Original run/artifact metadata, exact zip bytes, extracted receipts, logs, source inventories and build identities are retained here. The large native binaries remain in the separate GitHub binary artifact; their recorded SHA-256 values are in summary.json and original build receipts.

This proves the preserved component-store sequence only. export_status=NOT_RUN_COMPONENT_NO_RPC; swift_pairing_status=NOT_RUN; full_F10=NOT_PROVEN; client_enablement=DISABLED_PENDING_RUNTIME_COMPATIBILITY_PROOF. The separate actual account/export route is prepared in source 58815ae089699d6ca23a3589571b796fce3ec772 but was not executed by this run.
