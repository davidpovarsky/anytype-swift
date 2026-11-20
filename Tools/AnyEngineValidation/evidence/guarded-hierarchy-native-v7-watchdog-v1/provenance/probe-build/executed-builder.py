"""Private diagnostic Probe+wrapper build; unchanged production and20 checks."""
from pathlib import Path
import argparse
import difflib
import importlib.util
import json
import shutil
import subprocess

TRACE_SHA = 'b6b8d048529d341b05a33a159cbd70c2ee78183f4232ab475335acdec7d6e091'
PREPARED_SHA = '5c462ff4aae7ea1d66390d3dd1c7f9285061b186248d8f77fd0f963585d93bfb'
PATCH_SHA = '4d5f256a721d032092fe73ba0770a11e7ec9d9c47cd0564e5847f689f2abf023'
PINS = {'swift-crypto': 'e8d6eba1fef23ae5b359c46b03f7d94be2f41fed',
        'swift-asn1': '917b472dbe53ba699cbb0495f9a95a084bc6364d'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo-root', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    root, out = args.repo_root.resolve(), args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    helper_path = root / 'Tools/AnyEnginePort/run_live_provider_probe.py'
    spec = importlib.util.spec_from_file_location('process_helper', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    result = {'status': 'FAIL', 'diagnosticsOnly': True, 'unchangedTwentyAssertions': False,
              'productionHTTPSettingsChanged': False, 'transportReliabilityEstablished': False,
              'scope': 'Same current production hierarchy and20 assertions; only explicit diagnostic gate11 arm plus the reviewed temporary Engine one-shot fresh-session watchdog. Original requests remain unchanged.'}
    before = helper.source_snapshot(root, Path(__file__))
    helper.write_json(out / 'source-before.json', before)
    shutil.copyfile(__file__, out / 'executed-builder.py')
    shutil.copyfile(helper_path, out / 'executed-process-helper.py')
    expected = {}
    modules_before = {}
    try:
        original_dir = root / 'build/any-engine-port/guarded-hierarchy-components-v3'
        producer = original_dir / 'result.json'
        proof = json.loads(producer.read_text(encoding='utf8'))
        if proof.get('status') != 'PASS_EXACT_SOURCE_COMPONENT_BUILD' or proof.get('sourceStable') is not True:
            raise RuntimeError('successful_original_link_required')
        result['sourceInputs'] = proof['sourceInputs']
        for path, sha in proof['sourceInputs'].items():
            if helper.sha256(root / path) != sha:
                raise RuntimeError('compiled_source_changed:' + path)
        result['producerReceiptSHA256'] = helper.sha256(producer)
        trace_dir = root / 'build/any-engine-port/http-watchdog-engine-v4-20261119-215447-642343'
        trace_path = trace_dir / 'reusable-watchdog-engine-v4.json'
        if helper.sha256(trace_path) != TRACE_SHA:
            raise RuntimeError('reviewed_watchdog_manifest_changed')
        trace = json.loads(trace_path.read_text(encoding='utf8'))
        if trace.get('changedEngineFiles') != ['AnyHTTPClient.swift']:
            raise RuntimeError('unreviewed_watchdog_source_change')
        prefix = 'Modules/PinkhaAnyEngine/Sources/PinkhaAnyEngine/'
        engine_sources = {Path(p).name: s for p, s in proof['sourceInputs'].items() if p.startswith(prefix) and p.endswith('.swift')}
        if engine_sources != trace['originalEngineSourceManifest']:
            raise RuntimeError('original_engine_source_mismatch')
        receipt_path = root / trace['buildReceipt']
        if helper.sha256(receipt_path) != trace['buildReceiptSHA256']:
            raise RuntimeError('watchdog_compile_receipt_changed')
        receipt = json.loads(receipt_path.read_text(encoding='utf8'))
        expected_receipt = {'status': 'PASS_BUILD_ONLY', 'preparedSHA256': PREPARED_SHA,
            'originalRequestTimeoutSeconds': 30, 'controlRequestTimeoutSeconds': 10,
            'watchdogDelaySeconds': 1, 'maximumActivations': 1, 'businessResultsUseControlResponse': False,
            'productionSourceChanged': False, 'businessAssertionsChanged': False,
            'engineCompileExitCode': 0, 'modulewrapExitCode': 0, 'sourceStable': True,
            'copiedSourcesStable': True, 'cachedModulesStable': True, 'compilerUnchanged': True,
            'runnerUnchanged': True, 'boundedRunnerUnchanged': True}
        if any(receipt.get(k) != v for k, v in expected_receipt.items()):
            raise RuntimeError('watchdog_compile_provenance_incomplete')
        if helper.sha256(trace_dir / 'prepared.json') != PREPARED_SHA or helper.sha256(root / trace['diagnosticPatch']) != PATCH_SHA:
            raise RuntimeError('reviewed_watchdog_diff_or_preparation_changed')
        for name, sha in trace['copiedEngineSourceManifest'].items():
            if helper.sha256(trace_dir / 'EngineSources' / name) != sha:
                raise RuntimeError('actual_watchdog_compiler_source_changed')
        for item in trace['compiledFiles'].values():
            if helper.sha256(root / item['path']) != item['sha256']:
                raise RuntimeError('actual_watchdog_output_changed')
        for file in ('reusable-watchdog-engine-v4.json', 'prepared.json', 'build-receipt.json', 'AnyHTTPClient.watchdog-v4.diff'):
            shutil.copyfile(trace_dir / file, out / file)
        result.update(traceManifestSHA256=TRACE_SHA, traceBuildReceiptSHA256=helper.sha256(receipt_path),
                      tracePatchSHA256=PATCH_SHA, diagnosticEngineSourceInputs=trace['copiedEngineSourceManifest'])
        dep_proof = {}
        for package in ('PinkhaAnyHost', 'PinkhaAnyIntegration'):
            for name, pin in PINS.items():
                checkout = root / 'Modules' / package / '.build/checkouts' / name
                base = ['git', '--no-optional-locks', '-C', str(checkout)]
                head = subprocess.check_output(base + ['rev-parse', 'HEAD'], timeout=20, encoding='utf8').strip()
                status = subprocess.check_output(base + ['status', '--porcelain', '--untracked-files=normal'], timeout=20, encoding='utf8').strip()
                if head != pin or status:
                    raise RuntimeError('clean_dependency_pin_mismatch')
                dep_proof[package + '/' + name] = {'gitHEAD': head, 'clean': True}
        result['dependencySourceCompatibility'] = dep_proof
        original_compile_dir = root / 'build/any-engine-port/guarded-hierarchy-components-v1'
        original_compile = json.loads((original_compile_dir / 'result.json').read_text(encoding='utf8'))
        step = next(v for v in original_compile['steps'] if v['name'] == 'PinkhaAnyIntegrationProbe')
        if step.get('exitCode') != 0 or step.get('timedOut'):
            raise RuntimeError('original_probe_compile_not_proven')
        source_dir, modules = out / 'ProbeSources', out / 'Modules'
        source_dir.mkdir()
        modules.mkdir()
        source_paths = sorted((root / 'Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegrationProbe').glob('*.swift'))
        if len(source_paths) != 4:
            raise RuntimeError('four_original_probe_sources_required')
        copied = []
        source_changes = []
        for source in source_paths:
            data = source.read_bytes()
            new_data = data
            if source.name == 'GuardedHierarchyProbe.swift':
                anchor = b'            let beforeArchive = try await store.readObject(objectID: folderID)'
                if data.count(anchor) != 1:
                    raise RuntimeError('unique_gate11_anchor_missing')
                line_end = b'\r\n' if b'\r\n' in data else b'\n'
                addition = b'            AnyHTTPDiagnosticWatchdog.armAfterHierarchyGate11()' + line_end
                preceding = data[max(0, data.index(anchor) - 400):data.index(anchor)]
                if b'check("guarded_hierarchy_cycle_refused", true)' not in preceding:
                    raise RuntimeError('gate11_position_not_verified')
                new_data = data.replace(anchor, addition + anchor)
                if new_data.replace(addition, b'', 1) != data:
                    raise RuntimeError('probe_assertion_bytes_changed')
                source_changes = list(difflib.unified_diff(data.decode('utf8').splitlines(True), new_data.decode('utf8').splitlines(True), fromfile='original/GuardedHierarchyProbe.swift', tofile='diagnostic/GuardedHierarchyProbe.swift'))
            destination = source_dir / source.name
            destination.write_bytes(new_data)
            copied.append(destination)
        (out / 'Probe.arm-only.diff').write_text(''.join(source_changes), encoding='utf8')
        result['unchangedTwentyAssertions'] = True
        result['diagnosticProbeInputs'] = {p.relative_to(root).as_posix(): helper.sha256(p) for p in copied}
        result['originalAssertionSourceSHA256'] = helper.sha256(root / 'Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegrationProbe/GuardedHierarchyProbe.swift')
        result['probeArmDiffSHA256'] = helper.sha256(out / 'Probe.arm-only.diff')
        module_inputs = [trace_dir / 'Modules', original_compile_dir / 'Modules', root / 'Modules/PinkhaAnyIntegration/.build/x86_64-unknown-windows-msvc/debug/Modules']
        modules_before = {str(p): helper.sha256(p) for d in module_inputs for p in sorted(d.glob('*')) if p.is_file()}
        result['cachedModuleHashes'] = modules_before
        command = list(step['command'])
        old_sources = {str(p) for p in source_paths}
        command = [arg for arg in command if arg not in old_sources]
        command[command.index('-emit-module-path') + 1] = str(modules / 'PinkhaAnyIntegrationProbe.swiftmodule')
        output_map = {str(p): {'object': str(out / (p.name + '.o'))} for p in copied}
        helper.write_json(out / 'output-file-map.json', output_map)
        command[command.index('-output-file-map') + 1] = str(out / 'output-file-map.json')
        cache_command = trace['compilerCommand']
        command[command.index('-module-cache-path') + 1] = cache_command[cache_command.index('-module-cache-path') + 1]
        command[1:1] = ['-I', str(trace_dir / 'Modules')]
        command = ['-j1' if arg == '-j2' else '-gnone' if arg == '-g' else arg for arg in command]
        for i in range(len(command) - 2, -1, -1):
            if command[i:i+2] == ['-Xcc', '-gdwarf']:
                del command[i:i+2]
        command += [str(p) for p in copied]
        if Path(command[0]) != Path(trace['compilerCommand'][0]) or helper.sha256(Path(command[0])) != receipt['compilerSHA256']:
            raise RuntimeError('watchdog_probe_compiler_mismatch')
        compile_stage = out / 'compile'
        compile_stage.mkdir()
        result['compile'] = helper.run_process(command, root, compile_stage, 180)
        if result['compile'].get('exitCode') != 0 or result['compile'].get('timedOut') or result['compile'].get('cleanupErrors') or result['compile'].get('runnerErrorType'):
            raise RuntimeError('actual_diagnostic_probe_compile_failed')
        wrapper = out / 'PinkhaAnyIntegrationProbe.swiftmodule.o'
        wrap_command = [command[0], '-modulewrap', str(modules / 'PinkhaAnyIntegrationProbe.swiftmodule'), '-target', 'x86_64-unknown-windows-msvc', '-o', str(wrapper)]
        wrap_stage = out / 'wrap'
        wrap_stage.mkdir()
        result['modulewrap'] = helper.run_process(wrap_command, root, wrap_stage, 45)
        if result['modulewrap'].get('exitCode') != 0 or result['modulewrap'].get('timedOut') or result['modulewrap'].get('cleanupErrors') or result['modulewrap'].get('runnerErrorType'):
            raise RuntimeError('actual_diagnostic_probe_wrap_failed')
        original_objects = proof['objectHashes']
        for path, sha in original_objects.items():
            if helper.sha256(Path(path)) != sha:
                raise RuntimeError('retained_original_object_changed')
        objects = [Path(p) for p in original_objects]
        engine_objects = [p for p in objects if 'PinkhaAnyEngine.build' in p.parts]
        if {p.name for p in engine_objects} != {name + '.o' for name in engine_sources} | {'PinkhaAnyEngine.swiftmodule.o'}:
            raise RuntimeError('complete_engine_object_replacement_required')
        probe_objects = [p for p in objects if p.parent.name in ('PinkhaAnyIntegrationProbe', 'wrap-PinkhaAnyIntegrationProbe')]
        if {p.name for p in probe_objects} != {p.name + '.o' for p in source_paths} | {'PinkhaAnyIntegrationProbe.swiftmodule.o'}:
            raise RuntimeError('complete_probe_object_replacement_required')
        insertions = [root / trace['compiledFiles'][name]['path'] for name in ('PinkhaAnyEngine.o', 'PinkhaAnyEngine.swiftmodule.o')]
        insertions += [Path(value['object']) for value in output_map.values()] + [wrapper]
        objects = [p for p in objects if p not in engine_objects and p not in probe_objects] + insertions
        if len(objects) != len(set(objects)):
            raise RuntimeError('duplicate_link_object')
        expected = {str(p): helper.sha256(p) for p in objects}
        result.update(objectCount=len(objects), objectHashes=expected, removedEngineObjects=[str(p) for p in engine_objects], removedProbeObjects=[str(p) for p in probe_objects], insertedObjects=[str(p) for p in insertions])
        link = list(proof['process']['command'])
        indexes = [i for i, arg in enumerate(link) if arg.startswith('@')]
        if len(indexes) != 1:
            raise RuntimeError('unexpected_link_response_files')
        response = out / 'Objects.LinkFileList'
        response.write_text('\n'.join('"' + str(p).replace('\\', '/') + '"' for p in objects) + '\n', encoding='utf8')
        link[indexes[0]] = '@' + str(response)
        executable = out / 'guarded-hierarchy-watchdog-probe.exe'
        link[link.index('-o') + 1] = str(executable)
        if '/threads:1' not in link or '/debug:none' not in link:
            raise RuntimeError('bounded_link_profile_required')
        link_stage = out / 'link'
        link_stage.mkdir()
        result['process'] = helper.run_process(link, root, link_stage, 180)
        if result['process'].get('exitCode') != 0 or result['process'].get('timedOut') or result['process'].get('cleanupErrors') or result['process'].get('runnerErrorType'):
            raise RuntimeError('actual_watchdog_link_failed')
        if any(helper.sha256(Path(p)) != h for p, h in expected.items()):
            raise RuntimeError('link_inputs_changed')
        result.update(status='PASS_EXACT_SOURCE_COMPONENT_BUILD', binary=str(executable), binarySHA256=helper.sha256(executable), binaryBytes=executable.stat().st_size)
    except Exception as error:
        result['errorType'] = type(error).__name__
        if type(error) is RuntimeError:
            result['errorCode'] = str(error)
    finally:
        after = helper.source_snapshot(root, Path(__file__))
        helper.write_json(out / 'source-after.json', after)
        result['sourceStable'] = before['files'] == after['files'] and before['dependencies'] == after['dependencies']
        result['cachedModulesStable'] = all(helper.sha256(Path(p)) == h for p, h in modules_before.items())
        if not result['sourceStable'] or not result['cachedModulesStable']:
            result['status'] = 'FAIL'
        helper.write_json(out / 'result.json', result)
    print(json.dumps({k: result[k] for k in ('status', 'binarySHA256', 'objectCount', 'sourceStable', 'cachedModulesStable', 'unchangedTwentyAssertions', 'errorType', 'errorCode') if k in result}))
    return 0 if result['status'] == 'PASS_EXACT_SOURCE_COMPONENT_BUILD' else 1


if __name__ == '__main__':
    raise SystemExit(main())
