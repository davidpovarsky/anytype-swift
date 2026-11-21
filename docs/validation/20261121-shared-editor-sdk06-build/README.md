# Reuse the SDK06 build for the unexecuted retained editor profile

Source baseline: c6ecc8ae89891b335434faec36f40b3b63e79334.
The earlier retained run 44942212731 never reached any of its ten selected
methods: AnytypeTests linking failed on three missing package products.
Commit c6ecc8ae fixes those explicit target dependencies. The original failure
is preserved separately in ../20261121-retained-test-linkage.

The explicit `hanlin-native-shared-editor` lane reuses the same job's
SDK06 Debug app, test bundle and xctestrun. It executes the original ten
shared-editor methods / fifteen declared invocations, then the seven new
native text acknowledgement component methods, before creating the SDK06
native fixture and executing its UI journey. No second application build is
created. The default `hanlin-native` and optional `hanlin-native-text-ack`
selections remain available for later focused attempts.

The wrapper delegates source selection, raw summary and individual argument
validation to the unchanged Tools/Hanlin/run_host_tests.py shared-editor
profile. It requires the actual app path to match the SDK06 app, freezes both
executables and xctestrun by SHA256, rejects stale evidence and rechecks source
identity after execution. A passing component receipt does not claim actual
native persistence or full application acceptance.

Validation on Windows/Python3.12: seven new wrapper controls PASS
(job_52a31614adf8, 2026-11-21T20:47:39Z). They cover exact ten-method/fifteen-case
scope, both Apple summary count forms, wrong app rejection before Xcode,
missing parameter cases, source mutation, app/test/configuration byte mutation,
stale evidence and the actual tracked declaration set. This is controller
validation; actual Apple component execution remains pending until the new
SDK06 job supplies its original xcresult. Existing passing component suites
were not rerun.
