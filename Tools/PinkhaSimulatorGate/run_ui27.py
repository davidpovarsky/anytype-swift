"""Build once and execute real native/three-method UI smoke on disposable OS27 devices."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'PinkhaNativeDerived'))
from build_custom_heart import command, digest, git, contains
from build_native_ipa import prepare_source_cache, run_xctest
from validate_wave1 import verify_runtime_copies
from validate_release import method_results, candidate_identity
from simulator_identity import (read_simulator_entitlements, verify_simulator_keychain_identity,
                                verify_simulator_shared_app_group)
from compiled_products import capture_products
from rerun_original_ui import ui_only_project, install_ui_runner, export_ui_console
import wave15_diagnostics as diagnostics
import heart_runtime_profile as heart_profiles

SMOKE = ['testObjectAddPropertyButtonAndPickerSearch', 'testDocumentSourceSearchPresentation',
         'testSourceChipOpensAndClosesInspector']
KIT = '158acb295f832e96907cdadc813a1c2a4bb6a03c'
MARKER = 'pinkha-native-derived-v1-fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077'
DEFAULT_METHOD_SECONDS = 300
PROPERTIES_METHOD_SECONDS = 900
LONG_PROPERTIES_METHODS = frozenset({
    'PinkhaNativeDerivedAcceptanceUITests/testNativePropertiesPickerChipsSetMembershipAndRelaunch',
    'PinkhaNativeDerivedAcceptanceUITests/testUniversalPageNoteCustomPropertiesAndMixedSet',
})


def selection_time_budget(blueprint, selections):
    """Bound the two measured multi-document flows without raising the default.

    Run 44271564420 reached its second document while still making progress at
    the 300-second cap. Only these exact UI methods also opt into 900 in Swift.
    The batch supervisor uses the sum, not maximum multiplied by method count.
    """
    if not isinstance(blueprint, str) or not blueprint or blueprint != blueprint.strip():
        raise ValueError('One explicit test target is required for the time budget')
    if (not isinstance(selections, (list, tuple)) or not selections
            or any(not isinstance(name, str) or not name or name != name.strip() for name in selections)
            or len(set(selections)) != len(selections)):
        raise ValueError('Time budget requires distinct nonempty exact test selections')
    seconds = {name: PROPERTIES_METHOD_SECONDS
               if blueprint == 'PinkhaStage1AcceptanceUITests' and name in LONG_PROPERTIES_METHODS
               else DEFAULT_METHOD_SECONDS for name in selections}
    return dict(default_seconds=DEFAULT_METHOD_SECONDS, maximum_seconds=max(seconds.values()),
                method_seconds=seconds, total_method_seconds=sum(seconds.values()))


def ui_scope_plan(scope, devices):
    if scope not in {'FULL_SMOKE', 'STARTUP_IPAD_DIAGNOSTIC', 'NATIVE_CANCELLATION_DIAGNOSTIC'}:
        raise ValueError('Unsupported execution selection scope')
    kinds = ['iphone', 'ipad'] if scope == 'FULL_SMOKE' else ['ipad'] if scope == 'STARTUP_IPAD_DIAGNOSTIC' else []
    if any(kind not in devices or not devices[kind].get('udid') for kind in kinds):
        raise ValueError('Selection requires each declared device configuration')
    methods = SMOKE if scope == 'FULL_SMOKE' else ['testDocumentSourceSearchPresentation'] if kinds else []
    pairs = [dict(device_family=kind, device_udid=devices.get(kind, {}).get('udid'),
                  configuration_id=kind + '-en-portrait-os27',
                  method='AnytypeComprehensiveAcceptanceUITests/' + name)
             for kind in ['iphone', 'ipad'] for name in SMOKE]
    selected = [p for p in pairs if p['device_family'] in kinds and p['method'].split('/')[-1] in methods]
    excluded = [{**p, 'status': 'NOT_RUN'} for p in pairs if p not in selected]
    return dict(ui_scope=scope, selected_methods=list(methods), selected_device_families=kinds,
                selected_method_device_pairs=selected, expected_ui_executions=len(selected),
                expected_native_executions=int(scope != 'STARTUP_IPAD_DIAGNOSTIC'),
                expected_preparation_executions=len(kinds), unselected_smoke_pairs=excluded,
                release_accepted=False, full_matrix_accepted=False)


def completion_status(scope, actual_passed):
    expected = {'FULL_SMOKE': 6, 'STARTUP_IPAD_DIAGNOSTIC': 1,
                'NATIVE_CANCELLATION_DIAGNOSTIC': 0}.get(scope)
    if expected is None or type(actual_passed) is not int or actual_passed != expected:
        raise RuntimeError('Actual UI pass count differs from the declared scope')
    return {'FULL_SMOKE': 'SMOKE_PASS_FULL_ACCEPTANCE_PENDING',
            'STARTUP_IPAD_DIAGNOSTIC': 'STARTUP_DIAGNOSTIC_COMPLETE_FULL_ACCEPTANCE_PENDING',
            'NATIVE_CANCELLATION_DIAGNOSTIC': 'NATIVE_DIAGNOSTIC_COMPLETE_FULL_ACCEPTANCE_PENDING'}[scope]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def inject(value, blueprint, environment, app_path=None):
    if isinstance(value, dict):
        if value.get('BlueprintName') == blueprint or value.get('TestBundlePath', '').endswith(blueprint + '.xctest'):
            value.setdefault('EnvironmentVariables', {}).update(environment)
            if app_path:
                value['UITargetAppPath'] = str(app_path)
                value['UITargetAppBundleIdentifier'] = 'io.anytype.app'
        for child in value.values():
            inject(child, blueprint, environment, app_path)
    elif isinstance(value, list):
        for child in value:
            inject(child, blueprint, environment, app_path)


def run_selection(app, configuration, blueprint, udid, selections, environment, evidence, prefix, app_path=None):
    if evidence.exists() and any(evidence.iterdir()):
        raise RuntimeError('Refuse stale selection evidence; use a fresh attempt directory')
    time_budget = selection_time_budget(blueprint, selections)
    evidence.mkdir(parents=True, exist_ok=True)
    result = dict(status='FAIL', selected=selections, phase='EXECUTION', prefix=prefix, command_exit_code=None,
                  time_budget=time_budget)
    if blueprint == 'PinkhaStage1AcceptanceUITests':
        scope = environment.get('PINKHA_UI27_SELECTION_SCOPE', 'FULL_SMOKE')
        if scope not in {'FULL_SMOKE', 'STARTUP_IPAD_DIAGNOSTIC', 'WAVE15_ACCEPTANCE'}:
            raise ValueError('Unsupported recorded UI selection scope')
        result.update(ui_scope=scope, expected_selected_methods=len(selections),
                      release_accepted=False, full_matrix_accepted=False)
    write(evidence / 'result.json', result)
    try:
        with configuration.open('rb') as source:
            data = plistlib.load(source)
        inject(data, blueprint, environment, app_path)
        selected = configuration.with_name('UI27-' + prefix + '.xctestrun')
        with selected.open('wb') as target:
            plistlib.dump(data, target)
        write(evidence / 'selection-inputs.json', dict(blueprint=blueprint, selections=selections,
            environment=environment, xctestrun_sha256=digest(selected), xctestrun_path=str(selected),
            device_udid=udid, time_budget=time_budget))
        bundle = evidence / (prefix + '.xcresult')
        filters = sorted({name.split('/')[0] for name in selections}) if blueprint == 'AnytypeTests' else selections
        run_xctest(['xcodebuild', 'test-without-building', '-xctestrun', str(selected),
                    '-destination', 'platform=iOS Simulator,id=' + udid, '-parallel-testing-enabled', 'NO',
                    '-test-timeouts-enabled', 'YES',
                    '-default-test-execution-time-allowance', str(time_budget['default_seconds']),
                    '-maximum-test-execution-time-allowance', str(time_budget['maximum_seconds']),
                    *['-only-testing:' + blueprint + '/' + name for name in filters],
                    '-resultBundlePath', str(bundle)], app, evidence, bundle, prefix)
        result['command_exit_code'] = 0
        summary = json.loads((evidence / (prefix + '-summary.json')).read_text())
        devices = [row['device'] for row in summary.get('devicesAndConfigurations', [])]
        if not devices or any(d.get('osVersion', '').split('.')[0] != '27'
            or d.get('deviceId', '').lower() != udid.lower() or d.get('architecture') != 'arm64' for d in devices):
            raise RuntimeError('Actual xcresult OS27/device/architecture differs from the selected simulator')
        result['actual_devices'] = devices
        methods = method_results(json.loads((evidence / (prefix + '-tests.json')).read_text()))
        expected = {name.removesuffix('()') for name in selections}
        actual = {name.removesuffix('()'): outcome for name, outcome in methods.items()}
        if (summary.get('passedTests') != len(expected) or summary.get('failedTests') != 0
                or summary.get('skippedTests') != 0 or set(actual) != expected
                or any(outcome != 'Passed' for outcome in actual.values())):
            raise RuntimeError('Actual named method results/counts differ from exact selection')
        result.update(status='PASS', passed=len(expected), failed=0, skipped=0, actual_methods=methods)
    except BaseException as error:
        result.update(status='FAIL', error_type=type(error).__name__, error=str(error))
        if isinstance(error, subprocess.CalledProcessError):
            result['command_exit_code'] = error.returncode
    summary_path = evidence / (prefix + '-summary.json')
    tests_path = evidence / (prefix + '-tests.json')
    diagnostic_summary = None
    if summary_path.exists() and tests_path.exists():
        try:
            raw = json.loads(summary_path.read_text())
            diagnostic_summary = raw
            result.update(passed=raw.get('passedTests'), failed=raw.get('failedTests'), skipped=raw.get('skippedTests'),
                          actual_methods=method_results(json.loads(tests_path.read_text())))
        except (ValueError, KeyError) as error:
            result.update(status='FAIL', evidence_error=str(error))
    observation = diagnostics.emit_selection(result, diagnostic_summary)
    if observation is not None:
        result['public_diagnostics'] = observation
    write(evidence / 'result.json', result)
    return result


def test_configuration(products, blueprint):
    def matches(value):
        if isinstance(value, dict):
            return value.get('BlueprintName') == blueprint or any(matches(v) for v in value.values())
        return isinstance(value, list) and any(matches(v) for v in value)
    candidates = []
    for path in products.glob('*.xctestrun'):
        if path.name.startswith(('UI27-', 'PinkhaNativeDerived')):
            continue
        with path.open('rb') as source:
            if matches(plistlib.load(source)):
                candidates.append(path)
    if len(candidates) != 1:
        raise RuntimeError('Expected one actual current Xcode configuration for ' + blueprint)
    return candidates[0]


def read_process_identity(pid, executable, *, command_timeout=lambda: None):
    identity = subprocess.check_output(['ps', '-ww', '-p', str(pid), '-o', 'lstart=', '-o', 'comm='],
                                       text=True, timeout=command_timeout()).strip()
    actual_executable = subprocess.check_output(['ps', '-ww', '-p', str(pid), '-o', 'comm='],
                                                text=True, timeout=command_timeout()).strip()
    if not identity or actual_executable != str(executable):
        raise RuntimeError(f'Actual process executable identity differs: PID {pid}, expected {executable}, observed {actual_executable!r}')
    return identity


def observe_restore_storage(container, evidence, phase):
    """Observe whitelisted persisted metadata; never read Keychain or dump preferences."""
    preferences = container / 'Library/Preferences/io.anytype.app.plist'
    value = dict(status='OBSERVATIONS_ONLY', phase=phase, preferences_present=preferences.is_file(),
                 data_container_path_sha256=hashlib.sha256(str(container).encode()).hexdigest(),
                 middleware_repository_present=(container / 'Library/Application Support/Anytype/middleware-go').is_dir(),
                 scope='STANDARD_PREFERENCES_COPY_NOT_EFFECTIVE_APP_GROUP_OR_AUTH_STATE',
                 cold_process_effective_configuration_verified=False, keychain_read=False, keys={})
    try:
        if preferences.is_file():
            if preferences.stat().st_size > 4 * 1024 ** 2:
                raise ValueError('Preferences exceed bounded observation size')
            stored = plistlib.loads(preferences.read_bytes())
            for key in ['serverConfig', 'userId']:
                raw = stored.get(key)
                item = dict(present=raw is not None)
                if isinstance(raw, bytes):
                    item['encoded_sha256'] = hashlib.sha256(raw).hexdigest()
                    decoded = json.loads(raw)
                    if key == 'userId':
                        item['nonempty_string'] = isinstance(decoded, str) and bool(decoded)
                    elif isinstance(decoded, dict) and len(decoded) == 1:
                        name = next(iter(decoded))
                        item['configuration_case'] = name if name in ['anytype', 'localOnly', 'file'] else 'unrecognized'
                value['keys'][key] = item
    except Exception as error:
        value['observation_error_type'] = type(error).__name__
    write(evidence / ('restore-storage-' + phase + '.json'), value)
    return value


def code_carriers(bundle):
    """Inventory emitted executable bytes; deliberately make no resource equivalence claim."""
    bundle = bundle.resolve()
    info = plistlib.loads((bundle / 'Info.plist').read_bytes())
    if info.get('CFBundleExecutable') != 'Anytype':
        raise RuntimeError('Unexpected actual application executable')
    magic = {bytes.fromhex(value) for value in ['feedface', 'cefaedfe', 'feedfacf', 'cffaedfe',
                                               'cafebabe', 'bebafeca', 'cafebabf', 'bfbafeca']}
    declared = set()
    for metadata in bundle.rglob('Info.plist'):
        if not metadata.resolve().is_relative_to(bundle):
            raise RuntimeError('Bundle metadata points outside the actual bundle: ' + metadata.relative_to(bundle).as_posix())
        value = plistlib.loads(metadata.read_bytes()).get('CFBundleExecutable')
        if value:
            if not isinstance(value, str) or Path(value).name != value or '\\' in value or value in {'.', '..'}:
                raise RuntimeError('Unsafe declared executable name in ' + metadata.relative_to(bundle).as_posix())
            owner = next(parent for parent in metadata.parents
                         if parent == bundle or parent.suffix in {'.app', '.appex', '.framework', '.xctest', '.bundle'})
            executable = (owner / value).resolve()
            if not executable.is_relative_to(bundle) or not executable.is_file():
                raise RuntimeError('Declared executable missing or outside the actual bundle: '
                                   + metadata.relative_to(bundle).as_posix() + ' -> ' + value)
            declared.add(executable)
    carriers = {}
    aliases = {}
    excluded = 0
    for path in sorted(bundle.rglob('*')):
        if path.is_symlink() and not path.resolve().is_relative_to(bundle):
            raise RuntimeError('Bundle symlink requires an unverified external dependency')
        if not path.is_file():
            continue
        canonical = path.resolve()
        with path.open('rb') as source:
            is_macho = source.read(4) in magic
        if canonical in declared and not is_macho:
            raise RuntimeError('Declared executable has an unverified binary format: ' + path.relative_to(bundle).as_posix())
        if not is_macho:
            excluded += 1
            continue
        relative = canonical.relative_to(bundle).as_posix()
        aliases.setdefault(relative, []).append(path.relative_to(bundle).as_posix())
        if relative not in carriers:
            carriers[relative] = dict(sha256=digest(canonical), bytes=canonical.stat().st_size)
    if not declared.issubset({bundle / path for path in carriers}):
        raise RuntimeError('Actual declared code carrier was not inventoried')
    value = dict(scope='ACTUAL_MACHO_AND_DECLARED_EXECUTABLES', carriers=carriers,
                 aliases={path: sorted(names) for path, names in aliases.items()}, transformations=[],
                 full_bundle_equivalence=False,
                 exclusions=[dict(scope='non-Mach-O regular files not declared as executables', count=excluded,
                                  reason='Resources are outside executable-byte binding and were not compared')])
    code_only = {key: value[key] for key in ['scope', 'carriers', 'aliases', 'transformations']}
    canonical_data = json.dumps(code_only, sort_keys=True, separators=(',', ':')).encode()
    return dict(manifest=value, sha256=hashlib.sha256(canonical_data).hexdigest())


def mapped_app_code(installed, carriers, mapping):
    manifest = carriers['manifest']
    observed = []
    for canonical, aliases in manifest['aliases'].items():
        if any(re.search(re.escape(str(installed / alias)) + r'(?=\s|$)', mapping, re.M) for alias in aliases):
            observed.append(canonical)
    entrypoint = 'Anytype.debug.dylib' if 'Anytype.debug.dylib' in manifest['carriers'] else 'Anytype'
    required = {entrypoint, 'Frameworks/ProtobufMessages.framework/ProtobufMessages'}
    if not required.issubset(set(observed)):
        raise RuntimeError('Actual mapped app entrypoint/runtime missing: ' + ', '.join(sorted(required - set(observed))))
    return dict(required_mapped_code=sorted(required), observed_mapped_code=sorted(observed),
                unobserved_code=sorted(set(manifest['carriers']) - set(observed)),
                all_carriers_executed=False)


def verify_ui_process_continuity(evidence, prefix, live, selections, *,
                                 scope='ORDINARY_NON_RELAUNCH_METHOD_BOUNDARIES',
                                 command_timeout=lambda: None):
    """Bind actual entry/final UI hierarchies to one verified live process."""
    if scope not in {'ORDINARY_NON_RELAUNCH_METHOD_BOUNDARIES', 'ACTUAL_COLD_LAUNCH_UI_METHOD_BOUNDARIES'}:
        raise ValueError('Unknown UI process continuity scope')
    attachments = evidence / (prefix + '-attachments')
    manifest = json.loads((attachments / 'manifest.json').read_text())
    expected = {name.removesuffix('()') for name in selections}
    cases = {}
    for case in manifest:
        name = case.get('testIdentifier', '').removesuffix('()')
        if name not in expected:
            continue
        if name in cases:
            raise RuntimeError('Duplicate UI process evidence for a selected method')
        observations = {}
        for label in ['entry-hierarchy', 'final-hierarchy']:
            exported_label = re.compile(re.escape(label)
                + r'_\d+_[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}\.txt')
            matches = [a for a in case.get('attachments', [])
                       if a.get('suggestedHumanReadableName') == label
                       or exported_label.fullmatch(a.get('suggestedHumanReadableName', ''))]
            if len(matches) != 1:
                raise RuntimeError('Exactly one actual ' + label + ' attachment is required per method')
            path = attachments / matches[0]['exportedFileName']
            if path.resolve().parent != attachments.resolve():
                raise RuntimeError('UI process attachment path escapes its evidence directory')
            raw = path.read_bytes()
            first_line = raw.decode('utf-8-sig').lstrip().splitlines()[0]
            header = re.match(r'(?:Attributes:\s*)?Application,\s*(?:0x[0-9a-fA-F]+,\s*)?pid:\s*(\d+)', first_line)
            if header is None or int(header.group(1)) != live['pid']:
                raise RuntimeError('Actual UI target process differs from the mapped process')
            observations[label] = dict(path=path.relative_to(evidence).as_posix(), sha256=digest(path), pid=live['pid'])
        cases[name] = observations
    if set(cases) != expected:
        raise RuntimeError('Actual entry/final process evidence missing selected UI methods')
    after = read_process_identity(live['pid'], Path(live['installed_app']) / 'Anytype',
                                  command_timeout=command_timeout)
    if after != live['process_start_identity']:
        raise RuntimeError('App process start identity changed during UI execution')
    post_main = digest(Path(live['installed_app']) / 'Anytype')
    if post_main != live['installed_app_executable_sha256'] or post_main != live['built_app_executable_sha256']:
        raise RuntimeError('Installed app main executable changed during UI execution')
    post_carriers = code_carriers(Path(live['installed_app']))
    write(evidence / 'post-ui-installed-code-carriers.json', post_carriers)
    if (post_carriers['sha256'] != live['installed_code_carriers']['sha256']
            or post_carriers['sha256'] != live['built_code_carriers']['sha256']):
        raise RuntimeError('Installed executable code carriers changed during UI execution')
    command_timeout()
    result = dict(status='PASS', scope=scope, pid=live['pid'],
                  process_start_identity=live['process_start_identity'], runtime_sha256=live['runtime_sha256'],
                  post_ui_process_start_identity=after, post_ui_app_executable_sha256=post_main,
                  post_ui_code_carriers_sha256=post_carriers['sha256'], full_bundle_equivalence=False,
                  source_sha=live['source_sha'], run_id=live['run_id'], run_attempt=live['run_attempt'],
                  kit_sha=live['kit_sha'], native_marker=live['native_marker'],
                  candidate_inputs_sha256=live['candidate_inputs_sha256'],
                  methods=cases, every_launch_verified=False)
    write(evidence / 'ui-process-continuity.json', result)
    return result


def verify_signed_simulator(app_bundle, evidence):
    command(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(app_bundle)], app_bundle.parent, evidence)
    result = subprocess.run(['/usr/bin/codesign', '--display', '--entitlements', '-', '--xml', str(app_bundle)],
                            capture_output=True, check=True)
    entitlements = plistlib.loads(result.stdout)
    write(evidence / 'code-signature-entitlements.json', entitlements)
    info = plistlib.loads((app_bundle / 'Info.plist').read_bytes())
    if info['CFBundleIdentifier'] != 'io.anytype.app':
        raise RuntimeError('Actual simulator app bundle identity differs')
    executable = app_bundle / info['CFBundleExecutable']
    simulated = read_simulator_entitlements(executable)
    write(evidence / 'simulator-entitlements.json', dict(
        status='SIMULATOR_IDENTITY_INSPECTED_KEYCHAIN_NOT_RUN', evidence_source='MACHO___TEXT___entitlements',
        codesign_verify_exit_code=0, executable_sha256=digest(executable), **simulated))
    identifier = verify_simulator_keychain_identity(simulated)
    prefix = identifier.partition('.')[0]
    condition = info.get('CompilationCondition')
    identities = [dict(
        **verify_simulator_shared_app_group(simulated, info,
            application_prefix=prefix, compilation_condition=condition),
        executable_sha256=digest(executable), bundle_role='application')]
    expected_extensions = {
        'io.anytype.app.AnytypeShareExtension',
        'io.anytype.app.AnytypeNotificationExtension',
        'io.anytype.app.homewidget',
    }
    found_extensions = set()
    for extension in sorted((app_bundle / 'PlugIns').glob('*.appex')):
        extension_info = plistlib.loads((extension / 'Info.plist').read_bytes())
        bundle = extension_info.get('CFBundleIdentifier')
        if bundle not in expected_extensions or bundle in found_extensions:
            raise RuntimeError('Unexpected or duplicate actual simulator extension identity')
        found_extensions.add(bundle)
        if extension_info.get('CompilationCondition') != condition:
            raise RuntimeError('Actual simulator app and extension compilation conditions differ')
        extension_executable = extension / extension_info['CFBundleExecutable']
        if bundle == 'io.anytype.app.homewidget':
            # The original widget has no shared-group entitlement or container use.
            # Preserve it; do not grant a new capability just for this verification.
            identities.append(dict(bundle_identifier=bundle, compilation_condition=condition,
                executable_sha256=digest(extension_executable), bundle_role='widget_without_shared_group'))
        else:
            extension_simulated = read_simulator_entitlements(extension_executable)
            identities.append(dict(
                **verify_simulator_shared_app_group(extension_simulated, extension_info,
                    application_prefix=prefix, compilation_condition=condition),
                executable_sha256=digest(extension_executable), bundle_role='shared_group_extension'))
    if found_extensions != expected_extensions:
        raise RuntimeError('An original simulator extension is missing from the actual app')
    write(evidence / 'simulator-shared-group-identities.json', dict(
        status='CONFIGURATION_AND_ENTITLEMENTS_MATCH_CONTAINER_ACCESS_NOT_YET_RUN',
        identities=identities))


def installed_runtime_source(udid, evidence, built, source_identity, *, command_timeout=lambda: None):
    installed = Path(subprocess.check_output(['xcrun', 'simctl', 'get_app_container', udid,
                                             'io.anytype.app', 'app'], text=True,
                                             timeout=command_timeout()).strip())
    source = dict(**source_identity, installed_app=str(installed),
                  installed_app_executable_sha256=digest(installed / 'Anytype'),
                  built_app_executable_sha256=digest(built / 'Anytype'),
                  installed_code_carriers=code_carriers(installed), built_code_carriers=code_carriers(built),
                  full_bundle_equivalence=False)
    source['status'] = ('MATCHED_BYTES_PROCESS_NOT_YET_VERIFIED'
        if source['installed_app_executable_sha256'] == source['built_app_executable_sha256'] else 'FAIL')
    write(evidence / 'installed-app-source.json', source)
    if source['status'] == 'FAIL':
        raise RuntimeError('Installed app main executable differs from the fresh build')
    if source['installed_code_carriers']['sha256'] != source['built_code_carriers']['sha256']:
        source['status'] = 'FAIL'
        write(evidence / 'installed-app-source.json', source)
        raise RuntimeError('Installed executable code carriers differ from the fresh build')
    return source


def runtime_binding(app, evidence, head, args, installation=None):
    if installation is None:
        installation = json.loads((evidence / "heart/heart-installation.json").read_text())
    return heart_profiles.installed_binding(
        app, installation, head, getattr(args, "runtime_profile", "r14"),
        getattr(args, "heart_source_run_id", ""))


def observe_running_runtime(pid, evidence, built, source, *, command_timeout=lambda: None, metadata=None):
    """Map one supplied live PID. This function never launches or activates an app."""
    if type(pid) is not int or pid <= 1:
        raise ValueError('Actual app process ID is missing')
    marker = heart_profiles.verify_binding(source)
    installed = Path(source['installed_app'])
    runtime = installed / 'Frameworks/ProtobufMessages.framework/ProtobufMessages'
    identity = read_process_identity(pid, installed / 'Anytype', command_timeout=command_timeout)
    mapping = subprocess.run(['/usr/bin/vmmap', '-w', str(pid)], capture_output=True, text=True,
                             timeout=command_timeout())
    (evidence / 'live-runtime-vmmap.log').write_text(mapping.stdout + mapping.stderr)
    loaded = (mapping.returncode == 0 and str(runtime) in mapping.stdout
              and re.search(r'\[\s*' + str(pid) + r'\s*\]', mapping.stdout) is not None)
    identity_after = read_process_identity(pid, installed / 'Anytype', command_timeout=command_timeout)
    record = dict(pid=pid, installed_app=str(installed), runtime_path=str(runtime),
                  runtime_sha256=digest(runtime), marker_present=contains(runtime, marker.encode()),
                  runtime_loaded=loaded, vmmap_exit_code=mapping.returncode,
                  process_start_identity=identity, process_identity_unchanged=identity == identity_after,
                  runtime_verified_at=datetime.now(timezone.utc).isoformat(), every_launch_verified=False,
                  **(metadata or {}))
    write(evidence / 'live-runtime.json', record)
    if not record['marker_present'] or record['runtime_sha256'] != digest(built / 'Frameworks/ProtobufMessages.framework/ProtobufMessages'):
        raise RuntimeError('Installed runtime bytes/marker differ from the verified build')
    if not loaded or not record['process_identity_unchanged']:
        raise RuntimeError('Actual app process identity/runtime mapping is unverified')
    if digest(installed / 'Anytype') != source['built_app_executable_sha256']:
        raise RuntimeError('Installed app main executable changed during runtime mapping')
    record['mapped_app_code'] = mapped_app_code(installed, source['installed_code_carriers'], mapping.stdout)
    record.update({key: value for key, value in source.items() if key != 'status'})
    command_timeout()
    write(evidence / 'live-runtime.json', record)
    return record


def live_runtime(udid, evidence, built, language='en', *, source_identity):
    if language not in {'en', 'he'}:
        raise ValueError('Unsupported UI app language')
    source = installed_runtime_source(udid, evidence, built, source_identity)
    launch_started_at = datetime.now(timezone.utc).isoformat()
    launch = subprocess.check_output(['xcrun', 'simctl', 'launch', '--terminate-running-process', udid, 'io.anytype.app',
        '-AppleLanguages', '(' + language + ')', '-AppleLocale', 'he_IL' if language == 'he' else 'en_US'], text=True,
        env={**os.environ, 'SIMCTL_CHILD_PINKHA_UI27_ROUTE_OBSERVATION': '1',
             'SIMCTL_CHILD_PINKHA_UI27_STARTUP_OBSERVATION': '1'})
    pid = int(re.search(r':\s*(\d+)', launch).group(1))
    return observe_running_runtime(pid, evidence, built, source, metadata=dict(
        requested_app_language=language, route_observation_requested=True, launch_started_at=launch_started_at))


def execute(args, receipt):
    app = args.app.resolve()
    evidence = args.evidence.resolve()
    derived = args.derived.resolve()
    preflight = json.loads((evidence / 'preflight/preflight.json').read_text())
    if preflight.get('status') != 'PREFLIGHT_PASS_UI_NOT_RUN':
        raise RuntimeError('Actual OS27 preflight did not pass')
    plan = ui_scope_plan(args.ui_scope, preflight['selected'])
    smoke = plan['selected_methods']
    receipt.update(ui_scope=args.ui_scope, selection_plan=plan,
                   expected_native_executions=plan['expected_native_executions'],
                   expected_preparation_executions=plan['expected_preparation_executions'])
    write(evidence / 'selection-plan.json', plan)
    head = git(app, 'rev-parse', 'HEAD')
    if head != os.environ.get('GITHUB_SHA') or not os.environ.get('GITHUB_RUN_ID', '').isdigit():
        raise RuntimeError('Actual source/run identity differs')
    matrix = json.loads((app / 'Tools/PinkhaSimulatorGate/required-coverage.json').read_text())
    identity = candidate_identity(app, matrix)
    binding = runtime_binding(app, evidence, head, args)
    receipt.update(source_sha=head, kit_sha=KIT, **binding,
                   run_id=os.environ['GITHUB_RUN_ID'], run_attempt=os.environ['GITHUB_RUN_ATTEMPT'],
                   candidate_input_hashes=identity['hashes'], preflight=preflight)
    ipad = preflight['selected']['ipad']
    native_udid = ipad['udid']
    if plan['expected_native_executions']:
        native_udid = subprocess.check_output(['xcrun', 'simctl', 'create',
            'Pinkha-UI27-native-' + receipt['run_id'], ipad['device']['identifier'], ipad['runtime']['identifier']], text=True).strip()
        receipt['native_proof_udid'] = native_udid
    command(['xcrun', 'simctl', 'boot', native_udid], app, evidence)
    command(['xcrun', 'simctl', 'bootstatus', native_udid, '-b'], app, evidence)
    prepare_source_cache(app, derived)
    flags = ['OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED', 'ENABLE_TESTABILITY=YES',
             'ONLY_ACTIVE_ARCH=YES', 'SWIFT_OPTIMIZATION_LEVEL=-Onone', 'CODE_SIGN_IDENTITY=-',
             'CODE_SIGNING_ALLOWED=YES', 'CODE_SIGNING_REQUIRED=YES', 'PROVISIONING_PROFILE_SPECIFIER=']
    base = ['xcodebuild', 'build-for-testing', '-configuration', 'Release-Anytype',
            '-destination', 'platform=iOS Simulator,id=' + native_udid, '-derivedDataPath', str(derived),
            '-parallel-testing-enabled', 'NO']
    receipt['phase'] = 'BUILD'
    prior_logs = set(evidence.glob('command-*.log'))
    native_suites = []
    if plan['expected_native_executions']:
        native_suites.append('TorahWave1IntegrationTests')
    if plan['expected_preparation_executions']:
        native_suites.append('SimulatorAcceptancePreparationTests')
    command([*base, '-project', 'Anytype.xcodeproj', '-scheme', 'Anytype',
        *['-only-testing:AnytypeTests/' + name for name in native_suites], *flags], app, evidence)
    new_logs = set(evidence.glob('command-*.log')) - prior_logs
    receipt.update(native_build_succeeded=True, native_build_flags=flags,
                   native_build_log=next(iter(new_logs)).name if len(new_logs) == 1 else None)
    ui_derived = derived.with_name(derived.name + '-ui')
    if plan['expected_ui_executions']:
        ui_project = ui_only_project(app)
        # Xcode prunes products absent from an independent project's build graph.
        # Keep its runner products separate from the already built app/test host.
        ui_derived = derived.with_name(derived.name + '-ui')
        ui_base = list(base)
        ui_base[ui_base.index('-derivedDataPath') + 1] = str(ui_derived)
        command([*ui_base, '-project', str(ui_project), '-scheme', 'PinkhaPrebuiltUI',
            *['-only-testing:PinkhaStage1AcceptanceUITests/AnytypeComprehensiveAcceptanceUITests/' + name for name in smoke],
            *flags], app, evidence)
    products = derived / 'Build/Products'
    ui_products = ui_derived / 'Build/Products'
    built = products / 'Release-Anytype-iphonesimulator/Anytype.app'
    receipt['app_executable_sha256'] = digest(built / 'Anytype')
    write(evidence / 'execution.json', receipt)
    verify_signed_simulator(built, evidence)
    verify_runtime_copies(built, binding['native_marker'].encode(), evidence)
    checkout = derived / 'SourcePackages/checkouts/TorahInspectorKit'
    if not checkout.exists():
        checkout = next(p for p in (derived / 'SourcePackages/checkouts').iterdir() if p.name.lower() == 'torahinspectorkit')
    if git(checkout, 'rev-parse', 'HEAD') != KIT:
        raise RuntimeError('Actual resolved Kit checkout differs')
    lock = json.loads((app / 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved').read_text())
    if next(p['state']['revision'] for p in lock['pins'] if p['identity'] == 'torahinspectorkit') != KIT:
        raise RuntimeError('Actual resolved Kit lock differs')
    write(evidence / 'actual-package-pins.json', lock)
    native_configuration = test_configuration(products, 'AnytypeTests')
    receipt['phase'] = 'EXECUTION'
    receipt['native'] = dict(status='NOT_RUN', selected=[], passed=0, failed=0, skipped=0)
    if plan['expected_native_executions']:
        receipt['native'] = run_selection(app, native_configuration, 'AnytypeTests', native_udid,
            ['TorahWave1IntegrationTests/realNativeQueryAndNoteLifecycle'], {'PINKHA_WAVE1_ACCEPTANCE': '1'},
            evidence / 'native', 'native')
        write(evidence / 'execution.json', receipt)
    if not plan['expected_ui_executions']:
        receipt.update(actual_ui_passed=0, actual_ui_failed=0, actual_ui_skipped=0)
        if receipt['native']['status'] != 'PASS':
            raise RuntimeError('The named actual native diagnostic did not pass')
        receipt.update(status=completion_status(args.ui_scope, 0), release_accepted=False,
                       limitations=['Native diagnostic only; all UI and preparation NOT_RUN',
                                    'Full required matrix remains open'])
        return
    ui_configuration = test_configuration(ui_products, 'PinkhaStage1AcceptanceUITests')
    for kind in plan['selected_device_families']:
        selection = preflight['selected'][kind]
        device_evidence = evidence / kind
        device_evidence.mkdir(exist_ok=True)
        udid = selection['udid']
        if udid != native_udid:
            command(['xcrun', 'simctl', 'boot', udid], app, device_evidence)
        command(['xcrun', 'simctl', 'bootstatus', udid, '-b'], app, device_evidence)
        preparation = run_selection(app, native_configuration, 'AnytypeTests', udid,
            ['SimulatorAcceptancePreparationTests/prepareRealUIFixture'],
            {'PINKHA_SIMULATOR_ACCEPTANCE_PREPARATION': '1', 'PINKHA_SIMULATOR_UI_DISPOSABLE': '1'},
            device_evidence / 'preparation', 'prepare-' + kind)
        receipt[kind] = dict(preparation=preparation, ui_status='NOT_RUN')
        if preparation['status'] != 'PASS':
            continue
        container = Path(subprocess.check_output(['xcrun', 'simctl', 'get_app_container', udid, 'io.anytype.app', 'data'], text=True).strip())
        fixture = json.loads((container / 'Library/Application Support/pinkha-simulator-ui27-fixture.json').read_text())
        write(device_evidence / 'fixture-ids.json', fixture)
        receipt[kind]['restore_storage_before_launch'] = observe_restore_storage(container, device_evidence, 'before-launch')
        try:
            live = live_runtime(udid, device_evidence, built,
                source_identity={**binding, **{key: receipt[key] for key in ['source_sha', 'run_id', 'run_attempt', 'kit_sha']},
                    'candidate_inputs_sha256': hashlib.sha256(json.dumps(receipt['candidate_input_hashes'], sort_keys=True).encode()).hexdigest()})
            receipt[kind]['live_runtime'] = live
            install_ui_runner(udid, ui_products, app, device_evidence)
            result = run_selection(app, ui_configuration, 'PinkhaStage1AcceptanceUITests', udid,
                ['AnytypeComprehensiveAcceptanceUITests/' + name for name in smoke],
                {'PINKHA_NATIVE_UI_DISPOSABLE': '1', 'PINKHA_NATIVE_UI_FIXTURE_JSON': json.dumps(fixture),
                 'PINKHA_UI27_APP_LANGUAGE': 'en', 'PINKHA_UI27_EXPECTED_APP_PID': str(live['pid']),
                 'PINKHA_UI27_SELECTION_SCOPE': args.ui_scope},
                device_evidence / 'ui', 'smoke-' + kind, built)
        finally:
            export_ui_console(udid, device_evidence)
            receipt[kind]['restore_storage_after_ui'] = observe_restore_storage(container, device_evidence, 'after-ui')
        receipt[kind].update(ui_status=result['status'], ui=result, configuration_id=kind + '-en-portrait-os27')
        try:
            receipt[kind]['ui_process_continuity'] = verify_ui_process_continuity(
                device_evidence / 'ui', 'smoke-' + kind, live,
                ['AnytypeComprehensiveAcceptanceUITests/' + name for name in smoke])
        except Exception as error:
            receipt[kind]['ui_process_continuity'] = dict(status='FAIL', error_type=type(error).__name__, error=str(error))
            receipt[kind]['ui_status'] = 'FAIL'
            write(device_evidence / 'ui/ui-process-continuity.json', receipt[kind]['ui_process_continuity'])
        write(evidence / 'execution.json', receipt)
    for label, key in [('passed', 'actual_ui_passed'), ('failed', 'actual_ui_failed'), ('skipped', 'actual_ui_skipped')]:
        receipt[key] = sum(receipt.get(k, {}).get('ui', {}).get(label) or 0 for k in ['iphone', 'ipad'])
    if (plan['expected_native_executions'] and receipt['native']['status'] != 'PASS') or any(
            receipt.get(k, {}).get('ui_status') != 'PASS' for k in plan['selected_device_families']):
        raise RuntimeError('One or more actual native/preparation/UI components did not pass')
    if any(not receipt[k]['live_runtime']['runtime_loaded'] for k in plan['selected_device_families']):
        raise RuntimeError('Actual UI results retained, but required live-runtime mapping is unverified')
    receipt.update(status=completion_status(args.ui_scope, receipt['actual_ui_passed']), actual_ui_failed=0,
                   actual_ui_skipped=0, release_accepted=False,
                   limitations=['Selection scope: ' + args.ui_scope,
                                'Unselected method/device pairs are NOT_RUN',
                                'Full required matrix and visual review remain open'])


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--derived', type=Path, required=True)
    parser.add_argument('--ui-scope', choices=['FULL_SMOKE', 'STARTUP_IPAD_DIAGNOSTIC', 'NATIVE_CANCELLATION_DIAGNOSTIC'], default='FULL_SMOKE')
    parser.add_argument('--runtime-profile', choices=heart_profiles.PROFILE_NAMES, default='r14')
    parser.add_argument('--heart-source-run-id', default='')
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    receipt = dict(status='RUNNING', phase='PREFLIGHT', components={}, release_accepted=False,
                   ui_scope=args.ui_scope,
                   expected_native_executions=int(args.ui_scope != 'STARTUP_IPAD_DIAGNOSTIC'),
                   expected_preparation_executions=2 if args.ui_scope == 'FULL_SMOKE' else int(args.ui_scope == 'STARTUP_IPAD_DIAGNOSTIC'),
                   full_matrix_accepted=False,
                   started_at=datetime.now(timezone.utc).isoformat())
    write(args.evidence / 'execution.json', receipt)
    try:
        execute(args, receipt)
    except BaseException as error:
        receipt.update(status='FAIL', error_type=type(error).__name__, error=str(error))
    if receipt.get('native_build_succeeded'):
        try:
            receipt['compiled_products'] = capture_products(args.derived.resolve(), args.evidence,
                receipt['source_sha'], receipt['native_build_flags'])
        except Exception as error:
            receipt['compiled_products'] = dict(status='CAPTURE_FAILED_NO_BUILD_REUSE_ALLOWED', error=str(error))
    receipt['finished_at'] = datetime.now(timezone.utc).isoformat()
    write(args.evidence / 'execution.json', receipt)
    print(json.dumps(receipt))
    return 0 if receipt['status'] in {'SMOKE_PASS_FULL_ACCEPTANCE_PENDING',
        'STARTUP_DIAGNOSTIC_COMPLETE_FULL_ACCEPTANCE_PENDING',
        'NATIVE_DIAGNOSTIC_COMPLETE_FULL_ACCEPTANCE_PENDING'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
