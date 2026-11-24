# Original gomobile with exact Heart module roots

The failed ABI bind is retained as a failure. Its archives are never inputs to
this adapter. The pinned gomobile and gobind executables run again, unchanged,
and produce fresh generated source and real platform archives.

The original gomobile implementation promotes every module returned by
`go list -m -json all` into a root requirement. The retained run selected 695
modules and promoted previously pruned edges; its actual wrapper selected
googleapis 1.4.1, sdk/metric 1.46.0 and x/arch 0.10.0 instead of Heart's pinned
1.3.1, 1.44.0 and 0.8.0. The original observer correctly rejected this result.

The original pre-tidy wrapper says `go 1.26`: pinned gomobile's
`main.go:ensureGoVersion` deliberately emits major/minor only. This boundary is
distinct from the copied Heart module and the actual compiler, both pinned to
1.26.5. All 682 generated requirements and 13 replacements are also compared.

## Producer integration

Load `pinned_wrapper.py` from the committed control checkout. After the original
toolchain, module-list and gobind/gomobile preparation, immediately before the
real bind, call:

```python
launch = pinned.prepare(root, heart, work, evidence, env, modules,
                        go_root, sdk_context, ldflags, commands.deadline)
ordinary_path = env['PATH']
try:
    env['PATH'] = launch['path_prefix'] + os.pathsep + ordinary_path
    commands.require('gomobile_bind', ORIGINAL_UNCHANGED_BIND_ARGV, heart, 6000)
    bind = commands.items[-1]
finally:
    env['PATH'] = ordinary_path
adapter_row, adapter_receipt = pinned.collect(launch)
compiler_inputs = mobile.capture(commands, bind, heart, work, evidence, env,
                                sdk_context, modules, go_root, ldflags, row, write)
```

All arguments are actual current inputs; no fake run IDs or command receipts
are introduced. `env` must be the same dictionary used by `Commands`. The
adapter uses the pinned real Go binary, records its digest and the explicit
launcher/control-source identity, and joins the existing outer command group.
The original producer remains responsible for draining that group and for its
unchanged source, generated Swift, exports, Invocation link and final SDK gates.

Only the original per-target `go mod tidy` boundary is adapted. Before that
command, original Heart module roots and wildcard replacements are copied,
the module name becomes `gobind`, and one local Heart require/replace is added.
The exact structured root/directive delta is checked. Actual tidy outputs and
raw streams are retained. Its temporary added checksums are not admitted: the
original Heart go.sum bytes are restored, and real readonly module/package
declarations must succeed and match the original module selections. All three
targets must pass this declaration barrier before any archive compiler starts.

The real Go archive command adds only the explicitly recorded
`-mod=readonly`; all original targets, tags, compiler flags, minimum OS and
linker flags are required exactly. Compiler input hashes are checked before
and after each archive. Original gomobile packaging and original iosrepack
still execute. The original `abi_mobile_inputs.py` is unchanged and rechecks
the actual wrapper declarations and checksum subset afterwards.

## Required ABI admission revision

Use an explicit ABI admission schema `/2`, with a required
`pinned_wrapper` reference to `pinned-wrapper/RESULT.json`. Require its schema
`otzaria.gomobile-pinned-wrapper-observation/1`, status
`THREE_ACTUAL_PINNED_WRAPPERS_PASS`, exactly ios-arm64,
iossimulator-arm64 and iossimulator-amd64, the exact committed control SHA,
and all referenced launch, prepared, build, command and raw-stream hashes.
The outer real `gomobile_bind` must independently have returned zero and
drained its owned group. Each target's actual command must return zero without
timeout; nested commands deliberately do not claim independent group ownership.

Keep the original required command keys (`gomobile_bind`, actual Invocation
link, all three export observations). Do not accept this adapter implicitly
under the old `/1` schema. The result provides no Native, complete SDK, editor
runtime, device runtime or App Store credit by itself.

For independent before/after SDK intake, call
`verify(result_path, expected_sha256, root, source_sha)`. It checks the same
complete closure without writing anything and without requiring the historical
execution deadline to remain in the future. The returned summary contains the
schema, status, control SHA, exact receipt SHA, three target names and the four
explicit module/generator/rejected-artifact scope flags. All original work,
compiler declarations and archive evidence must remain available.
