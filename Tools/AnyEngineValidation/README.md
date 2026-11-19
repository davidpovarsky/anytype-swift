# Any engine integration validation

`run_runtime_validation.py` runs the pinned Any engine as separate managed processes. It creates fresh temporary account/device storage, uses synthetic Hebrew text, captures the mnemonic and host control tokens privately, and removes the temporary files after shutting the processes down. It never opens an existing Anytype or Any wallet.

## Run

Python 3.12 and the official Windows x86_64 Any v0.5.0 release executable are supported by the recorded validation. The executable digest is checked before starting it. Network bootstrap must be explicit: supply a staging/local nodeconf with `--network-config`, or use `--allow-public-network` for a disposable synthetic account on the official network.

```powershell
py -3.12 Tools/AnyEngineValidation/run_runtime_validation.py `
  --binary <path-to-release-any.exe> `
  --allow-public-network `
  --output <path-to-summary.json>
```

To include the actual Swift adapter, build `Modules/PinkhaAnyEngine` and add `--probe-binary <path-to-PinkhaAnyEngineProbe.exe>`.

## What the checks mean

The harness checks the release digest, managed startup, new-account identity, creation of an owned Space and native page, exact mixed Hebrew/English text round trips, the initial SSE snapshot and a subsequent edit event, restoration into an independent device directory, and bidirectional native-block synchronization. It verifies persisted reads and writes across shutdown and restart.

The offline phase uses a separate executable copy for each peer. It adds one temporary Windows outbound firewall rule for the first peer's exact executable path, verifies the rule in ActiveStore, proves that the second peer does not receive an offline write, then removes the rule and checks that the durable write synchronizes. The firewall profiles must already be enabled and the process must have authority to add the scoped rule. Existing firewall rules and profile settings are never changed. The rule name and verified removal are recorded in the result. Cleanup runs on failures as well.

Changing `nodeconf` alone is not proof of offline operation: the pinned `any-sync` service restores stored network configurations and merges coordinator addresses. `runtime-baseline-v2.json` is explicitly superseded for this reason. Its successful online observations remain observations, but its offline labels must not be used as acceptance evidence.

HTTP redirects are refused. Mutations fail if a successful HTTP response contains rejections. SSE shutdown closes the underlying socket and joins the reader. Transport failures on reads may be retried within the convergence deadline; writes are never blindly retried. Evidence records failures outside named checks as `fatalFailure`.

## Evidence and limits

- `evidence/source-build.json` records the public upstream/SDK source pins, official archive/executable hashes, a successful source CLI build, and the two focused upstream test packages.
- `evidence/runtime-baseline.json` records an early failure while querying a peer before its Space index arrived.
- `evidence/runtime-baseline-v2.json` is superseded: configuration-only offline isolation was insufficient.
- `evidence/runtime-firewall-v3.json` records the actual firewall-isolated engine component run.

The source CLI build omits the `llamacpp` tag. Runtime validation uses the verified official release binary with embedding disabled. These checks do not establish complete application migration, iOS UI acceptance, physical iPad behavior, semantic search quality, or parity of every custom capability. A missing Swift probe is reported as `NOT_RUN`, never as a passed adapter test.